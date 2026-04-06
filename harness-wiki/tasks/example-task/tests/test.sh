#!/usr/bin/env bash
# Verifier for example-task
# Writes a score 0.0-1.0 to $LOGS_DIR/reward.txt

set -euo pipefail

REWARD_FILE="${LOGS_DIR}/reward.txt"
OUTPUT="${WORKSPACE}/output.json"

score=0.0

# Check output file exists
if [[ ! -f "$OUTPUT" ]]; then
    echo "FAIL: output.json not found"
    echo "0.0" > "$REWARD_FILE"
    exit 0
fi

# Check it's valid JSON
if ! python3 -c "import json; json.load(open('$OUTPUT'))" 2>/dev/null; then
    echo "FAIL: output.json is not valid JSON"
    echo "0.0" > "$REWARD_FILE"
    exit 0
fi

# Check 'the' appears and has count >= 3
THE_COUNT=$(python3 -c "
import json
data = json.load(open('$OUTPUT'))
print(data.get('the', 0))
")

if [[ "$THE_COUNT" -ge 3 ]]; then
    score=0.5
fi

# Check 'dog' has count >= 2
DOG_COUNT=$(python3 -c "
import json
data = json.load(open('$OUTPUT'))
print(data.get('dog', 0))
")

if [[ "$DOG_COUNT" -ge 2 ]]; then
    score=$(python3 -c "print($score + 0.25)")
fi

# Check output is sorted descending
IS_SORTED=$(python3 -c "
import json
data = json.load(open('$OUTPUT'))
vals = list(data.values())
print('yes' if vals == sorted(vals, reverse=True) else 'no')
")

if [[ "$IS_SORTED" == "yes" ]]; then
    score=$(python3 -c "print($score + 0.25)")
fi

echo "$score" > "$REWARD_FILE"
echo "Score: $score"
