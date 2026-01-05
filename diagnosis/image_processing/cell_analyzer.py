"""
Cell analysis module for detecting circle color and size.

Detection logic:
- Check cell CENTER for color presence (not whole cell)
- Size 2 = large circle overlapping into neighbor cells
- Size 1 = small circle within cell bounds
- None = empty cell (no color at center)
"""
import cv2
import numpy as np
from typing import Optional


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

# Size thresholds based on pixel coverage ratio
LARGE_CIRCLE_THRESHOLD = 0.35  # >35% coverage = large circle (size 2)
SMALL_CIRCLE_THRESHOLD = 0.05  # >5% coverage = small circle (size 1)


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


def analyze_cell(cell_image: np.ndarray) -> dict:
    """
    Analyze a single cell for color and size.

    Detection logic:
    - Check CENTER of cell for color presence
    - Measure total coverage to determine size
    - Size 2 = large circle (overlaps neighbors)
    - Size 1 = small circle (within cell)

    Args:
        cell_image: BGR image of a single cell

    Returns:
        Dictionary with:
            - color: Detected color name or None
            - size: 1 (small), 2 (large), or None
            - confidence: Detection confidence (0-1)
            - pixel_ratio: Ratio of colored pixels in whole cell
            - center_ratio: Ratio of colored pixels at center
    """
    if cell_image.size == 0:
        return {
            'color': None,
            'size': None,
            'confidence': 0,
            'pixel_ratio': 0,
            'center_ratio': 0
        }

    # First check if there's color at the center
    center_color, center_ratio = _detect_color_at_center(cell_image)

    if center_color is None:
        return {
            'color': None,
            'size': None,
            'confidence': 0,
            'pixel_ratio': 0,
            'center_ratio': 0
        }

    # Color found at center - now measure total coverage to determine size
    hsv = cv2.cvtColor(cell_image, cv2.COLOR_BGR2HSV)
    mask = _get_color_mask(hsv, center_color)
    cell_area = cell_image.shape[0] * cell_image.shape[1]
    colored_pixels = cv2.countNonZero(mask)
    pixel_ratio = colored_pixels / cell_area

    # Determine size based on coverage
    # Large circles (size 2) cover more area and overflow into neighbors
    # Small circles (size 1) are contained within the cell
    if pixel_ratio > LARGE_CIRCLE_THRESHOLD:
        size = 2
    elif pixel_ratio > SMALL_CIRCLE_THRESHOLD:
        size = 1
    else:
        size = 1  # Default to small if color detected at center

    confidence = min(1.0, center_ratio)

    return {
        'color': center_color,
        'size': size,
        'confidence': confidence,
        'pixel_ratio': pixel_ratio,
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


def process_image(image_path: str) -> dict:
    """
    Complete processing pipeline for a single image.

    Args:
        image_path: Path to the input image

    Returns:
        Dictionary with all detection results
    """
    from .grid_detector import detect_grid_by_color, extract_cells

    image = cv2.imread(image_path)
    if image is None:
        return {'error': f'Could not load image: {image_path}'}

    # Try to detect grid
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
