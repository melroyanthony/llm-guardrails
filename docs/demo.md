# Demo

From a checkout:

```bash
uv sync --locked --all-extras
uv run uvicorn api.main:app --reload
```

| What | Where |
| --- | --- |
| Health | http://localhost:8000/health |
| Interactive API document | http://localhost:8000/docs |
| OpenAPI document | http://localhost:8000/openapi.json |

`GET /health` returns `{"status":"ok","version":"<installed>"}`. That version is the installed `ferroguard` distribution. The demo does not call an LLM. `POST /guard/full` uses `simulated_llm_response` when you send one, and otherwise echoes a stub that quotes the sanitised prompt.

```bash
curl -s -X POST http://localhost:8000/guard/input \
  -H 'Content-Type: application/json' \
  -d '{"text": "Mail a@b.co about the notes."}'
```

The image in `Dockerfile` serves the same app on port 8000. PyPI publishing stays in the release workflow.

Source and packages:

- [GitHub repository](https://github.com/melroyanthony/llm-guardrails)
- [ferroguard on PyPI](https://pypi.org/project/ferroguard/)
- [Guards](guides/guards.md)
- [Limits](guides/limits.md)
