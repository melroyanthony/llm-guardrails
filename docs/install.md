# Install

The distribution name and the import name are different.

```bash
pip install ferroguard
```

```python
import llm_guardrails
from llm_guardrails import GuardrailsPipeline
```

`import ferroguard` does not load the library. Wheels are abi3 for Python 3.11 and newer, so one wheel covers 3.11 through 3.14.

```python
--8<-- "examples/quickstart.py"
```

`pre.sanitised_text` for that input is `Mail <<EMAIL_1>> about the notes.` `pre.blocked` is false. `pre.pii_mapping` maps `<<EMAIL_1>>` back to `a@b.co`. Keep that mapping in your process. The HTTP demo does not return it.

Restore and the output checks:

```python
--8<-- "examples/restore.py"
```

That prints `Noted.`, then `True`, then `0.0`.

Development from a checkout uses uv and builds the extension:

```bash
uv sync --locked --all-extras
```

Publishing a wheel is the release workflow on `main`. This site does not publish packages.
