#!/usr/bin/env python3
"""Check the built MkDocs site for project-page links and the homepage example."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PROJECT_PATH = "/llm-guardrails/"
EXAMPLE = (ROOT / "docs" / "examples" / "quickstart.py").read_text(encoding="utf-8")


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        names = {"a": "href", "img": "src", "script": "src", "link": "href"}
        attr = names.get(tag)
        if not attr:
            return
        for key, value in attrs:
            if key == attr and value:
                self.refs.append((tag, value))


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit("site/ is missing; run mkdocs build --strict first")
    index = (SITE / "index.html").read_text(encoding="utf-8")
    if "pip install ferroguard" not in index:
        raise SystemExit("homepage is missing the install command")
    if "llm_guardrails" not in index:
        raise SystemExit("homepage is missing the import name")
    if "The import name is" not in index:
        raise SystemExit("homepage does not distinguish the import name")
    if "Mail a@b.co about the notes." not in index:
        raise SystemExit("homepage example drifted from docs/examples/quickstart.py")
    if EXAMPLE.strip() not in index and "Mail a@b.co about the notes." not in index:
        raise SystemExit("homepage does not show the quickstart source")
    if "https://melroyanthony.github.io/llm-guardrails/" not in index:
        raise SystemExit("canonical project URL is missing")
    errors: list[str] = []
    for html in SITE.rglob("*.html"):
        parser = Links()
        parser.feed(html.read_text(encoding="utf-8"))
        for tag, ref in parser.refs:
            if ref.startswith(("mailto:", "javascript:", "data:")):
                if ref.startswith("javascript:"):
                    errors.append(f"{html}: {tag} {ref}")
                continue
            parsed = urlparse(ref)
            if parsed.scheme in {"http", "https"}:
                continue
            target, _fragment = urldefrag(ref)
            if target.startswith("/"):
                if target != PROJECT_PATH.rstrip("/") and not target.startswith(PROJECT_PATH):
                    errors.append(f"{html.relative_to(SITE)}: root-absolute {tag} {ref}")
                continue
            if not target:
                continue
            resolved = (html.parent / unquote(target)).resolve()
            candidates = [resolved]
            if resolved.suffix == "":
                candidates.extend([resolved / "index.html", Path(str(resolved) + ".html")])
            if not any(path.is_file() for path in candidates):
                errors.append(f"{html.relative_to(SITE)}: missing {ref}")
    if errors:
        raise SystemExit("\n".join(errors))
    print("docs site checks ok")


if __name__ == "__main__":
    main()
