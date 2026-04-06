# harness-wiki

A clean-room fusion of two ideas:

- **[kevinrgu/autoagent](https://github.com/kevinrgu/autoagent)** — a meta-agent that hill-climbs its own task-agent harness overnight by reading failure trajectories and rewriting `agent.py`
- **[karpathy/llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)** — a persistent, compounding wiki that an LLM incrementally builds and maintains as structured long-term memory

The key insight joining them: **harness memory compounds**. Every task the agent runs either hits prior knowledge in the wiki (faster, fewer mistakes) or produces new knowledge for the wiki (future tasks benefit). The meta-agent's hill-climbing loop becomes more efficient over time because the task agent is no longer rediscovering the same patterns from scratch.

---

## Architecture

```
harness-wiki/
│
├── agent.py              ← The task agent harness (PRIMARY EDIT SURFACE)
│                           Meta-agent edits this. Two sections:
│                           • Editable: SYSTEM_PROMPT, MODEL, MAX_TURNS,
│                             create_tools(), create_agent(), run_task()
│                           • Fixed adapter: tool dispatch, wiki I/O,
│                             trajectory serialization (do not touch)
│
├── program.md            ← Human-editable meta-agent directive
│                           You steer the loop here. Meta-agent reads this.
│
├── CLAUDE.md             ← Wiki schema document
│                           Defines page conventions, naming, index format,
│                           token budget levels, what belongs in the wiki.
│
├── meta/
│   └── runner.py         ← Meta-agent orchestration loop (not under test)
│                           Reads program.md → diagnoses trajectories →
│                           proposes edits to agent.py → benchmarks →
│                           keeps or reverts based on score delta
│
├── harness_wiki/
│   ├── runner.py         ← Task runner: loads tasks/, runs agent, scores
│   ├── wiki.py           ← Wiki utilities: lint, orphan detection, rebuild
│   └── cli.py            ← CLI entry points (harness run / improve / wiki-*)
│
├── tasks/
│   └── example-task/     ← One task in Harbor-compatible format
│       ├── task.toml
│       ├── instruction.md
│       ├── tests/test.sh  ← Verifier: writes score 0.0–1.0 to reward.txt
│       └── environment/files/
│
├── wiki/                 ← Persistent wiki (LLM-maintained, you read)
│   ├── index.md          ← Page catalog (updated on every write)
│   └── log.md            ← Append-only change log
│
├── jobs/                 ← Per-run task outputs and trajectories (gitignored)
├── results.tsv           ← Append-only benchmark ledger
└── pyproject.toml
```

---

## Three layers (Karpathy pattern)

| Layer | What | Who owns it |
|---|---|---|
| **Raw sources** | Task instructions, reference files | You (immutable) |
| **Wiki** | `wiki/*.md` — accumulated agent knowledge | LLM (task agent writes) |
| **Schema** | `CLAUDE.md` — wiki conventions and workflows | You + LLM (co-evolve) |

The wiki is a **persistent, compounding artifact**. Cross-references are already there. Failure modes have already been flagged. The synthesis already reflects everything the agent has run. The wiki keeps getting richer with every task.

---

## Two loops (autoagent pattern)

### Inner loop — task agent (runs once per task)
```
load wiki index → run task → update wiki
```

### Outer loop — meta-agent (runs overnight / on demand)
```
read program.md
→ read agent.py
→ read results.tsv + trajectories
→ group failures by root cause
→ propose ONE improvement to agent.py
→ run benchmark
→ keep if score ↑, revert if score ↓
→ repeat
```

The meta-agent edits the **editable section** of `agent.py` only. The fixed adapter section (tool dispatch, wiki I/O, trajectory serialization) is infrastructure and is not touched.

---

## Quick start

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Set your API key
export GEMINI_API_KEY=your-gemini-api-key-here

# 4. Add tasks to tasks/ (see Task format below)

# 5. Run the benchmark once
harness run

# 6. Run a single task
harness run --task example-task

# 7. Run the meta-agent improvement loop (will iterate until you stop it)
harness improve --iterations 10

# 8. Check the wiki
harness wiki-show "csv parsing"
harness wiki-lint
```

---

## Task format

Each task is a directory under `tasks/`:

```
tasks/my-task/
  task.toml           ← metadata: name, description, timeout
  instruction.md      ← natural-language prompt sent to the task agent
  tests/
    test.sh           ← verifier entry point; writes score to $LOGS_DIR/reward.txt
  environment/
    files/            ← reference files copied into agent workspace before run
```

Scores are `0.0–1.0`. A task is "passed" at `>= 0.5`. The meta-agent hill-climbs on `passed` count.

### Minimal verifier (test.sh)
```bash
#!/usr/bin/env bash
REWARD_FILE="${LOGS_DIR}/reward.txt"
# ... verify workspace state ...
echo "1.0" > "$REWARD_FILE"   # full credit
echo "0.0" > "$REWARD_FILE"   # no credit
```

---

## Key files to edit

| File | When to edit |
|---|---|
| `program.md` | Change the meta-agent's direction or priorities |
| `CLAUDE.md` | Change wiki conventions as you discover what works |
| `agent.py` (editable section) | Manual harness tweaks; meta-agent also edits this |
| `tasks/` | Add new benchmark tasks |

**Do not edit** `agent.py` below `FIXED ADAPTER BOUNDARY` or `harness_wiki/runner.py` unless you're changing infrastructure.

---

## Wiki operations

The wiki implements all three of Karpathy's operations:

**Ingest** — `update_wiki` tool: after each task, the agent writes a page summarizing what it learned. A single task may touch 1–3 pages.

**Query** — `query_wiki` tool + wiki index injected into context: before each task, the agent consults prior knowledge. The index is loaded at L0 (always present); specific pages are loaded on demand at L2.

**Lint** — `harness wiki-lint`: finds orphan pages, dead wikilinks, pages missing from the index.

---

## Model empathy

autoagent's finding: a meta-agent diagnosing a task agent from the same model family outperforms cross-model pairings because the meta-agent shares the same weights and understands the inner agent's failure modes from the inside.

This repo defaults to Gemini (`gemini-2.5-flash`) throughout. To change the task agent model, edit `MODEL` in the editable section of `agent.py`. To change the meta-agent model, edit `META_MODEL` in `meta/runner.py`.

---

## Design principles (clean-room)

This is a **clean-room reimplementation** written from public descriptions only.

- No dependency on `openai-agents` or `harbor` (the original's deps) — uses `google-genai` SDK directly
- No Docker requirement — tasks run in temp directories; add Docker if you need stronger isolation
- Single `uv` workspace, no monorepo overhead
- Wiki layer is the novel addition: persistent memory that neither autoagent nor a plain task runner has
- `results.tsv` is the run ledger exactly as described in autoagent's program.md

---

## Dependencies

- `google-genai` — task agent and meta-agent API calls (Gemini)
- `pydantic` / `pydantic-settings` — config models
- `structlog` — structured logging throughout
- `typer` — CLI
- `tomli` — task.toml parsing
- `python-dotenv` — `.env` support

Python 3.12+, `uv` recommended.
