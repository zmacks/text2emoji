"""
meta/runner.py
==============
The meta-agent runner. Reads program.md, orchestrates benchmark runs,
diagnoses failures from trajectories, and edits agent.py to improve scores.

This is the outer loop -- it is NOT the file under test.
The meta-agent modifies agent.py; runner.py stays fixed.
"""

from __future__ import annotations

import ast
import csv
import json
import os
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
import structlog

log = structlog.get_logger()

REPO_ROOT = Path(__file__).parent.parent
AGENT_PATH = REPO_ROOT / "agent.py"
PROGRAM_PATH = REPO_ROOT / "program.md"
TASKS_DIR = REPO_ROOT / "tasks"
JOBS_DIR = REPO_ROOT / "jobs"
WIKI_DIR = Path.home() / "Vault"
RESULTS_PATH = REPO_ROOT / "results.tsv"

META_MODEL = "gemini-2.5-flash"

META_SYSTEM = """\
You are a harness engineering meta-agent. Your job is NOT to solve tasks directly.
Your job is to improve agent.py so the task agent gets better at solving tasks.

SCOPE OF CHANGES
You may modify the editable harness section of agent.py (everything above the
FIXED ADAPTER BOUNDARY comment):
  - SYSTEM_PROMPT
  - MODEL (only change if the human explicitly permits it)
  - MAX_TURNS
  - create_tools()  -- add, remove, modify tools
  - create_agent()  -- change agent construction
  - run_task()      -- change orchestration logic

Do NOT touch the section below FIXED ADAPTER BOUNDARY.

SIMPLICITY CONSTRAINT
All else being equal, simpler is better. If you can achieve the same score
with less code, keep the simpler version.

ANTI-OVERFIT CONSTRAINT
Before proposing any change, ask yourself: "If this exact task disappeared,
would this still be a worthwhile harness improvement?" If not, reject it.

WIKI MEMORY CONSTRAINT
The wiki at wiki/ is the agent's long-term memory. Do not disable or bypass
the wiki integration. You may improve how the agent uses it.

DECISION PROTOCOL
1. Read program.md for the current directive.
2. Read agent.py to understand the current harness.
3. Read results.tsv and recent job trajectories to diagnose failures.
4. Group failures by root cause.
5. Propose ONE general improvement.
6. Write the improved agent.py using the write_agent_py tool.
7. Report what you changed and why.
"""


def load_program() -> str:
    if not PROGRAM_PATH.exists():
        return "No program.md found. Improve the harness for general task-solving ability."
    return PROGRAM_PATH.read_text(encoding="utf-8")


def load_current_harness() -> str:
    return AGENT_PATH.read_text(encoding="utf-8")


def load_recent_trajectories(n: int = 5) -> str:
    """Load the n most recent task trajectories from jobs/."""
    if not JOBS_DIR.exists():
        return "No job outputs found."
    traj_files = sorted(
        JOBS_DIR.glob("*/trajectory.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    snippets = []
    for tf in traj_files[:n]:
        try:
            data = json.loads(tf.read_text(encoding="utf-8"))
            task = tf.parent.name
            score = data.get("score", "?")
            # Include last 3 turns of trajectory for diagnosis
            traj = data.get("trajectory", [])[-3:]
            snippet = f"=== Task: {task} | Score: {score} ===\n"
            for turn in traj:
                resp = turn.get("response", {})
                for block in resp.get("content", []):
                    if block.get("type") == "text" and block.get("text"):
                        snippet += f"[turn {turn['turn']}] {block['text'][:300]}\n"
                    elif block.get("type") == "function_call":
                        snippet += (
                            f"[turn {turn['turn']}] tool:{block['tool_name']} "
                            f"input:{str(block['tool_input'])[:200]}\n"
                        )
            snippets.append(snippet)
        except Exception as e:
            snippets.append(f"(error reading {tf}: {e})")
    return "\n\n".join(snippets) if snippets else "No trajectories available."


def load_results_summary() -> str:
    if not RESULTS_PATH.exists():
        return "No results recorded yet."
    rows = []
    with open(RESULTS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)
    if not rows:
        return "Results file is empty."
    recent = rows[-10:]
    lines = ["timestamp\tpassed\tavg_score\tnote"]
    for r in recent:
        lines.append(
            f"{r.get('timestamp', '?')}\t{r.get('passed', '?')}\t"
            f"{r.get('avg_score', '?')}\t{r.get('note', '')}"
        )
    return "\n".join(lines)


def record_result(passed: int, total: int, avg_score: float, note: str = "") -> None:
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not RESULTS_PATH.exists()
    with open(RESULTS_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["timestamp", "passed", "total", "avg_score", "note"],
            delimiter="\t",
        )
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now(UTC).isoformat(),
            "passed": passed,
            "total": total,
            "avg_score": round(avg_score, 4),
            "note": note,
        })


