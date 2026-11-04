# LLM Guardrails

A Python library that redacts PII, scores prompts for injection patterns, scores model
output for a few bias patterns, and checks that output against a small set of rules.
The checks run in Rust and are called from Python through PyO3. A FastAPI app in `api/`
demonstrates the pipeline. It does not call a model.

## ⚡ Stack

- 🦀 Rust on the stable toolchain in `rust-toolchain.toml`, with the `regex` crate
- 🐍 Python 3.11, 3.12, 3.13, or 3.14. Development uses 3.14 (`.python-version`). [uv](https://docs.astral.sh/uv/) installs it
- 🔗 [PyO3](https://pyo3.rs/) and [maturin](https://www.maturin.rs/), so `llm_guardrails._core` is the extension module
- 📦 Pydantic v2 models on the Python side of each guard
- 🚀 [FastAPI](https://fastapi.tiangolo.com/) demo
- 🧪 pytest, ruff, `cargo fmt`, `cargo clippy -D warnings`, `cargo test`

## 🚀 Get Started

### Requirements

- [Rust](https://rustup.rs/), via rustup. Opening the repo selects the stable channel in `rust-toolchain.toml`
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Python 3.11, 3.12, 3.13, or 3.14. `uv sync` reads `.python-version` and uses 3.14

### Run It

```bash
uv sync --all-extras
uv run uvicorn api.main:app --reload
```

| What | Where |
| --- | --- |
| 🩺 Health | http://localhost:8000/health |
| 📖 Interactive API docs | http://localhost:8000/docs |
| 📄 OpenAPI document | http://localhost:8000/openapi.json |

`GET /health` returns `{"status":"ok","version":"0.1.0"}`. That version string is hard-coded
in `api/main.py`. The package version in `pyproject.toml` is `0.2.0`.

Guard text from Python:

```python
from llm_guardrails import GuardrailsPipeline

pipeline = GuardrailsPipeline()
pre = pipeline.pre_process("My email is alice@example.com. Summarise this report.")

if pre.blocked:
    print(pre.injection.matched_rules)
else:
    print(pre.sanitised_text)
    # "My email is <<EMAIL_1>>. Summarise this report."
    post = pipeline.post_process("Paris is the capital of France.", pre.pii_mapping)
    print(post.final_text)
    print(post.bias.score)
    print(post.validation.is_valid)
```

`GuardrailsPipeline` takes its switches as constructor arguments (`pii_enabled`,
`injection_enabled`, `bias_enabled`, `output_validation_enabled`, `injection_threshold`,
`validation_rules`). `.env-template` lists similar names. Nothing in the library or the
demo reads that file.

The demo does not call an LLM. `POST /guard/full` uses `simulated_llm_response` when you
send one, and otherwise echoes a stub that quotes the sanitised prompt.

## 🛠️ Development

```bash
uv sync --locked --all-extras
uv run ruff check .
uv run ruff format --check .
uv run pytest
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
python3 scripts/release_subject.py --self-test
```

`uv sync` builds the extension. pytest needs that build because the wrappers import
`llm_guardrails._core`. `cargo test` runs the Rust tests without Python.

Two places to change when a guard's behaviour changes:

- the Rust function in `src/`
- the wrapper in `llm_guardrails/`, which should stay a conversion to a pydantic model

`api/main.py` should keep calling `GuardrailsPipeline` rather than growing its own checks.

## 📖 The API Documentation

FastAPI builds the document from the route functions.

| What | Where |
| --- | --- |
| 📖 Interactive reference | http://localhost:8000/docs |
| 📄 The document | http://localhost:8000/openapi.json |

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/health` | Returns status and the hard-coded demo version |
| `POST` | `/guard/input` | `pre_process`: PII placeholders and an injection score |
| `POST` | `/guard/output` | `post_process`: validation, bias score, PII restore |
| `POST` | `/guard/full` | Input guards, then a stub or caller-supplied response, then output guards |

Input example:

```bash
curl -s -X POST http://localhost:8000/guard/input \
  -H 'Content-Type: application/json' \
  -d '{"text": "My SSN is 123-45-6789. What is the weather?"}'
```

A blocked prompt (the injection score is at least the threshold, default `0.5`) comes back
with `"blocked": true` and no output section on `/guard/full`.

## ✅ Testing

```bash
uv run pytest
cargo test
```

pytest covers the wrappers and `GuardrailsPipeline` (`tests/`). `cargo test` covers the
regex helpers in `src/`. The demo routes have no automated test yet.

## 🚢 Deployment

The image in `Dockerfile` builds a wheel with maturin on `python:3.12-slim`, installs that
wheel plus FastAPI and uvicorn, and serves `api.main:app` on port 8000.

```bash
docker build -t llm-guardrails .
docker run --rm -p 8000:8000 llm-guardrails
curl -s http://localhost:8000/health
```

The image does not load `.env-template`. Local development uses uv and Python 3.14.
Publishing a wheel to PyPI is not wired up.

GitHub Actions, on pull requests and on pushes to `main`:

- `CI` runs ruff, pytest on Python 3.11 and 3.14, and `cargo fmt`, clippy, and `cargo test`
- `Security` runs cargo-deny and pip-audit
- `CodeQL` analyses Python and Rust with `build-mode: none`
- `Release` opens a release pull request. It does not push to `main`

## 🔒 Security

What the library actually does:

- **PII.** `src/pii_redactor.rs` replaces matches with `<<LABEL_N>>` and returns the map.
  Labels are `SSN`, `CREDIT_CARD`, `EMAIL`, `PHONE`, `IP_ADDRESS`, `DATE_OF_BIRTH`, and
  `NAME` (two consecutive capitalised words). The credit-card pattern is a run of 13–19
  digits with optional spaces or dashes, not a Luhn check. `NAME` will match ordinary
  title-case phrases. Restoration is a straight string replace of the placeholders.
- **Injection.** Eight regular expressions (`ignore_previous`, `reveal_system_prompt`,
  `role_play_attack`, `developer_mode`, `encoding_evasion`, `do_anything_now`,
  `system_role_injection`, `token_smuggling`). The score is the highest matching weight,
  plus `0.10` when two or more rules match, capped at `1.0`.
- **Bias.** A handful of stereotype patterns, a gendered-token imbalance check, and an
  absolute-generalisation pattern. The score is a weighted sum of those hits, capped at `1.0`.
- **Output.** Optional max length, a top-level JSON `type` and `required` check (not full
  JSON Schema), a hedging-phrase score exposed as `hallucination_score`, and
  required/blocked keyword checks. A hedging hit is a `warning` and does not by itself
  clear `is_valid`.

The map of original PII stays in memory and is handed back to the caller. The library does
not write it to disk. Discarding the map is how a caller drops those values. None of this
is a complete privacy, safety, or compliance programme. Pair it with the controls your
deployment actually needs, and do not send raw prompts to a model provider you have not
reviewed.

CI rejects known-vulnerable and yanked Rust crates (`deny.toml`) and known-vulnerable
Python dependencies (`pip-audit`).

## How the pieces fit

```mermaid
flowchart LR
    subgraph python [Python]
        API[api.main FastAPI]
        PIPE[GuardrailsPipeline]
        WRAP[PIIRedactor InjectionDetector BiasScorer OutputValidator]
    end
    subgraph rust [Rust cdylib]
        PII[pii_redactor]
        INJ[injection_detector]
        BIAS[bias_scorer]
        VAL[output_validator]
    end
    API --> PIPE --> WRAP
    WRAP --> PII
    WRAP --> INJ
    WRAP --> BIAS
    WRAP --> VAL
```

```mermaid
sequenceDiagram
    participant Caller
    participant Pipeline as GuardrailsPipeline
    participant Rust as llm_guardrails._core
    Caller->>Pipeline: pre_process(text)
    Pipeline->>Rust: pii_redact
    Rust-->>Pipeline: sanitised text, mapping
    Pipeline->>Rust: injection_analyse
    Rust-->>Pipeline: score, matched rules
    Pipeline-->>Caller: PreProcessResult
    Note over Caller: Caller sends sanitised text to a model, or stops when blocked
    Caller->>Pipeline: post_process(model text, mapping)
    Pipeline->>Rust: output_validate
    Pipeline->>Rust: bias_score
    Pipeline->>Rust: pii_restore
    Pipeline-->>Caller: PostProcessResult
```

## 📄 License

MIT. Copyright (c) 2026 Melroy Anthony. See [LICENSE](LICENSE).
