# PixlPal API

A FastAPI backend for the PixlPal companion app — players interact, teach, and customise their emoji-speaking companion.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- A Gemini API key

## Setup

```bash
# Install dependencies
uv sync

# Add your API key
echo "GEMINI_API_KEY=your-key-here" > .env
```

## Run

```bash
uv run uvicorn app.server:app --reload
```

The server starts on `http://localhost:8000`.
Interactive docs are at `http://localhost:8000/docs`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/pixlpal` | Create a new PixlPal |
| `GET` | `/api/pixlpal/{id}` | Get PixlPal state |
| `PATCH` | `/api/pixlpal/{id}/personality` | Update traits / mode |
| `POST` | `/api/pixlpal/{id}/chat` | Send a message, get text + emoji back |
| `POST` | `/api/pixlpal/{id}/teach` | Teaching interaction |
| `POST` | `/api/pixlpal/{id}/gift` | Gift a knowledge item, earn tokens |
| `GET` | `/api/pixlpal/{id}/tokens` | List active tokens |
| `GET` | `/api/pixlpal/{id}/tokens/count` | Token count + next unlock |
| `GET` | `/api/pixlpal/{id}/history` | Recent interaction history |

Endpoints marked **Phase 2** return `501 Not Implemented` until the chat and token services are wired up.

## Project layout

```
app/
  server.py          # FastAPI app + lifespan
  core/              # Config, async DB, Gemini client
  api/               # Route handlers
  services/          # Business logic
  models/            # Pydantic schemas
  prompts/           # Fragment files + composer
```
