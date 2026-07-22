#!/usr/bin/env python3
"""Run lightweight structural and internal-link checks against the generated site."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


REQUIRED_PAGES = (
    "404.html",
    "index.html",
    "recommendations/index.html",
    "results/index.html",
    "reports/index.html",
    "rules/index.html",
    "improvements/index.html",
)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []
        self.has_title = False
        self.has_description = False
        self.h1_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "title":
            self.has_title = True
        if tag == "meta" and attributes.get("name") == "description" and attributes.get("content"):
            self.has_description = True
        if tag == "h1":
            self.h1_count += 1
        if tag in {"a", "link", "script"}:
            reference = attributes.get("href") or attributes.get("src")
            if reference:
                self.references.append(reference)


def reference_target(page: Path, reference: str) -> Path | None:
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith(("#", "mailto:", "tel:")):
        return None
    raw_path = unquote(parsed.path)
    if not raw_path:
        return None
    target = (page.parent / raw_path).resolve()
    if raw_path.endswith("/"):
        target /= "index.html"
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path, nargs="?", default=Path("_site"))
    args = parser.parse_args()
    site = args.site.resolve()
    errors: list[str] = []

    for required in REQUIRED_PAGES:
        if not (site / required).is_file():
            errors.append(f"Missing required page: {required}")

    pages = sorted(site.rglob("*.html"))
    if not pages:
        errors.append("No HTML pages were generated")

    for page in pages:
        document = page.read_text(encoding="utf-8")
        parsed = PageParser()
        parsed.feed(document)
        relative = page.relative_to(site)
        if not parsed.has_title:
            errors.append(f"Missing title: {relative}")
        if not parsed.has_description:
            errors.append(f"Missing meta description: {relative}")
        if parsed.h1_count < 1:
            errors.append(f"Missing h1: {relative}")
        if "file://" in document:
            errors.append(f"Local file URL found: {relative}")
        for reference in parsed.references:
            target = reference_target(page, reference)
            if target is not None and not target.exists():
                errors.append(f"Broken link in {relative}: {reference}")

    if errors:
        raise SystemExit("Site checks failed:\n- " + "\n- ".join(errors))
    print(f"Checked {len(pages)} HTML pages; all internal references resolve.")


if __name__ == "__main__":
    main()
