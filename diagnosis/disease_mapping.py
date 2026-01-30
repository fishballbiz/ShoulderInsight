"""
Disease matching service.

Loads disease data from JSON and provides matching logic.

Hand color mapping:
- CYAN = Left hand (左手)
- GREEN = Right hand (右手)
"""
import json
from pathlib import Path
from typing import TypedDict

DISEASES_PATH = Path(__file__).parent.parent / 'data' / 'diseases.json'

LEFT_HAND_COLOR = 'CYAN'
RIGHT_HAND_COLOR = 'GREEN'

COLOR_SCORES: dict[str, int] = {'RED': 3, 'YELLOW': 2, 'BLUE': 1}
MAX_CIRCLE_SIZE = 5


class MatchedDisease(TypedDict):
    id: int
    name_zh: str
    name_en: str
    symptoms: list[str]
    report: str
    score: int
    max_score: int
    match_percent: float


class HandAnalysis(TypedDict):
    hand: str
    hand_zh: str
    color: str
    dot_count: int
    diseases: list[MatchedDisease]


def _load_diseases() -> list[dict]:
    """Load disease definitions from JSON file."""
    with open(DISEASES_PATH, encoding='utf-8') as f:
        return json.load(f)


def get_all_diseases() -> list[dict]:
    """Get all diseases with their grid patterns for display."""
    return _load_diseases()


def _filter_grid_by_color(
    grid_color: list,
    grid_size: list,
    target_color: str
) -> tuple[list, list]:
    """Filter grid to only include dots of a specific color."""
    filtered_color = []
    filtered_size = []
    for i in range(81):
        if grid_color[i] == target_color:
            filtered_color.append(grid_color[i])
            filtered_size.append(grid_size[i] if grid_size else 0)
        else:
            filtered_color.append(None)
            filtered_size.append(0)
    return filtered_color, filtered_size


def _calculate_match_score(
    result_grid_color: list,
    result_grid_size: list,
    disease_grid_color: list
) -> tuple[int, int]:
    """
    Calculate weighted match score between result and disease pattern.

    Scoring: circle_size (1-5) x color_score (RED=3, YELLOW=2, BLUE=1)
    Disease pattern color determines the weight.

    Returns:
        Tuple of (score, max_possible_score)
    """
    max_score = 0
    for color in disease_grid_color:
        if color is not None:
            max_score += MAX_CIRCLE_SIZE * COLOR_SCORES.get(color, 1)

    if max_score == 0:
        return 0, 0

    score = 0
    for i in range(81):
        disease_color = disease_grid_color[i]
        if disease_color is None:
            continue

        if result_grid_color[i] is not None:
            size = result_grid_size[i] if result_grid_size else 1
            size = max(1, min(MAX_CIRCLE_SIZE, size or 1))
            color_weight = COLOR_SCORES.get(disease_color, 1)
            score += size * color_weight

    return score, max_score


def _find_diseases_for_grid(
    grid_color: list,
    grid_size: list,
    threshold: float = 0.3
) -> list[MatchedDisease]:
    """Find matching diseases for a specific grid."""
    if not grid_color or len(grid_color) != 81:
        return []

    if not grid_size or len(grid_size) != 81:
        grid_size = [0] * 81

    diseases = _load_diseases()
    matches = []

    for disease in diseases:
        score, k = _calculate_match_score(
            grid_color,
            grid_size,
            disease['grid_color']
        )

        if k == 0:
            continue

        match_percent = score / k
        if match_percent >= threshold:
            matches.append({
                "id": disease["id"],
                "name_zh": disease["name_zh"],
                "name_en": disease["name_en"],
                "symptoms": disease["symptoms"],
                "report": disease.get("report", ""),
                "score": score,
                "max_score": k,
                "match_percent": round(match_percent * 100, 1)
            })

    matches.sort(key=lambda x: x["match_percent"], reverse=True)
    return matches


def find_matching_diseases_by_hand(
    ai_result: dict,
    threshold: float = 0.3
) -> dict:
    """
    Find diseases matching the analysis result, separated by hand.

    Args:
        ai_result: Analysis result with grid_color and grid_size
        threshold: Minimum match percentage (default 30%)

    Returns:
        Dictionary with 'left_hand' and 'right_hand' HandAnalysis
    """
    result_grid_color = ai_result.get('grid_color', [])
    result_grid_size = ai_result.get('grid_size', [])

    if not result_grid_color or len(result_grid_color) != 81:
        result_grid_color = [None] * 81

    if not result_grid_size or len(result_grid_size) != 81:
        result_grid_size = [0] * 81

    # Filter grids by hand color
    left_color, left_size = _filter_grid_by_color(
        result_grid_color, result_grid_size, LEFT_HAND_COLOR
    )
    right_color, right_size = _filter_grid_by_color(
        result_grid_color, result_grid_size, RIGHT_HAND_COLOR
    )

    # Count dots per hand
    left_dot_count = sum(1 for c in left_color if c is not None)
    right_dot_count = sum(1 for c in right_color if c is not None)

    # Find diseases for each hand
    left_diseases = _find_diseases_for_grid(left_color, left_size, threshold)
    right_diseases = _find_diseases_for_grid(right_color, right_size, threshold)

    return {
        'left_hand': {
            'hand': 'left',
            'hand_zh': '左手',
            'color': LEFT_HAND_COLOR,
            'dot_count': left_dot_count,
            'diseases': left_diseases,
        },
        'right_hand': {
            'hand': 'right',
            'hand_zh': '右手',
            'color': RIGHT_HAND_COLOR,
            'dot_count': right_dot_count,
            'diseases': right_diseases,
        }
    }


def find_matching_diseases(
    ai_result: dict,
    threshold: float = 0.3
) -> list[MatchedDisease]:
    """
    Find diseases matching the AI analysis result (combined).

    Args:
        ai_result: AI analysis result with grid_color and grid_size
        threshold: Minimum match percentage (default 30%)

    Returns:
        List of matching diseases sorted by match percentage
    """
    result_grid_color = ai_result.get('grid_color', [])
    result_grid_size = ai_result.get('grid_size', [])

    return _find_diseases_for_grid(result_grid_color, result_grid_size, threshold)
