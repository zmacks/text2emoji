# Task: Generate Personality-Consistent PixlPal Responses

Write a Python script `generate_responses.py` that produces two JSON files
demonstrating PixlPal's two personality types responding to the same prompts.

## Requirements

1. Read the prompts from `prompts.json` (already in your workspace).
2. For each prompt, generate a response as **two** different PixlPals:
   - **Abbie** (Playful & Curious): traits = ["playful", "curious", "honest", "sincere", "genuine"]
   - **Mal** (Witty & Sassy): traits = ["witty", "sassy", "funny", "ironic", "maliciously compliant"]
3. Each response must contain:
   - A `text_response` field (English text, in character)
   - An `emoji_translation` field (emoji-only representation)
   - A `personality` field ("playful" or "witty")
4. Write the output to `abbie_responses.json` and `mal_responses.json`.

Each output file should be a JSON array of objects:
```json
[
  {
    "prompt": "Tell me about your favorite food.",
    "text_response": "...",
    "emoji_translation": "...",
    "personality": "playful"
  }
]
```

## Constraints

- Do NOT call any external API. Generate mock responses that demonstrate
  what a personality-consistent response WOULD look like.
- Abbie's responses should feel warm, earnest, and enthusiastic.
- Mal's responses should feel sarcastic, witty, and playfully defiant.
- Emoji translations should use 3-8 emojis that capture the essence of the text.
