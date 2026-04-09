# PixlPal — Current State

**Last updated:** 2026-04-08  
**Reference plan:** [MVP_PLAN.md](MVP_PLAN.md)

---

## Summary

The project skeleton is complete and all read-paths are functional. The core gameplay loop (chat → teach → gift → discover → customize) is not yet wired end-to-end — every write path and all generation logic is a `NotImplementedError` stub. The test suite (62 tests, all green) and developer tooling (Makefile, dev deps) were added today.

---

## Phase 1 — API Foundation (~90% done)

### 1.1 Project restructure — complete

| File | Status |
|---|---|
| `app/server.py` | ✅ lifespan, CORS, routers wired |
| `app/core/config.py` | ✅ pydantic-settings, `.env` |
| `app/core/database.py` | ✅ WAL mode, FK enforcement, migrations, seed data |
| `app/core/gemini.py` | ✅ async thread-pool wrapper around google-genai |
| `app/models/schemas.py` | ✅ all request/response models |
| `app/prompts/composer.py` | ✅ data-driven, fragment cache |
| `app/api/routes_pixlpal.py` | ✅ |
| `app/api/routes_chat.py` | ✅ |
| `app/api/routes_tokens.py` | ✅ |

### 1.2 SQLite schema — complete

All 4 tables (`pixlpals`, `tokens`, `interactions`, `token_thresholds`) with indexes and seeded threshold data. WAL mode + FK enforcement enabled at startup.

### 1.3 API endpoints — 5 of 9 implemented, 4 stubs

| Endpoint | Status |
|---|---|
| `GET /health` | ✅ |
| `POST /api/pixlpal` | ✅ |
| `GET /api/pixlpal/{id}` | ✅ |
| `GET /api/pixlpal/{id}/tokens` | ✅ |
| `GET /api/pixlpal/{id}/tokens/count` | ✅ with threshold lookup |
| `PATCH /api/pixlpal/{id}/personality` | ⚠️ 501 stub |
| `POST /api/pixlpal/{id}/chat` | ⚠️ 501 stub |
| `POST /api/pixlpal/{id}/teach` | ⚠️ 501 stub |
| `POST /api/pixlpal/{id}/gift` | ⚠️ 501 stub |
| `GET /api/pixlpal/{id}/history` | ⚠️ 501 stub |

---

## Phase 2 — Core Loop (~25% done)

All four service files exist and are scaffolded. Read paths are solid; every write path and all generation logic is a `NotImplementedError`.

### 2.1 Chat service (`app/services/chat.py`)

| Item | Status |
|---|---|
| `parse_response(raw)` — XML tag extractor | ✅ implemented + 8 tests |
| `handle_chat(...)` — full pipeline | ❌ `NotImplementedError` |

The pipeline steps described in the plan (`boundary → get_active_knowledge → compose_prompt → gemini.generate → parse → interactions.save`) are all individually defined but none are wired together yet.

### 2.2 Personality service (`app/services/personality.py`)

| Item | Status |
|---|---|
| `create_pixlpal` | ✅ |
| `get_pixlpal` (with token count) | ✅ |
| `update_personality` (traits + mode toggle) | ❌ `NotImplementedError` |
| Trait discovery (roll every N interactions) | ❌ not started |

### 2.3 Token service (`app/services/tokens.py`)

| Item | Status |
|---|---|
| `list_tokens` | ✅ |
| `get_token_count` + threshold lookup | ✅ |
| `gift_knowledge` (Gemini summary → token → threshold check) | ❌ `NotImplementedError` |
| `get_active_knowledge` (budget-limited context injection) | ❌ `NotImplementedError` |

### 2.4 Boundary service (`app/services/boundary.py`)

| Item | Status |
|---|---|
| `check_input(text)` — keyword classifier | ✅ |
| `BREAK_CHARACTER_PREFIX` and `BLAND_SYSTEM_SUFFIX` constants | ✅ defined |
| `get_response_mode` — session history escalation | ⚠️ partial — classifies current input only, does not yet count prior violations from the `interactions` table |
| Wired into `handle_chat` | ❌ (chat not implemented) |

---

## Phase 3 — Harness Integration (~35% started)

| Item | Status |
|---|---|
| `harness-wiki` package (runner, wiki, CLI, meta) | ✅ exists as workspace member |
| `harness-wiki/agent.py` | ✅ exists |
| 3 pixlpal benchmark tasks | ✅ `pixlpal-personality-response`, `pixlpal-boundary-enforcement`, `pixlpal-emoji-translation` |
| Wiki pages (`harness-wiki/wiki/`) | ❌ directory is empty — 6 seed pages from plan are not written |
| Tasks runnable end-to-end against a live server | ❌ chat/gift/teach endpoints are all stubs |
| Phase 3 task list (6 tasks) | ⚠️ 3 of 6 created; missing: `pixlpal-chat-api`, `pixlpal-token-acquisition`, `pixlpal-token-progression` |

---

## Infrastructure / DX

| Item | Status |
|---|---|
| `Makefile` (dev/run/test/clean targets) | ✅ added 2026-04-08 |
| Test suite — 62 tests, all green | ✅ added 2026-04-08 |
| `pytest` + `pytest-asyncio` + `httpx` dev group | ✅ added 2026-04-08 |

---

## Critical path to working core loop

In plan order:

1. **`handle_chat`** — unblocks `/chat`, which unblocks harness tasks and makes the gameplay loop feel real
2. **`gift_knowledge` + `get_active_knowledge`** — completes the token economy (knowledge injection into chat)
3. **`update_personality`** — completes `PATCH /personality` and enables the witty mode unlock
4. **`get_response_mode` session history** — upgrade boundary service from stateless to session-aware
5. **Wiki seed pages** — needed before `harness improve` is useful
