"""
Disease matching service.

Loads disease data from JSON and provides matching logic.

Hand color mapping:
- CYAN = Left hand (左手)
- GREEN = Right hand (右手)
"""
import json
from pathlib import Path
from statistics import median

DISEASES_PATH = Path(__file__).parent.parent / 'data' / 'diseases.json'

LEFT_HAND_COLOR = 'CYAN'
RIGHT_HAND_COLOR = 'GREEN'

COLOR_SCORES: dict[str, int] = {'RED': 3, 'YELLOW': 2, 'BLUE': 1}
MAX_CIRCLE_SIZE = 5


def _load_diseases() -> list[dict]:
    """Load disease definitions from JSON file."""
    with open(DISEASES_PATH, encoding='utf-8') as f:
        return json.load(f)


def get_all_diseases() -> list[dict]:
    """Get all diseases with their grid patterns for display."""
    return _load_diseases()


REPORT_SECTION_LABELS = {
    'symptoms': '症狀',
    'treatments': '醫療處置',
    'carings': '居家照顧',
}


def _build_report_sections(
    report_data: dict,
    severity: str | None
) -> list[dict]:
    """Build structured report sections at the given severity level."""
    severity_key = severity or 'light'
    sections: list[dict] = []

    cause = report_data.get('cause', '')
    if cause:
        sections.append({'header': '成因', 'content': cause})

    for key, label in REPORT_SECTION_LABELS.items():
        subsection = report_data.get(key, {})
        text = subsection.get(severity_key, '')
        if text:
            sections.append({'header': label, 'content': text})

    return sections


SEVERITY_THRESHOLDS = {
    'light': (4, 8),
    'mild': (9, 18),
    'serious': (19, float('inf')),
}

SEVERITY_LABELS = {
    'light': '輕微',
    'mild': '中度',
    'serious': '嚴重',
}

MIN_DISPLAY_SCORE = 4
PRIMARY_RANK_GAP = 3


def _classify_severity(score: int) -> str | None:
    """Classify score into severity level. Returns None if below threshold."""
    for level, (low, high) in SEVERITY_THRESHOLDS.items():
        if low <= score <= high:
            return level
    return None


def _score_disease_for_hand(
    grid_color: list,
    grid_size: list,
    disease_grid_color: list,
    hand_color: str
) -> int:
    """Calculate weighted score for a single disease on one hand."""
    score = 0
    for i in range(81):
        disease_cell = disease_grid_color[i]
        if disease_cell is None:
            continue
        if grid_color[i] != hand_color:
            continue
        size = grid_size[i] if grid_size else 1
        size = max(1, min(MAX_CIRCLE_SIZE, size or 1))
        color_weight = COLOR_SCORES.get(disease_cell, 1)
        score += size * color_weight
    return score


def _build_median_grid(parsed_grids: list[dict]) -> tuple[list, list]:
    """
    Build a merged grid using the median size per cell across all images.

    Every image contributes to every cell (0 for no circle detected).
    The color is taken from whichever image detected a dot there.

    Returns:
        Tuple of (grid_color, grid_size) each with 81 elements.
    """
    cell_colors: list[str | None] = [None] * 81
    cell_sizes: list[list[int]] = [[] for _ in range(81)]

    for grid in parsed_grids:
        if not grid.get('success'):
            continue
        grid_color = grid.get('grid_color', [None] * 81)
        grid_size = grid.get('grid_size', [0] * 81)
        for i in range(81):
            if grid_color[i] is not None:
                cell_colors[i] = grid_color[i]
            cell_sizes[i].append(grid_size[i] or 0)

    median_sizes = [0] * 81
    for i in range(81):
        if cell_sizes[i]:
            median_sizes[i] = round(median(cell_sizes[i]))
        if median_sizes[i] == 0:
            cell_colors[i] = None

    return cell_colors, median_sizes


