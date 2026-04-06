"""
harness_wiki/cli.py
===================
CLI entry points for harness-wiki.
"""

from __future__ import annotations

import os
from pathlib import Path

import typer

app = typer.Typer(
    name="harness",
    help="harness-wiki: self-optimizing agent harness with persistent wiki memory",
    no_args_is_help=True,
)

REPO_ROOT = Path(__file__).parent.parent
WIKI_DIR = Path.home() / "Vault"


@app.command()
def run(
    task_name: str = typer.Option(None, "--task", "-t", help="Run a specific task by name."),
    concurrency: int = typer.Option(4, "--concurrency", "-n", help="Parallel task workers."),
    tasks_dir: Path = typer.Option(REPO_ROOT / "tasks", "--tasks-dir"),
    jobs_dir: Path = typer.Option(REPO_ROOT / "jobs", "--jobs-dir"),
) -> None:
    """Run the task benchmark suite."""
    from harness_wiki.runner import run_suite

    jobs_dir.mkdir(parents=True, exist_ok=True)
    run_suite(
        tasks_dir=tasks_dir,
        jobs_dir=jobs_dir,
        concurrency=concurrency,
        task_name=task_name,
    )


@app.command()
def improve(
    iterations: int = typer.Option(5, "--iterations", "-i"),
    concurrency: int = typer.Option(4, "--concurrency", "-n"),
) -> None:
    """Run the meta-agent improvement loop (requires GEMINI_API_KEY)."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "meta"))
    from meta.runner import run_improvement_loop
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    run_improvement_loop(client, iterations=iterations, concurrency=concurrency)


@app.command()
def wiki_lint() -> None:
    """Health-check the wiki: find orphans, stale refs, missing cross-links."""
    from harness_wiki.wiki import lint_wiki

    wiki_dir = WIKI_DIR
    issues = lint_wiki(wiki_dir)
    if not issues:
        typer.echo("Wiki is healthy. No issues found.")
    else:
        for issue in issues:
            typer.echo(f"  {issue}")
        raise typer.Exit(1)


@app.command()
def wiki_show(
    query: str = typer.Argument(..., help="Keywords to search the wiki for."),
) -> None:
    """Query the wiki index for relevant pages."""
    wiki_dir = WIKI_DIR
    index = wiki_dir / "index.md"
    if not index.exists():
        typer.echo("Wiki is empty.")
        raise typer.Exit(1)

    text = index.read_text(encoding="utf-8")
    hits = [l for l in text.splitlines() if query.lower() in l.lower()]
    if not hits:
        typer.echo(f"No pages matching '{query}'.")
    else:
        for h in hits:
            typer.echo(h)


if __name__ == "__main__":
    app()
