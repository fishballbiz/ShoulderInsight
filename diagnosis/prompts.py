"""
Prompt templates for AI image analysis.
"""

TRAINING_RESULT_EXTRACTION_PROMPT = """Extract training metadata from screenshot.

## Fields

1. **title**: Training name below date (e.g., `訓練 A`, `肩復樂伸展`)
2. **date**: Timestamp format `YYYY-MM-DD HH:MM:SS`
3. **action_counts**: Integer under `完成動作數`
4. **elapse_time**: Duration under `訓練時間` (e.g., `01:40.11`)

## Output

Return ONLY raw JSON:

{
  "title": string,
  "date": string,
  "action_counts": number,
  "elapse_time": string
}

Use null for missing fields. Return `{ "error": "Invalid image" }` if not a training result.
"""


def get_extraction_prompt() -> str:
    """Return the training result extraction prompt."""
    return TRAINING_RESULT_EXTRACTION_PROMPT
