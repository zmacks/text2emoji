.DEFAULT_GOAL := help

# ── Project config ────────────────────────────────────────────────────────────
APP_MODULE  := app.server:app
MAIN_SCRIPT := app/main.py
DB_FILE     := pixlpal.db
HOST        := 127.0.0.1
PORT        := 8000

# Generated artifact files that should not be committed
ARTIFACT_TXT := app/prompts/bratty_answer.txt \
                app/prompts/golden_retriever_answer.txt \
                app/prompts/system_prompt_created.txt

# ── Help ──────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  text2emoji / PixlPal — available commands"
	@echo ""
	@echo "  Setup"
	@echo "    make install        Install all dependencies via uv"
	@echo ""
	@echo "  Run"
	@echo "    make dev            Start FastAPI server with hot-reload"
	@echo "    make run            Start FastAPI server (production mode)"
	@echo "    make script         Run app/main.py directly (Gemini script)"
	@echo ""
	@echo "  Test"
	@echo "    make test           Run the full test suite"
	@echo "    make test-v         Run tests with verbose output"
	@echo ""
	@echo "  Clean"
	@echo "    make clean-txt      Remove generated prompt/answer .txt files"
	@echo "    make clean-db       Remove SQLite database + WAL/shm files"
	@echo "    make clean-cache    Remove __pycache__ and .pyc bytecode"
	@echo "    make clean          Run all clean targets"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────
.PHONY: install
install:
	uv sync

# ── Run ───────────────────────────────────────────────────────────────────────
.PHONY: dev
dev:
	uv run uvicorn $(APP_MODULE) --reload --host $(HOST) --port $(PORT)

.PHONY: run
run:
	uv run uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT)

.PHONY: script
script:
	uv run python $(MAIN_SCRIPT)

# ── Test ──────────────────────────────────────────────────────────────────────
.PHONY: test
test:
	uv run pytest tests/

.PHONY: test-v
test-v:
	uv run pytest tests/ -v

# ── Clean ─────────────────────────────────────────────────────────────────────
.PHONY: clean-txt
clean-txt:
	@echo "Removing generated prompt/answer files…"
	@rm -f $(ARTIFACT_TXT)
	@echo "Done."

.PHONY: clean-db
clean-db:
	@echo "Removing SQLite database and WAL files…"
	@rm -f $(DB_FILE) $(DB_FILE)-wal $(DB_FILE)-shm
	@echo "Done."

.PHONY: clean-cache
clean-cache:
	@echo "Removing Python bytecode and caches…"
	@find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -path ./.venv -prune -o -name "*.pyc" -delete 2>/dev/null || true
	@echo "Done."

.PHONY: clean
clean: clean-txt clean-db clean-cache
