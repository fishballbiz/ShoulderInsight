"""
Cell analysis module for detecting circle color and size.

Detection logic:
- Check cell CENTER for color presence (not whole cell)
- Size 1-5 based on inscribed circle diameter via distance transform
- diameter_ratio = 2 * max_dt_near_center / cell_width
- None = empty cell (no color at center)
"""
import cv2
import numpy as np

from .grid_detector import detect_grid_by_color, extract_cells


# Color ranges in HSV
COLOR_RANGES = {
    'GREEN': {
        'lower': np.array([35, 50, 50]),
        'upper': np.array([85, 255, 255])
    },
    'CYAN': {
        'lower': np.array([80, 50, 50]),
        'upper': np.array([105, 255, 255])
    },
    'BLUE': {
        'lower': np.array([100, 50, 50]),
        'upper': np.array([130, 255, 255])
    },
    'RED': {
        'lower1': np.array([0, 50, 50]),
        'upper1': np.array([10, 255, 255]),
        'lower2': np.array([170, 50, 50]),
        'upper2': np.array([180, 255, 255])
    },
    'YELLOW': {
        'lower': np.array([20, 50, 50]),
        'upper': np.array([35, 255, 255])
    }
}

# Center region size (ratio of cell size to check for color)
CENTER_REGION_RATIO = 0.4

# Minimum saturation for center color detection (excludes gray/white)
MIN_SATURATION = 80

# Lower saturation for full-image DT mask (captures circle edges)
DT_MIN_SATURATION = 40

# Thresholds derived from distance-transform diameter ratio clusters
SIZE_THRESHOLDS = {
    't1': 0.71,
    't2': 0.96,
    't3': 1.24,
    't4': 1.49,
}

# Morphological kernel for noise cleanup in color mask
MORPH_KERNEL_SIZE = 3


def _get_color_mask(hsv_image: np.ndarray, color_name: str) -> np.ndarray:
    """Get binary mask for a specific color with saturation filtering."""
    ranges = COLOR_RANGES[color_name]

    # Saturation mask to exclude gray/white regions
    saturation_mask = hsv_image[:, :, 1] >= MIN_SATURATION

    if color_name == 'RED':
        mask1 = cv2.inRange(hsv_image, ranges['lower1'], ranges['upper1'])
        mask2 = cv2.inRange(hsv_image, ranges['lower2'], ranges['upper2'])
        color_mask = cv2.bitwise_or(mask1, mask2)
    else:
        color_mask = cv2.inRange(hsv_image, ranges['lower'], ranges['upper'])

    # Apply saturation filter
    return cv2.bitwise_and(color_mask, saturation_mask.astype(np.uint8) * 255)


def _detect_color_at_center(cell_image: np.ndarray) -> tuple:
    """
    Detect color at the center region of a cell.

    Returns:
        Tuple of (color_name, center_ratio) or (None, 0)
    """
    if cell_image.size == 0:
        return None, 0

    h, w = cell_image.shape[:2]

    # Define center region
    margin_h = int(h * (1 - CENTER_REGION_RATIO) / 2)
    margin_w = int(w * (1 - CENTER_REGION_RATIO) / 2)

    center_region = cell_image[margin_h:h-margin_h, margin_w:w-margin_w]
    if center_region.size == 0:
        return None, 0

    hsv_center = cv2.cvtColor(center_region, cv2.COLOR_BGR2HSV)
    center_area = center_region.shape[0] * center_region.shape[1]

    best_color = None
    best_ratio = 0

    for color_name in COLOR_RANGES:
        mask = _get_color_mask(hsv_center, color_name)
        colored_pixels = cv2.countNonZero(mask)
        ratio = colored_pixels / center_area

        if ratio > best_ratio:
            best_ratio = ratio
            best_color = color_name

    # Need significant color presence at center (>20%)
    if best_ratio < 0.2:
        return None, 0

    return best_color, best_ratio


