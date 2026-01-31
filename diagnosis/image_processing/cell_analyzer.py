"""
Cell analysis module for detecting circle color and size.

Detection logic:
- Check cell CENTER for color presence (not whole cell)
- Size 1-5 based on diameter_ratio via minEnclosingCircle
- diameter_ratio = (2 * radius_px) / cell_width
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

# Minimum saturation to count as a color (excludes gray/white)
MIN_SATURATION = 80

SIZE_THRESHOLDS = {
    't1': 0.717,
    't2': 0.886,
    't3': 1.054,
    't4': 1.223,
}


def set_size_thresholds(t1: float, t2: float, t3: float, t4: float) -> None:
    """Update size thresholds dynamically."""
    SIZE_THRESHOLDS['t1'] = t1
    SIZE_THRESHOLDS['t2'] = t2
    SIZE_THRESHOLDS['t3'] = t3
    SIZE_THRESHOLDS['t4'] = t4


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


def _measure_diameter_ratio(cell_image: np.ndarray, mask: np.ndarray) -> float:
    """
    Measure circle diameter as a ratio of cell width using minEnclosingCircle.

    Returns 0.0 if no contour found.
    """
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return 0.0

    largest = max(contours, key=cv2.contourArea)
    (_, _), radius_px = cv2.minEnclosingCircle(largest)
    cell_width = cell_image.shape[1]
    return (2 * radius_px) / cell_width


def analyze_cell(cell_image: np.ndarray) -> dict:
    """
    Analyze a single cell for color and size.

    Detection logic:
    - Check CENTER of cell for color presence
    - Measure diameter_ratio via minEnclosingCircle to determine size (1-5)

    Args:
        cell_image: BGR image of a single cell

    Returns:
        Dictionary with:
            - color: Detected color name or None
            - size: 1-5 based on diameter_ratio, or None
            - confidence: Detection confidence (0-1)
            - diameter_ratio: Circle diameter / cell width
            - center_ratio: Ratio of colored pixels at center
    """
    if cell_image.size == 0:
        return {
            'color': None,
            'size': None,
            'confidence': 0,
            'diameter_ratio': 0,
            'center_ratio': 0
        }

    center_color, center_ratio = _detect_color_at_center(cell_image)

    if center_color is None:
        return {
            'color': None,
            'size': None,
            'confidence': 0,
            'diameter_ratio': 0,
            'center_ratio': 0
        }

    hsv = cv2.cvtColor(cell_image, cv2.COLOR_BGR2HSV)
    mask = _get_color_mask(hsv, center_color)
    diameter_ratio = _measure_diameter_ratio(cell_image, mask)

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

    return {
        'color': center_color,
        'size': size,
        'confidence': confidence,
        'diameter_ratio': diameter_ratio,
        'center_ratio': center_ratio
    }


def analyze_grid(cells: list) -> dict:
    """
    Analyze all 81 cells and return grid data.

    Args:
        cells: List of 81 cell images

    Returns:
        Dictionary with:
            - grid_color: List of 81 color values (or None)
            - grid_size: List of 81 size values (0, 1, or None)
            - cell_details: List of detailed analysis per cell
    """
    grid_color = []
    grid_size = []
    cell_details = []

    for i, cell in enumerate(cells):
        result = analyze_cell(cell)
        grid_color.append(result['color'])
        grid_size.append(result['size'])
        cell_details.append({
            'index': i,
            'row': i // 9,
            'col': i % 9,
            **result
        })

    return {
        'grid_color': grid_color,
        'grid_size': grid_size,
        'cell_details': cell_details
    }


def visualize_detection(image: np.ndarray, grid_info: dict, analysis: dict) -> np.ndarray:
    """
    Create a visualization of the grid detection results.

    Shows cell numbers in each cell, and for cells with dots, also shows size (1 or 2).

    Args:
        image: Original BGR image
        grid_info: Grid detection result
        analysis: Cell analysis result

    Returns:
        Annotated image showing detection results
    """
    result = image.copy()
    h_lines = grid_info['grid_lines_h']
    v_lines = grid_info['grid_lines_v']

    # Draw grid lines (green)
    for y in h_lines:
        cv2.line(result, (int(v_lines[0]), int(y)), (int(v_lines[-1]), int(y)), (0, 200, 0), 2)
    for x in v_lines:
        cv2.line(result, (int(x), int(h_lines[0])), (int(x), int(h_lines[-1])), (0, 200, 0), 2)

    # Color map for detected colors
    color_map = {
        'GREEN': (0, 255, 0),
        'CYAN': (255, 255, 0),
        'BLUE': (255, 0, 0),
        'RED': (0, 0, 255),
        'YELLOW': (0, 255, 255)
    }

    # Draw cell info for all 81 cells
    for detail in analysis['cell_details']:
        row, col = detail['row'], detail['col']
        cell_num = detail['index']

        x1 = int(v_lines[col])
        y1 = int(h_lines[row])
        x2 = int(v_lines[col + 1])
        y2 = int(h_lines[row + 1])
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if detail['color']:
            # Cell has a dot - draw colored background
            color = color_map.get(detail['color'], (128, 128, 128))

            # Fill cell with semi-transparent color
            overlay = result.copy()
            cv2.rectangle(overlay, (x1+2, y1+2), (x2-2, y2-2), color, -1)
            cv2.addWeighted(overlay, 0.4, result, 0.6, 0, result)

            # Draw cell number and size
            text = f"{cell_num}:{detail['size']}"
            font_scale = 0.4
            thickness = 1
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            tx = cx - tw // 2
            ty = cy + th // 2

            # White text with black outline for visibility
            cv2.putText(result, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX,
                       font_scale, (0, 0, 0), thickness + 2)
            cv2.putText(result, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX,
                       font_scale, (255, 255, 255), thickness)
        else:
            # Empty cell - just show cell number (smaller, gray)
            text = str(cell_num)
            font_scale = 0.35
            thickness = 1
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            tx = cx - tw // 2
            ty = cy + th // 2
            cv2.putText(result, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX,
                       font_scale, (150, 150, 150), thickness)

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


def _calibrate_and_assign_sizes(cell_details: list) -> list:
    """
    Calibrate size thresholds from actual diameter ratios and reassign sizes 1-5.
    """
    ratios = [
        d['diameter_ratio'] for d in cell_details if d['color'] is not None
    ]

    if len(ratios) < 2:
        return [d['size'] for d in cell_details]

    min_ratio = min(ratios)
    max_ratio = max(ratios)
    ratio_range = max_ratio - min_ratio

    if ratio_range < 0.01:
        return [3 if d['color'] else d['size'] for d in cell_details]

    t1 = min_ratio + ratio_range * 0.20
    t2 = min_ratio + ratio_range * 0.40
    t3 = min_ratio + ratio_range * 0.60
    t4 = min_ratio + ratio_range * 0.80

    new_sizes = []
    for detail in cell_details:
        if detail['color'] is None:
            new_sizes.append(detail['size'])
        else:
            dr = detail['diameter_ratio']
            if dr > t4:
                new_sizes.append(5)
            elif dr > t3:
                new_sizes.append(4)
            elif dr > t2:
                new_sizes.append(3)
            elif dr > t1:
                new_sizes.append(2)
            else:
                new_sizes.append(1)

    return new_sizes


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

    cells = extract_cells(image, grid_info)
    analysis = analyze_grid(cells)
    calibrated_sizes = _calibrate_and_assign_sizes(analysis['cell_details'])

    return _to_native({
        'success': True,
        'grid_color': analysis['grid_color'],
        'grid_size': calibrated_sizes,
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

    # Extract cells
    cells = extract_cells(image, grid_info)

    # Analyze cells
    analysis = analyze_grid(cells)

    # Create visualization
    viz_image = visualize_detection(image, grid_info, analysis)

    return {
        'grid_info': grid_info,
        'analysis': analysis,
        'visualization': viz_image,
        'image_shape': image.shape
    }


def calibrate_from_samples(image_paths: list) -> dict:
    """
    Analyze sample images to determine optimal 5-level size thresholds.

    Args:
        image_paths: List of paths to sample images

    Returns:
        Dictionary with calibration results and applied thresholds
    """
    all_ratios = []

    for image_path in image_paths:
        image = cv2.imread(image_path)
        if image is None:
            continue

        grid_info = detect_grid_by_color(image)
        if grid_info is None:
            continue

        cells = extract_cells(image, grid_info)

        for cell in cells:
            if cell.size == 0:
                continue

            center_color, _ = _detect_color_at_center(cell)
            if center_color is None:
                continue

            hsv = cv2.cvtColor(cell, cv2.COLOR_BGR2HSV)
            mask = _get_color_mask(hsv, center_color)
            diameter_ratio = _measure_diameter_ratio(cell, mask)

            all_ratios.append({
                'ratio': diameter_ratio,
                'color': center_color,
                'image': image_path
            })

    if not all_ratios:
        return {'error': 'No colored cells found in samples'}

    sorted_ratios = sorted([r['ratio'] for r in all_ratios])
    min_ratio = sorted_ratios[0]
    max_ratio = sorted_ratios[-1]

    range_size = max_ratio - min_ratio
    t1 = min_ratio + range_size * 0.20
    t2 = min_ratio + range_size * 0.40
    t3 = min_ratio + range_size * 0.60
    t4 = min_ratio + range_size * 0.80

    set_size_thresholds(t1, t2, t3, t4)

    bins = [0, 0.20, 0.40, 0.60, 0.80, 1.00,
            1.20, 1.40, 1.60, 1.80, 2.00, 2.50]
    histogram = {}
    for i in range(len(bins) - 1):
        count = sum(1 for r in sorted_ratios if bins[i] <= r < bins[i+1])
        histogram[f'{bins[i]:.2f}-{bins[i+1]:.2f}'] = count

    return {
        'ratios': all_ratios,
        'sorted_ratios': sorted_ratios,
        'count': len(all_ratios),
        'min': round(min_ratio, 3),
        'max': round(max_ratio, 3),
        'histogram': histogram,
        'thresholds': {
            't1': round(t1, 3),
            't2': round(t2, 3),
            't3': round(t3, 3),
            't4': round(t4, 3),
        },
        'size_ranges': {
            'size_1': f'< {t1:.3f}',
            'size_2': f'{t1:.3f} - {t2:.3f}',
            'size_3': f'{t2:.3f} - {t3:.3f}',
            'size_4': f'{t3:.3f} - {t4:.3f}',
            'size_5': f'> {t4:.3f}',
        }
    }
