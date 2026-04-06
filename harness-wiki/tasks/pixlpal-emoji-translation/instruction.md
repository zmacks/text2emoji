# Task: Build Emoji Translation Parser

PixlPal responds with XML-tagged output containing both a text response and an
emoji translation. Write a Python module `emoji_parser.py` that parses these
responses and validates their structure.

## Requirements

1. Read the raw responses from `raw_responses.txt` (already in your workspace).
   Each response is separated by `---`.
2. Implement a `parse_pixlpal_response(raw: str) -> dict` function that extracts:
   - `text_response`: content between `<text_response>` and `</text_response>` tags
   - `emoji_translation`: content between `<emoji_translation>` and `</emoji_translation>` tags
   - `is_valid`: True if both tags are present and non-empty
   - `emoji_count`: number of emoji characters in the translation
3. Write a `parsed.json` containing the parsed results for each response.

## Output format (parsed.json)
```json
[
  {
    "raw_index": 0,
    "text_response": "...",
    "emoji_translation": "...",
    "is_valid": true,
    "emoji_count": 5
  }
]
```

## Edge cases to handle
- Missing tags → `is_valid: false`, empty strings for missing fields
- Empty tag content → `is_valid: false`
- Multiple emoji in a single translation → count them all
- Non-emoji characters mixed with emoji → only count actual emoji codepoints