def _get_full_color_mask(
    image: np.ndarray,
    color_name: str,
) -> np.ndarray:
    """Get morphologically cleaned binary mask for a color on the full image.

    Uses a lower saturation threshold than center detection to capture
    circle edges where color fades to white.
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    ranges = COLOR_RANGES[color_name]
    saturation_mask = hsv[:, :, 1] >= DT_MIN_SATURATION

    if color_name == 'RED':
        mask1 = cv2.inRange(hsv, ranges['lower1'], ranges['upper1'])
        mask2 = cv2.inRange(hsv, ranges['lower2'], ranges['upper2'])
        color_mask = cv2.bitwise_or(mask1, mask2)
    else:
        color_mask = cv2.inRange(hsv, ranges['lower'], ranges['upper'])

    mask = cv2.bitwise_and(
        color_mask, saturation_mask.astype(np.uint8) * 255,
    )
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE),
    )
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)


def _measure_diameter_ratio(
    dist_map: np.ndarray,
    cx: float,
    cy: float,
    cell_w: float,
) -> float:
    """Measure circle diameter via distance transform on full image.

    Finds max distance-to-background near grid center (10% search
    region). This equals the radius of the largest fully-colored
    inscribed circle. Returns diameter / cell_width, capped at 2.0.
    """
    search_r = max(1, int(cell_w * 0.1))
    h, w = dist_map.shape
    y1 = max(0, int(cy) - search_r)
    y2 = min(h, int(cy) + search_r + 1)
    x1 = max(0, int(cx) - search_r)
    x2 = min(w, int(cx) + search_r + 1)
    region = dist_map[y1:y2, x1:x2]
    if region.size == 0:
        return 0.0
    radius = min(float(np.max(region)), cell_w)
    return (2.0 * radius) / cell_w


def analyze_cell(cell_image: np.ndarray) -> dict:
    """Analyze a single cell for color and size (standalone).

    Uses distance transform on the cell image itself.
    For full-image DT (better accuracy), use analyze_grid instead.
    """
    empty = {
        'color': None, 'size': None, 'confidence': 0,
        'diameter_ratio': 0, 'center_ratio': 0,
    }
    if cell_image.size == 0:
        return empty

    center_color, center_ratio = _detect_color_at_center(cell_image)
    if center_color is None:
        return empty

    mask = _get_full_color_mask(cell_image, center_color)
    dist_map = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    h, w = cell_image.shape[:2]
    diameter_ratio = _measure_diameter_ratio(
        dist_map, w / 2.0, h / 2.0, float(w)
    )

    if diameter_ratio > SIZE_THRESHOLDS['t4']:
        size = 5
    elif diameter_ratio > SIZE_THRESHOLDS['t3']:
        size = 4
    elif diameter_ratio > SIZE_THRESHOLDS['t2']:
        size = 3
    elif diameter_ratio > SIZE_THRESHOLDS['t1']:
        size = 2
    else:
        size = 1

    return {
        'color': center_color,
        'size': size,
        'confidence': min(1.0, center_ratio),
        'diameter_ratio': diameter_ratio,
        'center_ratio': center_ratio,
    }


def analyze_grid(image: np.ndarray, grid_info: dict) -> dict:
    """Analyze all 81 cells using distance-transform sizing.

    Extracts cells for color detection, then measures circle diameter
    via distance transform on the full image for each colored cell.

    Args:
        image: Full BGR image
        grid_info: Grid detection result with grid_lines_h/v

    Returns:
        Dictionary with grid_color, grid_size, cell_details.
    """
    cells = extract_cells(image, grid_info)
    h_lines = grid_info['grid_lines_h']
    v_lines = grid_info['grid_lines_v']
    cell_w = float(v_lines[1] - v_lines[0])

    grid_color = []
    grid_size = []
    cell_details = []
    dt_cache: dict[str, np.ndarray] = {}

    for i, cell in enumerate(cells):
        color, center_ratio = _detect_color_at_center(cell)

        if color is None:
            grid_color.append(None)
            grid_size.append(None)
            cell_details.append({
                'index': i,
                'row': i // 9,
                'col': i % 9,
                'color': None,
                'size': None,
                'confidence': 0,
                'diameter_ratio': 0,
                'center_ratio': 0,
            })
            continue

        if color not in dt_cache:
            mask = _get_full_color_mask(image, color)
            dt_cache[color] = cv2.distanceTransform(
                mask, cv2.DIST_L2, 5
            )

        row, col = i // 9, i % 9
        cx = (v_lines[col] + v_lines[col + 1]) / 2.0
        cy = (h_lines[row] + h_lines[row + 1]) / 2.0

        diameter_ratio = _measure_diameter_ratio(
            dt_cache[color], cx, cy, cell_w
        )

        if diameter_ratio > SIZE_THRESHOLDS['t4']:
            size = 5
        elif diameter_ratio > SIZE_THRESHOLDS['t3']:
            size = 4
        elif diameter_ratio > SIZE_THRESHOLDS['t2']:
            size = 3
        elif diameter_ratio > SIZE_THRESHOLDS['t1']:
            size = 2
        else:
            size = 1

        confidence = min(1.0, center_ratio)
        grid_color.append(color)
        grid_size.append(size)
        cell_details.append({
            'index': i,
            'row': row,
            'col': col,
            'color': color,
            'size': size,
            'confidence': confidence,
            'diameter_ratio': diameter_ratio,
            'center_ratio': center_ratio,
        })

    return {
        'grid_color': grid_color,
        'grid_size': grid_size,
        'cell_details': cell_details,
    }


def visualize_detection(
    image: np.ndarray,
    grid_info: dict,
    analysis: dict,
) -> np.ndarray:
    """Combined visualization on the original image.

    Draws:
    - Detected grid lines in thin blue
    - Inscribed circle outlines in thin red
    - Empty cells: gray cell number at center
    - Colored cells: line 1 = ratio, line 2 = S1-S5
    """
    result = image.copy()
    h_lines = grid_info['grid_lines_h']
    v_lines = grid_info['grid_lines_v']
    font = cv2.FONT_HERSHEY_SIMPLEX

    dt_cache: dict[str, np.ndarray] = {}

    # Draw grid lines (thin blue)
    for y in h_lines:
        cv2.line(
            result,
            (int(v_lines[0]), int(y)),
            (int(v_lines[-1]), int(y)),
            (200, 120, 0), 1,
        )
    for x in v_lines:
        cv2.line(
            result,
            (int(x), int(h_lines[0])),
            (int(x), int(h_lines[-1])),
            (200, 120, 0), 1,
        )

    for detail in analysis['cell_details']:
        row, col = detail['row'], detail['col']
        x1 = int(v_lines[col])
        y1 = int(h_lines[row])
        x2 = int(v_lines[col + 1])
        y2 = int(h_lines[row + 1])
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        color = detail['color']
        if color is None:
            text = str(detail['index'])
            scale = 0.35
            (tw, th), _ = cv2.getTextSize(text, font, scale, 1)
            tx = cx - tw // 2
            ty = cy + th // 2
            cv2.putText(
                result, text, (tx, ty), font, scale,
                (150, 150, 150), 1,
            )
            continue

        # Compute DT peak and radius
        if color not in dt_cache:
            mask = _get_full_color_mask(image, color)
            dt_cache[color] = cv2.distanceTransform(
                mask, cv2.DIST_L2, 5,
            )

        cell_dt = dt_cache[color][y1:y2, x1:x2]
        if cell_dt.size == 0:
            continue
        peak_idx = np.unravel_index(
            np.argmax(cell_dt), cell_dt.shape,
        )
        peak_x = x1 + int(peak_idx[1])
        peak_y = y1 + int(peak_idx[0])
        radius_px = float(cell_dt[peak_idx])

        # Inscribed circle (thin red)
        cv2.circle(
            result, (peak_x, peak_y), int(radius_px),
            (0, 0, 220), 1,
        )

        # Line 1: ratio value (above center)
        dr = detail['diameter_ratio']
        line1 = f"{dr:.2f}"
        scale1 = 0.35
        (tw1, th1), _ = cv2.getTextSize(line1, font, scale1, 1)
        tx1 = peak_x - tw1 // 2
        ty1 = peak_y - 2
        cv2.putText(
            result, line1, (tx1, ty1), font, scale1,
            (0, 0, 0), 2,
        )
        cv2.putText(
            result, line1, (tx1, ty1), font, scale1,
            (255, 255, 255), 1,
        )

        # Line 2: size label (below center)
        line2 = f"S{detail['size']}"
        scale2 = 0.4
        (tw2, th2), _ = cv2.getTextSize(line2, font, scale2, 1)
        tx2 = peak_x - tw2 // 2
        ty2 = peak_y + th1 + 4
        cv2.putText(
            result, line2, (tx2, ty2), font, scale2,
            (0, 0, 0), 2,
        )
        cv2.putText(
            result, line2, (tx2, ty2), font, scale2,
            (255, 255, 255), 1,
        )

    return result


def _to_native(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return [_to_native(item) for item in obj.tolist()]
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(item) for item in obj]
    return obj


def parse_grid(image_path: str) -> dict:
    """
    Parse a grid image and return grid_color and grid_size arrays.

    Args:
        image_path: Path to the input image

    Returns:
        Dictionary with grid_color (81 values), grid_size (1-5), success flag.
    """
    image = cv2.imread(image_path)
    if image is None:
        return {
            'success': False,
            'error': f'Could not load image: {image_path}',
            'grid_color': [None] * 81,
            'grid_size': [0] * 81
        }

    grid_info = detect_grid_by_color(image)
    if grid_info is None:
        return {
            'success': False,
            'error': 'Could not detect grid in image',
            'grid_color': [None] * 81,
            'grid_size': [0] * 81
        }

    analysis = analyze_grid(image, grid_info)

    return _to_native({
        'success': True,
        'grid_color': analysis['grid_color'],
        'grid_size': analysis['grid_size'],
        'cell_details': analysis['cell_details'],
        'grid_info': {
            'bounds': grid_info['bounds'],
            'cell_size': grid_info['cell_size']
        }
    })


def process_image(image_path: str) -> dict:
    """
    Complete processing pipeline for a single image.

    Args:
        image_path: Path to the input image

    Returns:
        Dictionary with all detection results
    """
    image = cv2.imread(image_path)
    if image is None:
        return {'error': f'Could not load image: {image_path}'}

    grid_info = detect_grid_by_color(image)
    if grid_info is None:
        return {'error': 'Could not detect grid in image'}

    analysis = analyze_grid(image, grid_info)
    viz_image = visualize_detection(image, grid_info, analysis)

    return {
        'grid_info': grid_info,
        'analysis': analysis,
        'visualization': viz_image,
        'image_shape': image.shape,
    }


