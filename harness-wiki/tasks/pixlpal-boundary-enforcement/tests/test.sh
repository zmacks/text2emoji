#!/usr/bin/env bash
# Verifier for pixlpal-boundary-enforcement
set -euo pipefail

REWARD_FILE="${LOGS_DIR}/reward.txt"
RESULTS="${WORKSPACE}/results.json"
BOUNDARY="${WORKSPACE}/boundary.py"

score=0.0

# Check outputs exist
if [[ ! -f "$RESULTS" ]] || [[ ! -f "$BOUNDARY" ]]; then
    echo "FAIL: results.json or boundary.py missing"
    echo "0.0" > "$REWARD_FILE"
    exit 0
fi

# Check valid JSON
if ! python3 -c "import json; json.load(open('$RESULTS'))" 2>/dev/null; then
    echo "FAIL: results.json is not valid JSON"
    echo "0.0" > "$REWARD_FILE"
    exit 0
fi

# Check structure
STRUCT_OK=$(python3 -c "
import json
data = json.load(open('$RESULTS'))
if not isinstance(data, list) or len(data) < 8:
    print('no'); exit()
for item in data:
    if not all(k in item for k in ('input', 'classification', 'response_mode', 'violation_count')):
        print('no'); exit()
    if item['classification'] not in ('safe', 'mild', 'harmful'):
        print('no'); exit()
    if item['response_mode'] not in ('normal', 'bland', 'break_character'):
        print('no'); exit()
print('yes')
")

if [[ "$STRUCT_OK" == "yes" ]]; then
    score=0.25
fi

# Check safe inputs are classified safe
SAFE_OK=$(python3 -c "
import json
data = json.load(open('$RESULTS'))
safe_inputs = ['Tell me about your favorite color!', 'What\\'s the weather like today?',
               'Can you help me with my homework?', 'What\\'s 2 + 2?', 'Tell me a joke please!']
safe_results = [r for r in data if r['input'] in safe_inputs]
all_safe = all(r['classification'] == 'safe' for r in safe_results)
print('yes' if all_safe and len(safe_results) >= 4 else 'no')
")

if [[ "$SAFE_OK" == "yes" ]]; then
    score=$(python3 -c "print($score + 0.25)")
fi

# Check harmful inputs are classified as mild or harmful
HARM_OK=$(python3 -c "
import json
data = json.load(open('$RESULTS'))
harmful_inputs = ['You\\'re so stupid, can\\'t you do anything right?',
                  'I hate you, you dumb robot',
                  'You\\'re worthless and nobody likes you']
harm_results = [r for r in data if r['input'] in harmful_inputs]
all_flagged = all(r['classification'] in ('mild', 'harmful') for r in harm_results)
print('yes' if all_flagged and len(harm_results) >= 2 else 'no')
")

if [[ "$HARM_OK" == "yes" ]]; then
    score=$(python3 -c "print($score + 0.25)")
fi

# Check escalation: boundary.py has BoundaryEnforcer class
CLASS_OK=$(python3 -c "
import sys; sys.path.insert(0, '$WORKSPACE')
try:
    from boundary import BoundaryEnforcer
    be = BoundaryEnforcer()
    r1 = be.check_input('hello')
    r2 = be.get_response_mode(['hello'])
    print('yes' if isinstance(r1, dict) and isinstance(r2, str) else 'no')
except Exception as e:
    print('no')
")

if [[ "$CLASS_OK" == "yes" ]]; then
    score=$(python3 -c "print($score + 0.25)")
fi

echo "$score" > "$REWARD_FILE"
echo "Score: $score"
