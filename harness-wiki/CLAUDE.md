# CLAUDE.md — Wiki Schema

This document defines the conventions for the wiki/ directory.
The agent reads this at task start to understand how to maintain the wiki correctly.

## Overview

The wiki is a persistent, compounding knowledge base. It sits between the raw
task experience and the agent's working memory. The agent owns this layer entirely:
it creates pages, updates them after each task, maintains cross-references, and
keeps everything consistent across runs.

You never (or rarely) write the wiki yourself. The agent writes and maintains all of it.

## Directory layout

```
wiki/
  index.md         — catalog of all pages with one-line summaries (update on every write)
  log.md           — append-only chronological record of all wiki changes
  <slug>.md        — individual knowledge pages
```

## Page conventions

### Naming
- Use lowercase slugs: `python-csv-parsing`, `bash-find-patterns`, `json-schema-validation`
- Be specific enough to be searchable but not so specific that the page is one-task only

### Required front matter (YAML)
```yaml
---
tags: [python, csv, parsing]
confidence: high | medium | low
last_updated: 2026-04-05
---
```

### Page structure
1. **Summary** — one paragraph on what this page covers
2. **Key findings** — bullet list of the most important learnings
3. **Code examples** — inline code blocks when relevant
4. **Gotchas** — known failure modes, edge cases, surprises
5. **Cross-references** — `[[related-page]]` links to other wiki pages

## Operations

### Ingest (after a task)
When you complete a task, call `update_wiki` with:
- A page slug specific to what you learned
- Content following the page structure above
- A one-line summary for the index

A single task might produce 1–3 wiki pages. It is fine to update an existing
page rather than creating a new one if the content overlaps.

### Query (before a task)
Before starting a task, call `query_wiki` with relevant keywords.
Read the index first (it's already injected into your context), then use
`read_file wiki/<page>.md` to drill into specific pages.

### Progressive disclosure (token budget)
- L0 (~200 tokens): injected wiki index — always present
- L1 (~1-2K): full index.md — use `read_file wiki/index.md`
- L2 (~2-5K): specific page — use `read_file wiki/<page>.md`
- L3 (5-20K+): rare, only for very large reference pages

Do not read full pages until you have checked the index first.

## What belongs in the wiki

Good candidates:
- Patterns that solved a class of task (e.g. "how to parse CSV with quoting")
- Tool invocation patterns that are non-obvious
- Known failure modes for tasks in this domain
- Lookup tables or reference data needed repeatedly

Bad candidates:
- Task-specific output (the result of *this* task)
- One-off hacks that only apply to one task
- Content that changes on every run (put that in the task output)

## Anti-patterns

- Do NOT create a wiki page for every single task. Pages should capture reusable patterns.
- Do NOT put large raw data in the wiki. Summarize and extract the key insight.
- Do NOT leave orphan pages (no inbound links). Cross-link aggressively.

## Index format

Each entry in index.md:
```
- [[page-slug]] — One-line summary of what the page contains
```

## Log format

Each entry in log.md:
```
## [2026-04-05T14:22:00Z] update | page-slug

One-line summary of what changed and why.
```

Logs are append-only. Never modify existing log entries.
