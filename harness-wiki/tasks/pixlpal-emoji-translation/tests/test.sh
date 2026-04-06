#!/usr/bin/env bash
# Verifier for pixlpal-emoji-translation
set -euo pipefail

REWARD_FILE="${LOGS_DIR}/reward.txt"
PARSED="${WORKSPACE}/parsed.json"
PARSER="${WORKSPACE}/emoji_parser.py"

score=0.0

# Check outputs exist
if [[ ! -f "$PARSED" ]] || [[ ! -f "$PARSER" ]]; then
    echo "FAIL: parsed.json or emoji_parser.py missing"
    echo "0.0" > "$REWARD_FILE"
    exit 0
fi

# Check valid JSON
if ! python3 -c "import json; json.load(open('$PARSED'))" 2>/dev/null; then
    echo "FAIL: parsed.json is not valid JSON"
    echo "0.0" > "$REWARD_FILE"
    exit 0
fi

# Check structure: 5 entries with required fields
STRUCT_OK=$(python3 -c "
import json
data = json.load(open('$PARSED'))
if not isinstance(data, list) or len(data) < 5:
    print('no'); exit()
for item in data:
    if not all(k in item for k in ('text_response', 'emoji_translation', 'is_valid', 'emoji_count')):
        print('no'); exit()
print('yes')
")

if [[ "$STRUCT_OK" == "yes" ]]; then
    score=0.25
fi

# Check valid responses are marked valid
VALID_OK=$(python3 -c "
import json
data = json.load(open('$PARSED'))
# Response 0 and 1 should be valid, 2/3/4 should be invalid
r0_ok = data[0]['is_valid'] == True
r1_ok = data[1]['is_valid'] == True
r2_invalid = data[2]['is_valid'] == False
print('yes' if r0_ok and r1_ok and r2_invalid else 'no')
")

if [[ "$VALID_OK" == "yes" ]]; then
    score=$(python3 -c "print($score + 0.25)")
fi

# Check emoji counts for valid responses
EMOJI_COUNT_OK=$(python3 -c "
import json
data = json.load(open('$PARSED'))
# Response 0 has 5 emoji, response 1 has 5 emoji
r0_count = data[0].get('emoji_count', 0)
r1_count = data[1].get('emoji_count', 0)
print('yes' if r0_count >= 4 and r1_count >= 4 else 'no')
")

if [[ "$EMOJI_COUNT_OK" == "yes" ]]; then
    score=$(python3 -c "print($score + 0.25)")
fi

# Check parser module is importable and has parse function
PARSE_OK=$(python3 -c "
import sys; sys.path.insert(0, '$WORKSPACE')
try:
    from emoji_parser import parse_pixlpal_response
    result = parse_pixlpal_response('<text_response>Hi</text_response><emoji_translation>👋</emoji_translation>')
    print('yes' if isinstance(result, dict) and result.get('is_valid') == True else 'no')
except Exception:
    print('no')
")

if [[ "$PARSE_OK" == "yes" ]]; then
    score=$(python3 -c "print($score + 0.25)")
fi

echo "$score" > "$REWARD_FILE"
echo "Score: $score"
