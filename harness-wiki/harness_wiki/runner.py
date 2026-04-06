"""
harness_wiki/runner.py
======================
Task runner: loads tasks from tasks/, instantiates agent.py's AutoAgent interface,
runs each task in the sandbox workspace, collects scores, writes job outputs.

This is the adapter between tasks/ and agent.py.
It is NOT the file under test — it calls into agent.py.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from google import genai
import structlog
import tomli

log = structlog.get_logger()

REPO_ROOT = Path(__file__).parent.parent
AGENT_PATH = REPO_ROOT / "agent.py"
WIKI_DIR = Path.home() / "Vault"


def load_agent_module():
    """Dynamically load agent.py so meta-agent edits are picked up at runtime."""
    spec = importlib.util.spec_from_file_location("agent", AGENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_task(task_dir: Path) -> dict:
    """Load task config and instruction from a task directory."""
    config_path = task_dir / "task.toml"
    instruction_path = task_dir / "instruction.md"

    config = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomli.load(f)

    instruction = ""
    if instruction_path.exists():
        instruction = instruction_path.read_text(encoding="utf-8")

    return {
        "name": task_dir.name,
        "config": config,
        "instruction": instruction,
        "task_dir": task_dir,
    }


def run_verifier(task_dir: Path, workspace: Path, logs_dir: Path) -> float:
    """Run the task verifier. Returns score 0.0–1.0."""
    test_sh = task_dir / "tests" / "test.sh"
    if not test_sh.exists():
        log.warning("no_verifier_found", task=task_dir.name)
        return 0.0

    reward_path = logs_dir / "reward.txt"
    env = {
        **os.environ,
        "WORKSPACE": str(workspace),
        "LOGS_DIR": str(logs_dir),
        "TASK_DIR": str(task_dir),
    }

    result = subprocess.run(
        ["bash", str(test_sh)],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=str(workspace),
    )

    # Verifier writes score to /logs/reward.txt
    if reward_path.exists():
        try:
            score = float(reward_path.read_text(encoding="utf-8").strip())
            return max(0.0, min(1.0, score))
        except ValueError:
            pass

    # Fall back to exit code
    return 1.0 if result.returncode == 0 else 0.0


def run_one_task(task: dict, jobs_dir: Path, wiki_dir: Path) -> dict:
    """Run a single task and return its result."""
    task_name = task["name"]
    job_dir = jobs_dir / task_name
    job_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = job_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Create a fresh workspace for the task
    with tempfile.TemporaryDirectory(prefix=f"hw_{task_name}_") as tmpdir:
        workspace = Path(tmpdir)

        # Copy task reference files into workspace
        env_files = task["task_dir"] / "environment" / "files"
        if env_files.exists():
            for f in env_files.iterdir():
                shutil.copy2(f, workspace / f.name)

        # Load agent module fresh (picks up any edits)
        try:
            agent_module = load_agent_module()
        except Exception as e:
            log.error("agent_load_failed", task=task_name, error=str(e))
            return {"task": task_name, "score": 0.0, "passed": False, "error": str(e)}

        # Build client + agent
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        tools = agent_module.create_tools(workspace, wiki_dir)
        agent = agent_module.create_agent(client, tools, agent_module.SYSTEM_PROMPT, agent_module.MODEL)

        # Run task
        timeout_sec = task["config"].get("timeout", 300)
        try:
            result = agent_module.run_task(
                agent=agent,
                instruction=task["instruction"],
                workspace=workspace,
                wiki_dir=wiki_dir,
                max_turns=agent_module.MAX_TURNS,
            )
        except Exception as e:
            log.error("task_run_error", task=task_name, error=str(e))
            result = {"success": False, "output": str(e), "trajectory": []}

        # Write trajectory
        traj_path = job_dir / "trajectory.json"
        traj_path.write_text(
            json.dumps({
                "task": task_name,
                "instruction": task["instruction"],
                "result": result.get("output", ""),
                "trajectory": result.get("trajectory", []),
            }, indent=2),
            encoding="utf-8",
        )

        # Run verifier
        score = run_verifier(task["task_dir"], workspace, logs_dir)

        # Update trajectory with score
        traj_data = json.loads(traj_path.read_text(encoding="utf-8"))
        traj_data["score"] = score
        traj_path.write_text(json.dumps(traj_data, indent=2), encoding="utf-8")

        log.info("task_complete", task=task_name, score=score)
        return {
            "task": task_name,
            "score": score,
            "passed": score >= 0.5,
        }


def run_suite(
    tasks_dir: Path = REPO_ROOT / "tasks",
    jobs_dir: Path = REPO_ROOT / "jobs",
    wiki_dir: Path = WIKI_DIR,
    concurrency: int = 4,
    task_name: str | None = None,
) -> list[dict]:
    """Run all tasks (or a single named task) in the task suite."""
    if not tasks_dir.exists():
        log.error("tasks_dir_not_found", path=str(tasks_dir))
        return []

    # Discover tasks
    all_task_dirs = sorted(
        [d for d in tasks_dir.iterdir() if d.is_dir() and (d / "instruction.md").exists()]
    )

    if task_name:
        all_task_dirs = [d for d in all_task_dirs if d.name == task_name]

    if not all_task_dirs:
        log.warning("no_tasks_found", tasks_dir=str(tasks_dir))
        return []

    tasks = [load_task(d) for d in all_task_dirs]
    log.info("running_tasks", count=len(tasks), concurrency=concurrency)

    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(run_one_task, t, jobs_dir, wiki_dir): t for t in tasks}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                task = futures[future]
                log.error("task_future_error", task=task["name"], error=str(e))
                results.append({"task": task["name"], "score": 0.0, "passed": False})

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    avg_score = sum(r["score"] for r in results) / total if total else 0.0

    print(f"SUMMARY: passed={passed} | total={total} | avg_score={avg_score:.4f}")
    return results


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks-dir", default=str(REPO_ROOT / "tasks"))
    parser.add_argument("--jobs-dir", default=str(REPO_ROOT / "jobs"))
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--task-name", default=None)
    args = parser.parse_args()

    run_suite(
        tasks_dir=Path(args.tasks_dir),
        jobs_dir=Path(args.jobs_dir),
        concurrency=args.concurrency,
        task_name=args.task_name,
    )


if __name__ == "__main__":
    main()
