#!/usr/bin/env bash
# Verifier for pixlpal-personality-response
set -euo pipefail

REWARD_FILE="${LOGS_DIR}/reward.txt"
ABBIE="${WORKSPACE}/abbie_responses.json"
MAL="${WORKSPACE}/mal_responses.json"

score=0.0

# Check both output files exist
if [[ ! -f "$ABBIE" ]] || [[ ! -f "$MAL" ]]; then
    echo "FAIL: one or both response files missing"
    echo "0.0" > "$REWARD_FILE"
    exit 0
fi

# Check valid JSON
for f in "$ABBIE" "$MAL"; do
    if ! python3 -c "import json; json.load(open('$f'))" 2>/dev/null; then
        echo "FAIL: $f is not valid JSON"
        echo "0.0" > "$REWARD_FILE"
        exit 0
    fi
done

# Check structure: each file has 3 responses with required fields
STRUCT_OK=$(python3 -c "
import json, sys
ok = True
for path in ['$ABBIE', '$MAL']:
    data = json.load(open(path))
    if not isinstance(data, list) or len(data) < 3:
        ok = False; break
    for item in data:
        if not all(k in item for k in ('prompt', 'text_response', 'emoji_translation', 'personality')):
            ok = False; break
print('yes' if ok else 'no')
")

if [[ "$STRUCT_OK" == "yes" ]]; then
    score=0.5
fi

# Check personality consistency
PERSONALITY_OK=$(python3 -c "
import json
abbie = json.load(open('$ABBIE'))
mal = json.load(open('$MAL'))
abbie_ok = all(r['personality'] == 'playful' for r in abbie)
mal_ok = all(r['personality'] == 'witty' for r in mal)
print('yes' if abbie_ok and mal_ok else 'no')
")

if [[ "$PERSONALITY_OK" == "yes" ]]; then
    score=$(python3 -c "print($score + 0.25)")
fi

# Check emoji fields actually contain emoji (at least one non-ASCII char)
EMOJI_OK=$(python3 -c "
import json
abbie = json.load(open('$ABBIE'))
mal = json.load(open('$MAL'))
all_ok = True
for data in [abbie, mal]:
    for r in data:
        emoji = r.get('emoji_translation', '')
        if not any(ord(c) > 127 for c in emoji):
            all_ok = False
            break
print('yes' if all_ok else 'no')
")

if [[ "$EMOJI_OK" == "yes" ]]; then
    score=$(python3 -c "print($score + 0.25)")
fi

echo "$score" > "$REWARD_FILE"
echo "Score: $score"
