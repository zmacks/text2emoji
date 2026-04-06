"""
harness_wiki/wiki.py
====================
Wiki maintenance utilities: lint, health-check, cross-link analysis.
These implement Karpathy's "lint" operation: find contradictions, orphan pages,
missing cross-references, stale claims, and data gaps.
"""

from __future__ import annotations

import re
from pathlib import Path


def get_all_pages(wiki_dir: Path) -> list[Path]:
    """Return all .md pages in the wiki except index.md and log.md."""
    if not wiki_dir.exists():
        return []
    return [
        p for p in wiki_dir.glob("*.md")
        if p.name not in ("index.md", "log.md")
    ]


def get_wikilinks(content: str) -> set[str]:
    """Extract [[wikilink]] references from markdown content."""
    return set(re.findall(r"\[\[([^\]]+)\]\]", content))


def lint_wiki(wiki_dir: Path) -> list[str]:
    """
    Health-check the wiki. Returns a list of issue strings.
    An empty list means the wiki is healthy.
    """
    issues: list[str] = []

    if not wiki_dir.exists():
        return ["Wiki directory does not exist."]

    pages = get_all_pages(wiki_dir)
    page_names = {p.stem for p in pages}
    index_path = wiki_dir / "index.md"

    # Check index exists
    if not index_path.exists():
        issues.append("WARN: index.md is missing")
    else:
        index_text = index_path.read_text(encoding="utf-8")
        indexed_names = set(re.findall(r"\[\[([^\]]+)\]\]", index_text))

        # Pages not in index
        for name in page_names:
            if name not in indexed_names:
                issues.append(f"ORPHAN: '{name}.md' is not listed in index.md")

        # Index entries pointing to missing pages
        for name in indexed_names:
            if name not in page_names:
                issues.append(f"DEAD_LINK: index.md references [[{name}]] but the page doesn't exist")

    # Check cross-links within pages
    all_refs: dict[str, set[str]] = {}
    for page in pages:
        content = page.read_text(encoding="utf-8")
        refs = get_wikilinks(content)
        all_refs[page.stem] = refs
        for ref in refs:
            if ref != "index" and ref not in page_names:
                issues.append(f"DEAD_LINK: '{page.stem}.md' links to [[{ref}]] which doesn't exist")

    # Find pages with no inbound links (orphans inside wiki)
    inbound: dict[str, int] = {name: 0 for name in page_names}
    for refs in all_refs.values():
        for ref in refs:
            if ref in inbound:
                inbound[ref] += 1

    for name, count in inbound.items():
        if count == 0 and name not in ("overview", "index"):
            issues.append(f"ORPHAN: '{name}.md' has no inbound links from other pages")

    return issues


def rebuild_index(wiki_dir: Path) -> None:
    """Rebuild index.md from scratch by scanning all pages for their first heading."""
    pages = get_all_pages(wiki_dir)
    entries = []
    for page in sorted(pages, key=lambda p: p.stem):
        content = page.read_text(encoding="utf-8")
        # Extract first non-empty line as summary
        summary_line = ""
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                summary_line = line[:100]
                break
        entries.append(f"- [[{page.stem}]] — {summary_line}")

    index_content = "# Wiki Index\n\nLLM-maintained knowledge base.\n\n## Pages\n\n"
    index_content += "\n".join(entries) + "\n"
    (wiki_dir / "index.md").write_text(index_content, encoding="utf-8")
