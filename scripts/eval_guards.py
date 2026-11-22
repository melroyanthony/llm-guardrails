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
from collections.abc import Callable
from pathlib import Path

from llm_guardrails._core import injection_candidate_score
from llm_guardrails.bias_scorer import BiasScorer
from llm_guardrails.guards import GuardRegistry
from llm_guardrails.injection_detector import InjectionDetector
from llm_guardrails.output_validator import OutputValidator
from llm_guardrails.pii_redactor import PIIRedactor

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "evals" / "v1"
CASES_PATH = EVAL_DIR / "cases.jsonl"
MANIFEST_PATH = EVAL_DIR / "manifest.json"

# Precision and recall are gated only for guards that have a labelled set.
# Every name from GuardRegistry.builtins is still in the predictor map.
GATED_GUARDS = ("injection", "pii")

# A row's provenance is one of these values, and the file uses each of them.
ALLOWED_PROVENANCE = frozenset({"blind", "issue_12", "pattern", "probe", "review", "unit_test"})


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


def provenance_errors(rows: list[dict]) -> list[str]:
    """The set of provenance values must equal the allowed set."""
    found = {row.get("provenance") for row in rows}
    if found == ALLOWED_PROVENANCE:
        return []
    missing = sorted(ALLOWED_PROVENANCE - found)
    extra = sorted(str(name) for name in found - ALLOWED_PROVENANCE)
    return [
        f"provenance must be exactly {sorted(ALLOWED_PROVENANCE)}; missing {missing}; extra {extra}"
    ]


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


def build_predictors(threshold: float) -> dict[str, Callable[[str], bool] | None]:
    """Binary predictors keyed by registry guard name.

    ``pii_restore`` is in the map because the registry registers it, and it
    is not a yes-or-no detector.
    """
    detector = InjectionDetector(threshold=threshold)
    redactor = PIIRedactor()
    validator = OutputValidator()
    scorer = BiasScorer()
    made: dict[str, Callable[[str], bool] | None] = {
        "pii": lambda text: bool(redactor.redact(text)[1]),
        "injection": lambda text: detector.score(text) >= threshold,
        "output_validation": lambda text: not validator.validate(text).is_valid,
        "bias": lambda text: scorer.score(text).score >= threshold,
        "pii_restore": None,
    }
    names = GuardRegistry.builtins().names()
    missing = [name for name in names if name not in made]
    if missing:
        raise RuntimeError(f"eval has no predictor for registry guard(s): {missing}")
    return {name: made[name] for name in names}


def _time_group(
    rows: list[dict],
    predict: Callable[[str], bool],
    repeats: int,
) -> tuple[list[bool], list[float]]:
    for row in rows:
        predict(row["text"])
    predicted: list[bool] = []
    samples: list[float] = []
    for row in rows:
        guess = False
        for _ in range(repeats):
            begin = time.perf_counter()
            guess = predict(row["text"])
            samples.append((time.perf_counter() - begin) * 1_000_000)
        predicted.append(guess)
    return predicted, samples


def _metrics(rows: list[dict], predicted: list[bool], samples: list[float] | None) -> dict:
    metrics = rates([bool(row["label"]) for row in rows], predicted)
    if samples is not None:
        metrics["p50_us"] = nearest_rank(samples, 50)
        metrics["p99_us"] = nearest_rank(samples, 99)
        metrics["max_us"] = max(samples)
        metrics["sample_count"] = len(samples)
    return metrics


def _subset_metrics(rows: list[dict], predicted: dict[str, bool]) -> dict | None:
    if not rows:
        return None
    guesses = [predicted[row["id"]] for row in rows]
    return _metrics(rows, guesses, None)


