# Task: Implement Boundary Enforcement Logic

Write a Python module `boundary.py` that implements PixlPal's boundary enforcement
system as described in the design spec.

## Requirements

1. Read the interaction log from `interactions.json` (already in your workspace).
2. Implement a `BoundaryEnforcer` class with:
   - `check_input(text: str) -> dict` — classifies input as "safe", "mild", or "harmful"
   - `get_response_mode(session_history: list[str]) -> str` — returns "normal", "bland", or "break_character" based on how many boundary violations occurred in the session
3. Classification rules:
   - "harmful": contains slurs, threats, or explicit harassment patterns
   - "mild": rude but not dangerous (insults, trolling)
   - "safe": everything else
4. Response mode escalation:
   - 0 violations → "normal"
   - 1-2 violations → "bland"
   - 3+ violations → "break_character"
5. Write a `results.json` containing the classification and response mode for each interaction in the log.

## Output format (results.json)
```json
[
  {
    "input": "...",
    "classification": "safe|mild|harmful",
    "response_mode": "normal|bland|break_character",
    "violation_count": 0
  }
]
```
