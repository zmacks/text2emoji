"""
harness-wiki: agent.py
======================
The task agent harness. This is the primary edit surface for the meta-agent.

STRUCTURE
---------
Everything above the FIXED ADAPTER BOUNDARY is editable by the meta-agent:
  - SYSTEM_PROMPT      : the agent's instructions
  - MODEL              : which Gemini model to use
  - MAX_TURNS          : agentic loop limit
  - create_tools()     : tool definitions (add/remove/modify freely)
  - create_agent()     : agent construction (sub-agents, handoffs)
  - run_task()         : orchestration logic

Everything below the FIXED ADAPTER BOUNDARY is infrastructure.
Do NOT modify below unless the human explicitly asks.

MEMORY INTEGRATION
------------------
The agent has access to a persistent wiki at wiki/ relative to the workspace.
On each task start the agent loads wiki/index.md and relevant pages.
After task completion the agent updates the wiki with what it learned.
The wiki is the agent's long-term memory across runs; treat it carefully.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# EDITABLE HARNESS SECTION -- meta-agent edits everything below this line
# until the FIXED ADAPTER BOUNDARY comment.
# ---------------------------------------------------------------------------

MODEL = "gemini-2.5-flash"
MAX_TURNS = 40

SYSTEM_PROMPT = """\
You are a capable autonomous agent working inside a sandboxed Linux environment.

You receive a natural-language task instruction and must complete it correctly.
You have access to a persistent wiki that holds accumulated knowledge from prior
runs. Always consult the wiki before starting a task -- it may contain shortcuts,
known failure modes, or solved sub-problems relevant to your current work.

After completing a task, always call update_wiki with a concise summary of:
  - What you did and why
  - Any tools or techniques that worked well
  - Any gotchas or failure modes you encountered

This keeps the wiki useful for future runs. Do not skip this step.