def score_cases(rows: list[dict], *, threshold: float, repeats: int) -> dict:
    predictors = build_predictors(threshold)
    by_guard: dict[str, list[dict]] = {}
    for row in rows:
        by_guard.setdefault(row["guard"], []).append(row)
    unknown = set(by_guard) - set(predictors)
    if unknown:
        raise ValueError(f"no predictor for {sorted(unknown)}")

    report: dict = {
        "guards": {},
        "slices": {},
        "blind": {},
        "candidate": {},
        "unlabelled_guards": [],
    }
    predicted_by_id: dict[str, bool] = {}
    for name in predictors:
        group = by_guard.get(name, [])
        predict = predictors[name]
        if not group or predict is None:
            report["unlabelled_guards"].append(name)
            continue
        predicted, samples = _time_group(group, predict, repeats)
        for row, guess in zip(group, predicted, strict=True):
            predicted_by_id[row["id"]] = guess
        report["guards"][name] = _metrics(group, predicted, samples)

    injection_rows = by_guard.get("injection", [])
    for split in ("direct", "indirect"):
        chosen = [row for row in injection_rows if row["split"] == split]
        metrics = _subset_metrics(chosen, predicted_by_id)
        if metrics is not None:
            report["slices"][f"injection_{split}"] = metrics
    for guard in GATED_GUARDS:
        chosen = [row for row in by_guard.get(guard, []) if row.get("provenance") == "blind"]
        metrics = _subset_metrics(chosen, predicted_by_id)
        if metrics is not None:
            report["blind"][guard] = metrics

    detector = InjectionDetector(threshold=threshold)
    for row in injection_rows:
        detector.score(row["text"])
    candidate_predicted = []
    shipped_predicted = []
    for row in injection_rows:
        shipped = predicted_by_id[row["id"]]
        shipped_predicted.append(shipped)
        candidate_predicted.append(injection_candidate_score(row["text"]) >= threshold)
    labels = [bool(row["label"]) for row in injection_rows]
    candidate = rates(labels, candidate_predicted)
    candidate["extra_false_positives"] = sum(
        (not label) and (not shipped) and guess
        for label, shipped, guess in zip(
            labels, shipped_predicted, candidate_predicted, strict=True
        )
    )
    report["candidate"]["injection_stripped"] = candidate
    report["latency_repeats"] = repeats
    return report


def round_rate(value: float) -> float:
    return round(value, 4)


def regression_errors(report: dict, baseline: dict, tolerance: float | None = None) -> list[str]:
    if tolerance is None:
        tolerance = float(baseline.get("tolerance", 0.0001))
    errors = []
    for guard in GATED_GUARDS:
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


def _rate_line(name: str, metrics: dict, *, latency: bool) -> str:
    precision = f"{metrics['precision']:.4f}"
    recall = f"{metrics['recall']:.4f}"
    if not latency:
        return f"| {name} | {precision} | {recall} | {metrics['support']} |"
    return (
        f"| {name} | {metrics['precision']:.4f} | {metrics['recall']:.4f} | "
        f"{metrics['p50_us']:.1f} | {metrics['p99_us']:.1f} | {metrics['support']} |"
    )


def markdown_report(report: dict) -> str:
    repeats = report["latency_repeats"]
    lines = [
        "## Eval",
        "",
        f"Latency is a nearest-rank percentile of {repeats} timed repeats per row, "
        "after a warm-up pass. It is not a gate.",
        "",
        "| Guard | Precision | Recall | p50 (µs) | p99 (µs) | n |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for guard in GATED_GUARDS:
        lines.append(_rate_line(guard, report["guards"][guard], latency=True))
    lines.extend(
        [
            "",
            "| Slice | Precision | Recall | n |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for name, metrics in report["slices"].items():
        lines.append(_rate_line(name, metrics, latency=False))
    lines.extend(["", "| Blind rows | Precision | Recall | n |", "| --- | ---: | ---: | ---: |"])
    for name, metrics in report["blind"].items():
        lines.append(_rate_line(f"blind {name}", metrics, latency=False))
    candidate = report["candidate"]["injection_stripped"]
    unlabelled = ", ".join(report["unlabelled_guards"]) or "(none)"
    lines.extend(
        [
            "",
            "Whitespace-stripped injection pass (eval-only, not InjectionDetector): "
            f"precision {candidate['precision']:.4f}, "
            f"recall {candidate['recall']:.4f}, "
            f"extra false positives {candidate['extra_false_positives']}.",
            "",
            f"Guards in the map with no labelled rows: {unlabelled}.",
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
    version = manifest.get("version")
    if not isinstance(version, int):
        print(f"unexpected eval version {version}", file=sys.stderr)
        return 1
    threshold = float(manifest["threshold"])
    tolerance = float(manifest["tolerance"])
    repeats = int(manifest["latency_repeats"])
    if repeats < 2:
        print("latency_repeats must be at least 2", file=sys.stderr)
        return 1

    rows = load_cases()
    errors = provenance_errors(rows)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    report = score_cases(rows, threshold=threshold, repeats=repeats)
    report["version"] = version
    report["cases_sha256"] = digest
    text = markdown_report(report)
    print(text)
    publish_summary(text)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.check:
        baseline = json.loads(args.check.read_text(encoding="utf-8"))
        errors = regression_errors(report, baseline, tolerance)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
