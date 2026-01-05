"""
Disease matching service.

Loads disease data from JSON and provides matching logic.
"""
import json
from pathlib import Path
from typing import TypedDict

DISEASES_PATH = Path(__file__).parent.parent / 'data' / 'diseases.json'


class MatchedDisease(TypedDict):
    id: int
    name_zh: str
    name_en: str
    symptoms: list[str]
    report: str
    score: int
    max_score: int
    match_percent: float


def _load_diseases() -> list[dict]:
    """Load disease definitions from JSON file."""
    with open(DISEASES_PATH, encoding='utf-8') as f:
        return json.load(f)


def get_all_diseases() -> list[dict]:
    """Get all diseases with their grid patterns for display."""
    return _load_diseases()


def _calculate_match_score(
    result_grid_color: list,
    result_grid_size: list,
    disease_grid_color: list
) -> tuple[int, int]:
    """
    Calculate match score between AI result and disease pattern.

    Returns:
        Tuple of (score, max_possible_score K)
    """
    k = sum(1 for color in disease_grid_color if color is not None)

    if k == 0:
        return 0, 0

    score = 0
    for i in range(81):
        if disease_grid_color[i] is None:
            continue

        if result_grid_color[i] is not None:
            score += 1
            if result_grid_size[i] == 1:
                score += 2

    return score, k


def find_matching_diseases(
    ai_result: dict,
    threshold: float = 0.3
) -> list[MatchedDisease]:
    """
    Find diseases matching the AI analysis result.

    Args:
        ai_result: AI analysis result with grid_color and grid_size
        threshold: Minimum match percentage (default 30%)

    Returns:
        List of matching diseases sorted by match percentage
    """
    result_grid_color = ai_result.get('grid_color', [])
    result_grid_size = ai_result.get('grid_size', [])

    if not result_grid_color or len(result_grid_color) != 81:
        return []

    if not result_grid_size or len(result_grid_size) != 81:
        result_grid_size = [None] * 81

    diseases = _load_diseases()
    matches = []

    for disease in diseases:
        score, k = _calculate_match_score(
            result_grid_color,
            result_grid_size,
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