Work methodically. If a step fails, diagnose before retrying. Produce the
correct final artifact or system state as specified in the task instruction.
"""


def create_tools(workspace: Path, wiki_dir: Path) -> list[dict]:
    """
    Define the tool schemas available to the task agent.
    The meta-agent may add, remove, or modify tools here.

    Returns a list of dicts with keys: name, description, parameters.
    These are converted to Gemini FunctionDeclarations at call time.
    """
    return [
        {
            "name": "bash",
            "description": (
                "Execute a bash command in the task workspace. "
                "Working directory is set to the task workspace. "
                "Returns stdout, stderr, and exit code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to run.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default 30).",
                    },
                },
                "required": ["command"],
            },
        },
        {
            "name": "read_file",
            "description": "Read a file from the task workspace or wiki.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Relative path from workspace root, or "
                            "'wiki/<page>.md' to read from the wiki."
                        ),
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "write_file",
            "description": "Write content to a file in the task workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from workspace root.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
        {
            "name": "list_files",
            "description": "List files in a directory within the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from workspace root (default '.').",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "query_wiki",
            "description": (
                "Search the wiki index for pages relevant to a query. "
                "Returns matching page names and one-line summaries. "
                "Use this before starting a task to find relevant prior knowledge."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords or topic to search for.",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "update_wiki",
            "description": (
                "Write or update a page in the persistent wiki. "
                "Call this after task completion to record what you learned. "
                "Page content should be concise markdown. "
                "The wiki index will be updated automatically."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page_name": {
                        "type": "string",
                        "description": (
                            "Short slug for the page, e.g. 'python-csv-parsing' "
                            "or 'bash-file-search-patterns'."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": "Markdown content for the wiki page.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "One-line summary for the index.",
                    },
                },
                "required": ["page_name", "content", "summary"],
            },
        },
    ]


def create_agent(
    client: genai.Client,
    tools: list[dict],
    system: str,
    model: str,
) -> dict:
    """
    Agent configuration bundle. The meta-agent may modify this to add
    sub-agents, change the model, or alter construction.
    """
    # Convert plain-dict tool definitions to Gemini FunctionDeclarations
    function_declarations = [
        types.FunctionDeclaration(
            name=t["name"],
            description=t["description"],
            parameters=t["parameters"],
        )
        for t in tools
    ]

    return {
        "client": client,
        "function_declarations": function_declarations,
        "system": system,
        "model": model,
    }


def run_task(
    agent: dict,
    instruction: str,
    workspace: Path,
    wiki_dir: Path,
    max_turns: int = MAX_TURNS,
) -> dict:
    """
    Orchestration loop. Runs the agent against a task instruction.
    Returns a result dict with keys: success, output, trajectory.

    Uses Gemini's function-calling protocol:
      1. Send user message with tool declarations
      2. If the model responds with function_call parts, execute them
      3. Return function_response parts and loop
      4. If no function_call parts, extract text and finish
    """
    client: genai.Client = agent["client"]
    trajectory: list[dict] = []

    # Load wiki index as context
    wiki_context = _load_wiki_context(wiki_dir)
    augmented_instruction = (
        f"{instruction}\n\n---\nWiki context (accumulated prior knowledge):\n"
        f"{wiki_context}"
    ) if wiki_context else instruction

    # Build Gemini config with tools and system instruction
    config = types.GenerateContentConfig(
        system_instruction=agent["system"],
        tools=[types.Tool(function_declarations=agent["function_declarations"])],
        max_output_tokens=4096,
    )

    # Conversation history as a list of Content objects
    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=augmented_instruction)],
        )
    ]

    for turn in range(max_turns):
        response = client.models.generate_content(
            model=agent["model"],
            config=config,
            contents=contents,
        )

        trajectory.append({"turn": turn, "response": _serialize_response(response)})

        candidate = response.candidates[0]
        model_content = candidate.content

        # Append the model's response to the conversation history
        contents.append(model_content)

        # Check if the model made any function calls
        function_calls = [
            part for part in model_content.parts
            if part.function_call is not None
        ]

        if not function_calls:
            # No function calls -- the model is done
            output = _extract_text(model_content)
            return {"success": True, "output": output, "trajectory": trajectory}

        # Execute each function call and collect results
        result_parts: list[types.Part] = []
        for part in function_calls:
            fc = part.function_call
            tool_args = dict(fc.args) if fc.args else {}
            result = _dispatch_tool(fc.name, tool_args, workspace, wiki_dir)
            result_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result},
                )
            )

        # Append tool results as a user turn
        contents.append(types.Content(role="user", parts=result_parts))

    return {
        "success": False,
        "output": f"Exceeded max_turns ({max_turns})",
        "trajectory": trajectory,
    }


# ---------------------------------------------------------------------------
# FIXED ADAPTER BOUNDARY -- do NOT modify below this line.
# This section handles tool dispatch, wiki I/O, and trajectory serialization.
# ---------------------------------------------------------------------------


def _dispatch_tool(
    name: str, inputs: dict, workspace: Path, wiki_dir: Path
) -> str:
    """Route tool calls to their implementations."""
    try:
        if name == "bash":
            return _tool_bash(inputs, workspace)
        elif name == "read_file":
            return _tool_read_file(inputs, workspace, wiki_dir)
        elif name == "write_file":
            return _tool_write_file(inputs, workspace)
        elif name == "list_files":
            return _tool_list_files(inputs, workspace)
        elif name == "query_wiki":
            return _tool_query_wiki(inputs, wiki_dir)
        elif name == "update_wiki":
            return _tool_update_wiki(inputs, wiki_dir)
        else:
            return f"Error: unknown tool '{name}'"
    except Exception as exc:
        return f"Error in tool '{name}': {exc}"


def _tool_bash(inputs: dict, workspace: Path) -> str:
    command = inputs["command"]
    timeout = int(inputs.get("timeout", 30))
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(workspace),
    )
    parts = []
    if result.stdout:
        parts.append(f"stdout:\n{result.stdout.rstrip()}")
    if result.stderr:
        parts.append(f"stderr:\n{result.stderr.rstrip()}")
    parts.append(f"exit_code: {result.returncode}")
    return "\n".join(parts)


def _tool_read_file(inputs: dict, workspace: Path, wiki_dir: Path) -> str:
    path_str: str = inputs["path"]
    if path_str.startswith("wiki/"):
        target = wiki_dir / path_str[5:]
    else:
        target = workspace / path_str
    if not target.exists():
        return f"Error: file not found: {path_str}"
    return target.read_text(encoding="utf-8")


def _tool_write_file(inputs: dict, workspace: Path) -> str:
    target = workspace / inputs["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(inputs["content"], encoding="utf-8")
    return f"Written {len(inputs['content'])} bytes to {inputs['path']}"


def _tool_list_files(inputs: dict, workspace: Path) -> str:
    rel = inputs.get("path", ".")
    target = workspace / rel
    if not target.exists():
        return f"Error: directory not found: {rel}"
    entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
    lines = [f"{'d' if e.is_dir() else 'f'}  {e.name}" for e in entries]
    return "\n".join(lines) if lines else "(empty directory)"


def _tool_query_wiki(inputs: dict, wiki_dir: Path) -> str:
    query = inputs["query"].lower()
    index_path = wiki_dir / "index.md"
    if not index_path.exists():
        return "Wiki is empty. No prior knowledge found."
    index_text = index_path.read_text(encoding="utf-8")
    # Simple keyword match over index lines
    matches = []
    for line in index_text.splitlines():
        if query in line.lower():
            matches.append(line)
    if not matches:
        return f"No wiki pages matched '{inputs['query']}'."
    return "Matching wiki entries:\n" + "\n".join(matches)


def _tool_update_wiki(inputs: dict, wiki_dir: Path) -> str:
    page_name: str = inputs["page_name"].strip().lower().replace(" ", "-")
    content: str = inputs["content"]
    summary: str = inputs["summary"]

    # Write page
    page_path = wiki_dir / f"{page_name}.md"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    page_path.write_text(content, encoding="utf-8")

    # Update index.md
    index_path = wiki_dir / "index.md"
    _update_index(index_path, page_name, summary)

    # Append to log.md
    log_path = wiki_dir / "log.md"
    _append_log(log_path, page_name, summary)

    return f"Wiki page '{page_name}.md' written and index updated."


def _load_wiki_context(wiki_dir: Path) -> str:
    """Load the wiki index as context for the agent."""
    index_path = wiki_dir / "index.md"
    if not index_path.exists():
        return ""
    text = index_path.read_text(encoding="utf-8")
    # Return first 2000 chars to stay within context budget (L1 layer per Karpathy)
    return text[:2000]


def _update_index(index_path: Path, page_name: str, summary: str) -> None:
    """Add or update a page entry in index.md."""
    entry = f"- [[{page_name}]] -- {summary}"
    if not index_path.exists():
        index_path.write_text(
            "# Wiki Index\n\nLLM-maintained knowledge base.\n\n## Pages\n\n" + entry + "\n",
            encoding="utf-8",
        )
        return
    text = index_path.read_text(encoding="utf-8")
    # Remove existing entry for this page if present
    lines = [line for line in text.splitlines() if f"[[{page_name}]]" not in line]
    lines.append(entry)
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_log(log_path: Path, page_name: str, summary: str) -> None:
    """Append a timestamped entry to log.md."""
    import datetime

    ts = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = f"## [{ts}] update | {page_name}\n\n{summary}\n\n"
    if not log_path.exists():
        log_path.write_text(
            "# Wiki Log\n\nAppend-only record of wiki changes.\n\n", encoding="utf-8"
        )
    with log_path.open("a", encoding="utf-8") as f:
        f.write(entry)


def _serialize_response(response: Any) -> dict:
    """Serialize a Gemini response for trajectory storage."""
    candidate = response.candidates[0]
    usage = response.usage_metadata
    return {
        "finish_reason": str(candidate.finish_reason),
        "usage": {
            "input": usage.prompt_token_count if usage else 0,
            "output": usage.candidates_token_count if usage else 0,
        },
        "content": [
            {
                "type": "function_call" if part.function_call else "text",
                "text": part.text if part.text else None,
                "tool_name": part.function_call.name if part.function_call else None,
                "tool_input": (
                    dict(part.function_call.args)
                    if part.function_call and part.function_call.args
                    else None
                ),
            }
            for part in candidate.content.parts
        ],
    }


def _extract_text(content: Any) -> str:
    """Extract text from a Gemini Content object."""
    return " ".join(
        part.text for part in content.parts if part.text
    ).strip()