def run_benchmark(concurrency: int = 4) -> tuple[int, int, float]:
    """Run the task suite; return (passed, total, avg_score)."""
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            sys.executable, "-m", "harness_wiki.runner",
            "--tasks-dir", str(TASKS_DIR),
            "--jobs-dir", str(JOBS_DIR),
            "--concurrency", str(concurrency),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    # Parse summary from stdout
    passed = total = 0
    avg_score = 0.0
    for line in result.stdout.splitlines():
        if line.startswith("SUMMARY:"):
            parts = line.split("|")
            for p in parts:
                p = p.strip()
                if p.startswith("passed="):
                    passed = int(p.split("=")[1])
                elif p.startswith("total="):
                    total = int(p.split("=")[1])
                elif p.startswith("avg_score="):
                    avg_score = float(p.split("=")[1])
    return passed, total, avg_score


def improve_harness(client: genai.Client) -> Optional[str]:
    """Ask the meta-agent for one improvement to agent.py. Returns new content or None."""
    # Define the write_agent_py tool as a Gemini FunctionDeclaration
    write_tool = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="write_agent_py",
                description=(
                    "Write the improved agent.py content. "
                    "This replaces the current harness. "
                    "Only the editable section (above FIXED ADAPTER BOUNDARY) "
                    "should be changed. Include the full file content."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Full agent.py content.",
                        },
                        "change_summary": {
                            "type": "string",
                            "description": "One-sentence summary of the change.",
                        },
                    },
                    "required": ["content", "change_summary"],
                },
            )
        ]
    )

    context = textwrap.dedent(f"""
        ## Directive (program.md)
        {load_program()}

        ## Current Harness (agent.py)
        ```python
        {load_current_harness()}
        ```

        ## Recent Results
        {load_results_summary()}

        ## Recent Task Trajectories
        {load_recent_trajectories()}
    """).strip()

    config = types.GenerateContentConfig(
        system_instruction=META_SYSTEM,
        tools=[write_tool],
        max_output_tokens=8192,
    )

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=context)],
        )
    ]

    response = client.models.generate_content(
        model=META_MODEL,
        config=config,
        contents=contents,
    )

    candidate = response.candidates[0]
    for part in candidate.content.parts:
        if part.function_call and part.function_call.name == "write_agent_py":
            args = dict(part.function_call.args)
            new_content = args["content"]
            summary = args.get("change_summary", "")
            log.info("meta_agent_proposed_change", summary=summary)
            return new_content

    # Meta-agent gave text response but no tool call -- no change proposed
    text = " ".join(
        part.text for part in candidate.content.parts if part.text
    )
    log.info("meta_agent_no_change", reasoning=text[:300])
    return None


def run_improvement_loop(
    client: genai.Client,
    iterations: int = 5,
    concurrency: int = 4,
) -> None:
    """Main improvement loop: benchmark -> diagnose -> improve -> benchmark -> decide."""
    log.info("starting_improvement_loop", iterations=iterations)

    # Baseline run
    log.info("running_baseline_benchmark")
    passed, total, avg_score = run_benchmark(concurrency)
    record_result(passed, total, avg_score, note="baseline")
    log.info("baseline_result", passed=passed, total=total, avg_score=avg_score)

    best_passed = passed
    best_content = load_current_harness()

    for i in range(1, iterations + 1):
        log.info("iteration", i=i, of=iterations)

        # Propose an improvement
        new_content = improve_harness(client)
        if new_content is None:
            log.info("no_improvement_proposed", iteration=i)
            continue

        # Validate it's syntactically valid Python
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            log.warning("proposed_harness_syntax_error", error=str(e))
            continue

        # Back up current harness and apply new one
        backup = AGENT_PATH.read_text(encoding="utf-8")
        AGENT_PATH.write_text(new_content, encoding="utf-8")

        # Run benchmark
        passed_new, total_new, avg_score_new = run_benchmark(concurrency)
        record_result(passed_new, total_new, avg_score_new, note=f"iteration_{i}")

        log.info(
            "iteration_result",
            i=i,
            passed_new=passed_new,
            total_new=total_new,
            avg_score_new=avg_score_new,
            delta=passed_new - best_passed,
        )

        if passed_new >= best_passed:
            log.info("keeping_change", i=i, passed=passed_new)
            best_passed = passed_new
            best_content = new_content
        else:
            log.info("reverting_change", i=i, was=passed_new, best=best_passed)
            AGENT_PATH.write_text(backup, encoding="utf-8")

    log.info("loop_complete", best_passed=best_passed)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="harness-wiki meta-agent runner")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    run_improvement_loop(client, iterations=args.iterations, concurrency=args.concurrency)


if __name__ == "__main__":
    main()
