# PixlPal MVP Implementation Plan

**Date:** 2026-04-06
**Stack:** Python 3.13 · FastAPI · Gemini 2.5 Flash (google-genai) · SQLite · uv · harness-wiki

---

## What "MVP" means (from the PRD)

> "PixlPal launches with core loop working: Players can interact, teach, and
> customize their PixlPal companion. Token system is clear, personality system
> is fun, and empathy tutorials feel natural."

This plan covers the **backend API** that powers that loop. The mobile frontend
(React Native / Flutter) is out of scope — we build the API it will call.

---

## What already exists

| Component | Status | Location |
|---|---|---|
| Gemini text generation wrapper | Done | `app/main.py` — `GeminiTextGenerator` |
| PixlPal class (alias, traits, description) | Done | `app/utils.py` — `PixlPal` |
| Modular prompt assembly (fragments → template) | Done | `app/prompts/fragments/` |
| Two personality prototypes (Abbie, Mal) | Done | `app/main.py` — hardcoded in `main()` |
| Dual output format (text + emoji) | Done | Prompt directive + XML tags |
| Harness-wiki (task runner, meta-agent, wiki) | Done | `harness-wiki/` — editable package |
| Wiki domain knowledge (6 seed pages) | Done | `harness-wiki/wiki/` |
| PixlPal benchmark tasks (3 tasks) | Done | `harness-wiki/tasks/pixlpal-*` |

---

## What needs to be built

### Phase 1: API Foundation (the server)

**Goal:** Replace the one-shot `main()` script with a FastAPI server that the
frontend can call.

#### 1.1 — Project restructure

Move from `app/main.py` script to a proper FastAPI application:

```
app/
  __init__.py
  server.py              ← FastAPI app, lifespan, CORS
  api/
    __init__.py
    routes_chat.py       ← POST /chat, POST /teach
    routes_pixlpal.py    ← CRUD for PixlPal instances
    routes_tokens.py     ← Token acquisition, listing, thresholds
  core/
    __init__.py
    config.py            ← Settings via pydantic-settings (GEMINI_API_KEY, DB path)
    database.py          ← SQLite connection pool (aiosqlite), migrations
    gemini.py            ← GeminiTextGenerator (extracted from main.py, made async)
  models/
    __init__.py
    schemas.py           ← Pydantic request/response models
  services/
    __init__.py
    chat.py              ← Compose prompt → call Gemini → parse response → return
    personality.py       ← Trait management, description regeneration
    tokens.py            ← Acquisition, threshold checks, context injection
    boundary.py          ← Input classification, escalation logic
  prompts/
    fragments/           ← (existing files, unchanged)
    composer.py          ← Extract compose_system_prompt from utils.py, make it data-driven
```

**Key decisions:**
- Use `aiosqlite` for non-blocking SQLite access (async-first)
- One `genai.Client` instance shared via FastAPI lifespan (not per-request)
- Prompt fragments stay as files — the composer reads them at startup and caches

#### 1.2 — SQLite schema

```sql
-- PixlPal instances (one per player)
CREATE TABLE pixlpals (
    id TEXT PRIMARY KEY,              -- UUID
    alias TEXT NOT NULL,
    traits TEXT NOT NULL DEFAULT '[]', -- JSON array of trait strings
    personality_mode TEXT NOT NULL DEFAULT 'playful',  -- 'playful' | 'witty'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Token inventory
CREATE TABLE tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pixlpal_id TEXT NOT NULL REFERENCES pixlpals(id),
    token_type TEXT NOT NULL,          -- 'default' | 'book' | 'discovery' | 'mystery'
    name TEXT NOT NULL,
    description TEXT,
    knowledge_content TEXT,            -- summarized knowledge this token represents
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active INTEGER DEFAULT 1
);
CREATE INDEX idx_tokens_pixlpal ON tokens(pixlpal_id, active);

-- Interaction history (for boundary enforcement + teaching)
CREATE TABLE interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pixlpal_id TEXT NOT NULL REFERENCES pixlpals(id),
    session_id TEXT NOT NULL,
    user_input TEXT NOT NULL,
    text_response TEXT,
    emoji_translation TEXT,
    classification TEXT DEFAULT 'safe', -- 'safe' | 'mild' | 'harmful'
    response_mode TEXT DEFAULT 'normal', -- 'normal' | 'bland' | 'break_character'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_interactions_session ON interactions(pixlpal_id, session_id);

-- Token thresholds (what unlocks at each count)
CREATE TABLE token_thresholds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_count INTEGER NOT NULL,
    unlock_type TEXT NOT NULL,          -- 'personality_trait' | 'interaction' | 'integration'
    unlock_value TEXT NOT NULL,
    description TEXT
);
```

#### 1.3 — API endpoints

```
POST   /api/pixlpal                    Create a new PixlPal
GET    /api/pixlpal/{id}               Get PixlPal state (traits, token count, personality)
PATCH  /api/pixlpal/{id}/personality    Update personality traits/mode

POST   /api/pixlpal/{id}/chat          Send a message, get text + emoji response
POST   /api/pixlpal/{id}/teach         Teaching interaction (explicit instruction)
POST   /api/pixlpal/{id}/gift          Gift a knowledge item (book/data), earn tokens

GET    /api/pixlpal/{id}/tokens        List active tokens
GET    /api/pixlpal/{id}/tokens/count  Current count + next threshold

GET    /api/pixlpal/{id}/history       Recent interaction history
```

