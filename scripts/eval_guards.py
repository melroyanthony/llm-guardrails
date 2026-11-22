#!/usr/bin/env python3
"""Score the versioned eval set and fail only on a precision or recall drop.

Latency is reported. It is not a gate: the clock moves between runners.
The whitespace-stripped injection pass is scored beside the shipped guard
and is not what ``InjectionDetector`` uses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

from llm_guardrails._core import injection_candidate_score
from llm_guardrails.injection_detector import InjectionDetector
from llm_guardrails.pii_redactor import PIIRedactor

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "evals" / "v1"
CASES_PATH = EVAL_DIR / "cases.jsonl"
MANIFEST_PATH = EVAL_DIR / "manifest.json"
THRESHOLD = 0.5
TOLERANCE = 0.0001

GUARDS = ("injection", "pii")


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def cases_sha256() -> str:
    digest = hashlib.sha256(CASES_PATH.read_bytes()).hexdigest()
    return digest


def load_cases() -> list[dict]:
    rows = []
    for line_number, line in enumerate(CASES_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        row["_line"] = line_number
        rows.append(row)
    return rows


def nearest_rank(samples: list[float], percent: float) -> float:
    """Nearest-rank percentile. ``samples`` need not be sorted."""
    if not samples:
        raise ValueError("no latency samples")
    ordered = sorted(samples)
    index = math.ceil(percent / 100 * len(ordered)) - 1
    index = min(max(index, 0), len(ordered) - 1)
    return ordered[index]


def rates(labels: list[bool], predicted: list[bool]) -> dict[str, float | int]:
    pairs = list(zip(labels, predicted, strict=True))
    true_positive = sum(label and guess for label, guess in pairs)
    false_positive = sum((not label) and guess for label, guess in pairs)
    false_negative = sum(label and (not guess) for label, guess in pairs)
    predicted_positive = true_positive + false_positive
    labelled_positive = true_positive + false_negative
    precision = 1.0 if predicted_positive == 0 else true_positive / predicted_positive
    recall = 1.0 if labelled_positive == 0 else true_positive / labelled_positive
    return {
        "precision": precision,
        "recall": recall,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "support": len(labels),
    }


def _injection_prediction(score: float) -> bool:
    return score >= THRESHOLD


def _pii_prediction(redactor: PIIRedactor, text: str) -> bool:
    _redacted, mapping = redactor.redact(text)
    return bool(mapping)


def score_cases(rows: list[dict]) -> dict:
    detector = InjectionDetector(threshold=THRESHOLD)
    redactor = PIIRedactor()
    by_guard: dict[str, list[dict]] = {guard: [] for guard in GUARDS}
    for row in rows:
        by_guard[row["guard"]].append(row)

    report: dict = {"guards": {}, "candidate": {}}
    for guard, group in by_guard.items():
        started: list[float] = []
        predicted: list[bool] = []
        if guard == "injection":
            detector.score(group[0]["text"])
            for row in group:
                begin = time.perf_counter()
                score = detector.score(row["text"])
                started.append((time.perf_counter() - begin) * 1_000_000)
                predicted.append(_injection_prediction(score))
        else:
            _pii_prediction(redactor, group[0]["text"])
            for row in group:
                begin = time.perf_counter()
                predicted.append(_pii_prediction(redactor, row["text"]))
                started.append((time.perf_counter() - begin) * 1_000_000)
        labels = [bool(row["label"]) for row in group]
        metrics = rates(labels, predicted)
        metrics["p50_us"] = nearest_rank(started, 50)
        metrics["p99_us"] = nearest_rank(started, 99)
        report["guards"][guard] = metrics

    injection_rows = by_guard["injection"]
    detector.score(injection_rows[0]["text"])
    candidate_predicted = []
    shipped_predicted = []
    for row in injection_rows:
        shipped_predicted.append(_injection_prediction(detector.score(row["text"])))
        candidate_predicted.append(_injection_prediction(injection_candidate_score(row["text"])))
    labels = [bool(row["label"]) for row in injection_rows]
    candidate = rates(labels, candidate_predicted)
    extra_false_positives = sum(
        (not label) and (not shipped) and guess
        for label, shipped, guess in zip(
            labels, shipped_predicted, candidate_predicted, strict=True
        )
    )
    candidate["extra_false_positives"] = extra_false_positives
    report["candidate"]["injection_stripped"] = candidate
    return report


def round_rate(value: float) -> float:
    return round(value, 4)


def regression_errors(report: dict, baseline: dict) -> list[str]:
    tolerance = float(baseline.get("tolerance", TOLERANCE))
    errors = []
    for guard in GUARDS:
        live = report["guards"][guard]
        expected = baseline["guards"][guard]
        for metric in ("precision", "recall"):
            actual = round_rate(float(live[metric]))
            floor = round_rate(float(expected[metric])) - tolerance
            if actual + 1e-12 < floor:
                errors.append(
                    f"{guard} {metric} {actual:.4f} is below {floor:.4f} "
                    f"(baseline {expected[metric]:.4f}, tolerance {tolerance})"
                )
    return errors


def markdown_report(report: dict) -> str:
    lines = [
        "## Eval v1",
        "",
        "| Guard | Precision | Recall | p50 (µs) | p99 (µs) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for guard in GUARDS:
        metrics = report["guards"][guard]
        lines.append(
            "| {guard} | {precision:.4f} | {recall:.4f} | {p50:.1f} | {p99:.1f} |".format(
                guard=guard,
                precision=metrics["precision"],
                recall=metrics["recall"],
                p50=metrics["p50_us"],
                p99=metrics["p99_us"],
            )
        )
    candidate = report["candidate"]["injection_stripped"]
    lines.extend(
        [
            "",
            "Whitespace-stripped injection pass (not the shipped detector): "
            f"precision {candidate['precision']:.4f}, "
            f"recall {candidate['recall']:.4f}, "
            f"extra false positives {candidate['extra_false_positives']}.",
            "",
        ]
    )
    return "\n".join(lines)


def publish_summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", type=Path, help="Baseline JSON. Fail on a regression.")
    parser.add_argument("--output", type=Path, help="Write the full report JSON here.")
    args = parser.parse_args(argv)

    manifest = load_manifest()
    digest = cases_sha256()
    if manifest.get("cases_sha256") != digest:
        print("evals/v1/cases.jsonl does not match manifest cases_sha256", file=sys.stderr)
        return 1
    if manifest.get("version") != 1:
        print(f"unexpected eval version {manifest.get('version')}", file=sys.stderr)
        return 1

    rows = load_cases()
    report = score_cases(rows)
    report["version"] = manifest["version"]
    report["cases_sha256"] = digest
    text = markdown_report(report)
    print(text)
    publish_summary(text)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.check:
        baseline = json.loads(args.check.read_text(encoding="utf-8"))
        errors = regression_errors(report, baseline)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
