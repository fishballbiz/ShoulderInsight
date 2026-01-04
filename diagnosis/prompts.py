"""
Prompt templates for AI image analysis.
"""

TRAINING_RESULT_EXTRACTION_PROMPT = """Parse the image and extract training result data.

## CRITICAL: 9×9 Grid Extraction (MOST IMPORTANT)

The grid extraction MUST be 100% accurate. This is the primary purpose of this task.

1. Locate the **9×9 grid** in the lower portion of the image
2. Traverse in **row-major order** (left → right, top → bottom)
3. Output **exactly 81 entries** per array

For each cell:
- If **no circle exists**: use `null`
- If a circle exists:
  - **grid_color**: `"GREEN"` (light green) or `"CYAN"` (light blue/aqua)
  - **grid_size**: `0` (small, within cell) or `1` (large, slightly outside cell)

**Double-check every cell. Count rows and columns carefully. Accuracy is critical.**

---

## Other Fields

- **title**: Training name below the date (e.g., `訓練 A`, `肩復樂訓練-簡單`)
- **date**: Timestamp near top (e.g., `2024-06-11 14:24:32`)
- **action_counts**: Integer under `完成動作數`
- **elapse_time**: Time under `訓練時間` (e.g., `MM:SS.xx`)

---

## Special Case

If grid is covered by text like `訓練 標準完成`:
- `grid_color`: array of 81 `null`
- `grid_size`: array of 81 `null`

---

## Output

Return ONLY raw JSON, no markdown:

{
  "title": string,
  "date": string,
  "action_counts": number,
  "elapse_time": string,
  "grid_color": (string | null)[],
  "grid_size": (number | null)[]
}

If invalid image, return: { "error": "Invalid training result image" }
"""


def get_extraction_prompt() -> str:
    """Return the training result extraction prompt."""
    return TRAINING_RESULT_EXTRACTION_PROMPT