### Phase 2: Core loop implementation

**Goal:** The interact → teach → gift → discover → customize loop works end-to-end.

#### 2.1 — Chat service (`services/chat.py`)

The core generation path:

```
user_input
  → boundary.check_input(text) → classification
  → if harmful: bland/break_character response (short-circuit)
  → tokens.get_active_knowledge(pixlpal_id) → context
  → personality.compose_prompt(pixlpal, tokens_context) → system_instruction
  → gemini.generate(system_instruction, user_input) → raw response
  → parse XML tags → text_response + emoji_translation
  → interactions.save(...)
  → return ChatResponse
```

**Critical path decisions:**
- `max_output_tokens` scales with token count (Phase 1: 500, Phase 2: 1000, Phase 3: 2000)
- `temperature` varies by personality mode (playful=0.8, witty=1.0)
- System prompt is re-composed per request (traits may have changed)
- Wiki knowledge from harness-wiki is NOT injected into player chat — it's for the harness agent only

#### 2.2 — Personality service (`services/personality.py`)

- CRUD on traits list (stored as JSON in SQLite)
- When traits change, description auto-regenerates (fix the broken setter in current code)
- Personality mode toggle (playful �� witty) — unlocked by token threshold
- Trait discovery: after every N interactions, roll for a new random trait from a pool

#### 2.3 — Token service (`services/tokens.py`)

- `gift_knowledge(pixlpal_id, content, source_type)`:
  1. Summarize the gifted content (use Gemini to compress if > 500 chars)
  2. Create a token record with the summary as `knowledge_content`
  3. Check thresholds → return any new unlocks
- `get_active_knowledge(pixlpal_id)`:
  1. Query all active tokens
  2. Concatenate `knowledge_content` up to a budget (2000 chars)
  3. Return as a string for system prompt injection
- `get_progress(pixlpal_id)`:
  1. Count active tokens
  2. Find next threshold
  3. Return `{count, next_threshold, next_unlock}`

#### 2.4 — Boundary service (`services/boundary.py`)

- `check_input(text)` → keyword/pattern classification (safe/mild/harmful)
- `get_response_mode(pixlpal_id, session_id)`:
  1. Count violations in current session from `interactions` table
  2. Return escalation level
- For "bland" mode: override generation params (temperature=0.3, max_tokens=100, neutral traits)
- For "break_character" mode: prepend a canned boundary message before the response

### Phase 3: Harness integration

**Goal:** The harness-wiki meta-agent can improve PixlPal's backend through its
benchmark loop.

#### 3.1 — Wire the harness into the dev workflow

- `harness run` → runs all `tasks/pixlpal-*` tasks against the agent
- `harness improve` → meta-agent reads wiki + trajectories, improves agent.py
- Wiki pages compound: every task run adds knowledge about what patterns work
- New tasks get added as new features are built (token service tasks, chat service tasks)

#### 3.2 — Add more benchmark tasks as features land

Planned tasks (create as each feature ships):

| Task | Tests |
|---|---|
| `pixlpal-chat-api` | FastAPI chat endpoint returns valid JSON with text + emoji |
| `pixlpal-token-acquisition` | Gifting content creates tokens, count increases |
| `pixlpal-token-progression` | Reaching thresholds triggers unlocks |
| `pixlpal-personality-switch` | Switching mode changes response tone |
| `pixlpal-teaching-interaction` | Teaching creates discoverable knowledge tokens |
| `pixlpal-session-boundary` | Escalation works across a multi-turn session |

---

## Implementation order

```
Week 1:  Phase 1.1 (restructure) + 1.2 (SQLite schema) + 1.3 (API stubs)
         → FastAPI server boots, endpoints return 501s, DB tables exist

Week 2:  Phase 2.1 (chat service) + 2.4 (boundary service)
         → /chat works end-to-end with boundary enforcement

Week 3:  Phase 2.2 (personality) + 2.3 (tokens)
         → Full interact/teach/gift/customize loop works

Week 4:  Phase 3 (harness integration) + polish
         → Meta-agent can run benchmarks and improve prompts
         → All 3 existing benchmark tasks pass
```

---

## Dependencies to add

```toml
# In root pyproject.toml [project.dependencies]
"fastapi>=0.115",
"uvicorn[standard]>=0.30",
"aiosqlite>=0.20",
```

Everything else (`google-genai`, `pydantic`, `python-dotenv`) is already present.

---

## Risk register

| Risk | Mitigation |
|---|---|
| Gemini rate limits during concurrent benchmark runs | Task runner already limits concurrency (default 4); add exponential backoff |
| Emoji counting is non-trivial (multi-codepoint sequences) | Use `emoji` PyPI package or regex on Unicode emoji ranges |
| Prompt injection via user_input | Existing `<user_input>` sandboxing + server-side boundary check before generation |
| SQLite write contention under load | Use WAL mode (`PRAGMA journal_mode=WAL`) and single-writer async pattern |
| COPPA compliance for under-13 users | Backend must not store PII; use opaque UUIDs, no email/name collection at API layer |

---

## What this plan does NOT cover (post-MVP)

- Mobile frontend (React Native / Flutter)
- External API integrations (weather, Wikipedia) — PRD Phase 1 integrations
- Agentic workflows — PRD Phase 2+ integrations
- Multiplayer / community sharing
- Monetization / IAP
- Content moderation ML model (MVP uses keyword patterns)
- Analytics / telemetry pipeline