def accumulate_disease_scores(parsed_grids: list[dict]) -> dict:
    """
    Score diseases using the median grid built from multiple parsed grids.

    For each cell, the median size across all images is used.
    Disease scores are calculated once from this median grid.

    Args:
        parsed_grids: List of parse_grid results (each has grid_color, grid_size)

    Returns:
        Dictionary with left_hand, right_hand analysis and image_count.
    """
    diseases = _load_diseases()
    median_color, median_size = _build_median_grid(parsed_grids)

    hand_dot_counts = {'left': 0, 'right': 0}
    for i in range(81):
        if median_color[i] == LEFT_HAND_COLOR:
            hand_dot_counts['left'] += 1
        elif median_color[i] == RIGHT_HAND_COLOR:
            hand_dot_counts['right'] += 1

    hand_scores: dict[str, dict[int, int]] = {
        'left': {},
        'right': {},
    }
    for disease in diseases:
        for hand, hand_color in [('left', LEFT_HAND_COLOR),
                                 ('right', RIGHT_HAND_COLOR)]:
            score = _score_disease_for_hand(
                median_color, median_size,
                disease['grid_color'], hand_color
            )
            hand_scores[hand][disease['id']] = score

    result = {
        'image_count': len(parsed_grids),
        'merged_grid': {
            'grid_color': median_color,
            'grid_size': median_size,
        },
    }

    for hand, hand_zh in [('left', '左手'), ('right', '右手')]:
        all_diseases = []
        for disease in diseases:
            score = hand_scores[hand][disease['id']]
            severity = _classify_severity(score) if score >= MIN_DISPLAY_SCORE else None
            report_data = disease.get('report', {})
            report_sections = _build_report_sections(report_data, severity)
            disclaimer = report_data.get('disclaimer', '')
            all_diseases.append({
                'id': disease['id'],
                'name_zh': disease['name_zh'],
                'name_en': disease['name_en'],
                'symptoms': disease['symptoms'],
                'report_sections': report_sections,
                'disclaimer': disclaimer,
                'score': score,
                'severity': severity,
                'severity_zh': SEVERITY_LABELS.get(severity, ''),
            })

        all_diseases.sort(key=lambda d: d['score'], reverse=True)

        visible = [d for d in all_diseases if d['score'] >= MIN_DISPLAY_SCORE]

        for i, d in enumerate(visible):
            if i == 0:
                d['rank'] = 'primary'
            elif i == 1:
                diff = visible[0]['score'] - d['score']
                d['rank'] = 'primary' if diff <= PRIMARY_RANK_GAP else 'secondary'
            else:
                d['rank'] = None

        result[f'{hand}_hand'] = {
            'hand': hand,
            'hand_zh': hand_zh,
            'color': LEFT_HAND_COLOR if hand == 'left' else RIGHT_HAND_COLOR,
            'dot_count': hand_dot_counts[hand],
            'diseases': visible[:2],
            'all_diseases': all_diseases,
        }

    return result


def simulate_disease_scores(
    user_grid: list[int],
    light_min: int = 4,
    light_max: int = 8,
    mild_max: int = 18,
) -> dict:
    """Score diseases against a user grid without hand filtering."""
    diseases = _load_diseases()
    min_display = light_min
    thresholds = {
        'light': (light_min, light_max),
        'mild': (light_max + 1, mild_max),
        'serious': (mild_max + 1, float('inf')),
    }

    scored = []
    for disease in diseases:
        score = sum(
            user_grid[i] * COLOR_SCORES.get(
                disease['grid_color'][i], 0
            )
            for i in range(81)
            if user_grid[i] > 0
            and disease['grid_color'][i] is not None
        )
        severity = None
        if score >= min_display:
            for level, (lo, hi) in thresholds.items():
                if lo <= score <= hi:
                    severity = level
                    break
        scored.append({
            'id': disease['id'],
            'name_zh': disease['name_zh'],
            'name_en': disease['name_en'],
            'grid_color': disease['grid_color'],
            'score': score,
            'severity': severity,
            'severity_zh': SEVERITY_LABELS.get(severity, ''),
        })

    by_score = sorted(scored, key=lambda d: d['score'], reverse=True)
    visible = [
        d for d in by_score if d['score'] >= min_display
    ][:2]
    for i, d in enumerate(visible):
        if i == 0:
            d['rank'] = 'primary'
            d['rank_zh'] = '主要'
        else:
            gap = visible[0]['score'] - d['score']
            primary = gap <= PRIMARY_RANK_GAP
            d['rank'] = 'primary' if primary else 'secondary'
            d['rank_zh'] = '主要' if primary else '次要'

    return {'scored': scored, 'visible': visible}
