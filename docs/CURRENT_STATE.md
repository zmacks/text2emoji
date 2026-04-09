# PixlPal — Current State

**Last updated:** 2026-04-08  
**Reference plan:** [MVP_PLAN.md](MVP_PLAN.md)

---

## Summary

The project skeleton is complete and the first half of the core gameplay loop is live. `/chat` is fully implemented end-to-end — classification, knowledge injection, Gemini generation, XML parsing, and interaction persistence all wired. `get_active_knowledge` is implemented with a budget-respecting separator-aware join. The remaining loop blockers are `gift_knowledge` (token economy), `update_personality` (customisation), and session-history escalation in the boundary service.

Test suite: **107 tests, all green** (87 unit/integration + 20 property-based). Hypothesis found and fixed a budget-overflow bug in `get_active_knowledge` on first run.

---

## Phase 1 — API Foundation ✅ complete

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

### 1.3 API endpoints — 6 of 9 implemented, 3 stubs

| Endpoint | Status |
|---|---|
| `GET /health` | ✅ |
| `POST /api/pixlpal` | ✅ |
| `GET /api/pixlpal/{id}` | ✅ |
| `GET /api/pixlpal/{id}/tokens` | ✅ |
| `GET /api/pixlpal/{id}/tokens/count` | ✅ with threshold lookup |
| `POST /api/pixlpal/{id}/chat` | ✅ full pipeline |
| `PATCH /api/pixlpal/{id}/personality` | ⚠️ 501 stub |
| `POST /api/pixlpal/{id}/teach` | ⚠️ 501 stub |
| `POST /api/pixlpal/{id}/gift` | ⚠️ 501 stub |
| `GET /api/pixlpal/{id}/history` | ⚠️ 501 stub |

---

## Phase 2 — Core Loop (~50% done)

### 2.1 Chat service (`app/services/chat.py`) — complete

| Item | Status |
|---|---|
| `parse_response(raw)` — XML tag extractor | ✅ |
| `handle_chat(...)` — full pipeline | ✅ |
| `_max_tokens_for_count` — scales 500/1000/2000 with token count | ✅ |
| `_save_interaction` — persists to `interactions` table | ✅ |

Pipeline: `check_input → get_response_mode → get_pixlpal → get_active_knowledge → compose_system_prompt → gemini.generate → parse_response → _save_interaction`

Generation parameters scale with state: `max_output_tokens` grows with token count (500 → 1000 → 2000 at thresholds 1 and 5); temperature is 0.8 for playful mode, 1.0 for witty. Boundary enforcement prepends `BREAK_CHARACTER_PREFIX` for `break_character` mode and appends `BLAND_SYSTEM_SUFFIX` to the system prompt for both flagged modes.

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
| `get_active_knowledge` — budget-limited context injection | ✅ fixed separator-budget bug |
| `gift_knowledge` (Gemini summary → token → threshold check) | ❌ `NotImplementedError` |

### 2.4 Boundary service (`app/services/boundary.py`)

| Item | Status |
|---|---|
| `check_input(text)` — keyword classifier | ✅ |
| `BREAK_CHARACTER_PREFIX` and `BLAND_SYSTEM_SUFFIX` constants | ✅ |
| Wired into `handle_chat` | ✅ |
| `get_response_mode` — session history escalation | ⚠️ partial — classifies current input only; does not yet query the `interactions` table to count prior session violations |

---

## Phase 3 — Harness Integration (~35% started)

| Item | Status |
|---|---|
| `harness-wiki` package (runner, wiki, CLI, meta) | ✅ exists as workspace member |
| `harness-wiki/agent.py` | ✅ exists |
| 3 pixlpal benchmark tasks | ✅ `pixlpal-personality-response`, `pixlpal-boundary-enforcement`, `pixlpal-emoji-translation` |
| Tasks runnable end-to-end against a live server | ⚠️ `/chat` is live; `/gift` and `/teach` are still stubs |
| Wiki pages (`harness-wiki/wiki/`) | ❌ directory is empty |
| Phase 3 task list (6 tasks) | ⚠️ 3 of 6 created; missing: `pixlpal-chat-api`, `pixlpal-token-acquisition`, `pixlpal-token-progression` |

---

## Infrastructure / DX

| Item | Status |
|---|---|
| `Makefile` (dev/run/test/clean targets) | ✅ |
| Test suite — 107 tests, all green | ✅ |
| `pytest` + `pytest-asyncio` + `httpx` + `hypothesis` dev group | ✅ |
| Property-based tests (`tests/test_property.py`, 20 tests) | ✅ |
| Hypothesis found + fixed budget-overflow bug in `get_active_knowledge` | ✅ |

---

## Critical path to working core loop

1. **`gift_knowledge`** — completes the token economy; players can gift content, earn tokens, trigger threshold unlocks
2. **`update_personality`** — completes `PATCH /personality` and enables the witty mode unlock
3. **`get_response_mode` session history** — upgrade boundary service from stateless to session-aware escalation (1-2 violations → bland, 3+ → break_character)
4. **Wiki seed pages** — needed before `harness improve` is useful; `pixlpal-chat-api` harness task is now unblocked
