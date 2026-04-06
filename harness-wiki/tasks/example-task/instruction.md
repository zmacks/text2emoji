# Task: Count Word Frequencies

Count the frequency of each word in the file `input.txt` (already present in
your workspace). Write a file `output.json` containing a JSON object where
keys are lowercase words and values are their integer counts.

Exclude punctuation. Treat contractions as single words (e.g. "don't" → "don't").
Sort the output JSON by frequency descending.

Example for input "Hello world hello":
```json
{"hello": 2, "world": 1}
```
