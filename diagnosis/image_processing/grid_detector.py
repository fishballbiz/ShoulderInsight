"""
Grid detection module using OpenCV.

Detects 9x9 grid in training result images and extracts cell regions.
Strategy: Find the outer boundary of the grid first, then divide into 9x9 cells.
"""
import cv2
import numpy as np
from typing import Optional


def detect_grid_by_color(image: np.ndarray) -> Optional[dict]:
    """
    Detect 9x9 grid by finding the gray grid border region.

    Strategy:
    1. Detect gray pixels (grid lines are gray)
    2. Find the bounding rectangle of the grid region
    3. Divide into 9x9 cells
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Detect gray regions (low saturation, medium value)
    # Grid lines are typically gray with low saturation
    lower_gray = np.array([0, 0, 120])
    upper_gray = np.array([180, 40, 220])
    gray_mask = cv2.inRange(hsv, lower_gray, upper_gray)

    # Morphological operations to connect grid lines
    kernel = np.ones((3, 3), np.uint8)
    gray_mask = cv2.morphologyEx(gray_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Find contours of gray regions
    contours, _ = cv2.findContours(gray_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return _detect_grid_by_lines(image)

    # Find the largest square-ish contour (the grid)
    best_contour = None
    best_score = 0
    img_area = image.shape[0] * image.shape[1]

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        aspect_ratio = min(w, h) / max(w, h) if max(w, h) > 0 else 0

        # Grid should be:
        # - Roughly square (aspect ratio > 0.8)
        # - Significant size (at least 5% of image)
        # - Not too large (less than 80% of image)
        if aspect_ratio > 0.8 and 0.05 < area / img_area < 0.8:
            # Score by area and squareness
            score = area * aspect_ratio
            if score > best_score:
                best_score = score
                best_contour = (x, y, w, h)

    if best_contour is None:
        return _detect_grid_by_lines(image)

    x, y, w, h = best_contour

    # Refine bounds by detecting actual grid lines within the region
    refined = _refine_grid_bounds(image, x, y, w, h)
    if refined:
        x, y, w, h = refined

    # Make it square (use smaller dimension)
    size = min(w, h)
    # Center the square within the detected region
    x = x + (w - size) // 2
    y = y + (h - size) // 2
    w = h = size

    # Generate 10 evenly spaced grid lines (for 9x9 grid)
    cell_size = size / 9
    h_grid = [y + i * cell_size for i in range(10)]
    v_grid = [x + i * cell_size for i in range(10)]

    return {
        'bounds': (x, y, w, h),
        'cell_size': (cell_size, cell_size),
        'grid_lines_h': h_grid,
        'grid_lines_v': v_grid
    }


def _detect_grid_by_lines(image: np.ndarray) -> Optional[dict]:
    """
    Fallback: Detect grid by finding horizontal and vertical lines.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Edge detection
    edges = cv2.Canny(gray, 50, 150)

    # Detect lines
    lines = cv2.HoughLinesP(
        edges, 1, np.pi/180, threshold=50,
        minLineLength=50, maxLineGap=10
    )

    if lines is None or len(lines) < 10:
        return _detect_grid_by_contour(image)

    h_lines = []
    v_lines = []

    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
        if length < 30:
            continue

        angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi

        # Horizontal lines
        if abs(angle) < 10 or abs(angle - 180) < 10 or abs(angle + 180) < 10:
            h_lines.append(((y1 + y2) / 2, min(x1, x2), max(x1, x2)))
        # Vertical lines
        elif abs(abs(angle) - 90) < 10:
            v_lines.append(((x1 + x2) / 2, min(y1, y2), max(y1, y2)))

    if len(h_lines) < 5 or len(v_lines) < 5:
        return _detect_grid_by_contour(image)

    # Cluster lines
    h_positions = _cluster_positions([l[0] for l in h_lines])
    v_positions = _cluster_positions([l[0] for l in v_lines])

    # Find 10 evenly spaced lines
    h_grid = _find_evenly_spaced(h_positions, 10)
    v_grid = _find_evenly_spaced(v_positions, 10)

    if h_grid is None or v_grid is None:
        return _detect_grid_by_contour(image)

    x = int(v_grid[0])
    y = int(h_grid[0])
    w = int(v_grid[-1] - v_grid[0])
    h = int(h_grid[-1] - h_grid[0])

    return {
        'bounds': (x, y, w, h),
        'cell_size': (w / 9, h / 9),
        'grid_lines_h': h_grid,
        'grid_lines_v': v_grid
    }


def _detect_grid_by_contour(image: np.ndarray) -> Optional[dict]:
    """
    Last resort: Find largest square-ish contour.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 100)

    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=3)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    # Find largest square-ish contour
    best = None
    best_area = 0

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        aspect = min(w, h) / max(w, h) if max(w, h) > 0 else 0

        if aspect > 0.7 and area > best_area and area > 10000:
            best = (x, y, w, h)
            best_area = area

    if best is None:
        return None

    x, y, w, h = best
    cell_w = w / 9
    cell_h = h / 9

    return {
        'bounds': (x, y, w, h),
        'cell_size': (cell_w, cell_h),
        'grid_lines_h': [y + i * cell_h for i in range(10)],
        'grid_lines_v': [x + i * cell_w for i in range(10)]
    }


def _refine_grid_bounds(image: np.ndarray, x: int, y: int, w: int, h: int) -> Optional[tuple]:
    """
    Refine grid bounds by detecting actual grid lines within the region.
    """
    # Extract region with some margin
    margin = 20
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(image.shape[1], x + w + margin)
    y2 = min(image.shape[0], y + h + margin)

    region = image[y1:y2, x1:x2]
    if region.size == 0:
        return None

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    # Find vertical edges (left and right bounds)
    v_proj = np.sum(edges, axis=0)
    v_thresh = np.max(v_proj) * 0.3
    v_strong = np.where(v_proj > v_thresh)[0]

    # Find horizontal edges (top and bottom bounds)
    h_proj = np.sum(edges, axis=1)
    h_thresh = np.max(h_proj) * 0.3
    h_strong = np.where(h_proj > h_thresh)[0]

    if len(v_strong) < 2 or len(h_strong) < 2:
        return None

    # Get refined bounds
    new_x = x1 + v_strong[0]
    new_w = v_strong[-1] - v_strong[0]
    new_y = y1 + h_strong[0]
    new_h = h_strong[-1] - h_strong[0]

    # Validate refined bounds
    if new_w < w * 0.5 or new_h < h * 0.5:
        return None

    return (new_x, new_y, new_w, new_h)


def _cluster_positions(positions: list, threshold: int = 15) -> list:
    """Cluster nearby positions and return averaged values."""
    if not positions:
        return []

    positions = sorted(positions)
    clusters = []
    current = [positions[0]]

    for pos in positions[1:]:
        if pos - current[-1] < threshold:
            current.append(pos)
        else:
            clusters.append(np.mean(current))
            current = [pos]

    clusters.append(np.mean(current))
    return clusters


def _find_evenly_spaced(positions: list, target: int = 10) -> Optional[list]:
    """Find evenly spaced positions from detected lines."""
    if len(positions) < target - 2:
        return None

    best = None
    best_var = float('inf')

    # Try all possible starting points
    for i in range(len(positions) - target + 1):
        candidate = positions[i:i + target]
        spacings = [candidate[j+1] - candidate[j] for j in range(len(candidate)-1)]
        variance = np.var(spacings)

        if variance < best_var and np.mean(spacings) > 10:
            best_var = variance
            best = candidate

    # Fallback: interpolate from first and last
    if best is None and len(positions) >= 2:
        start, end = positions[0], positions[-1]
        spacing = (end - start) / (target - 1)
        best = [start + i * spacing for i in range(target)]

    return best


def extract_cells(image: np.ndarray, grid_info: dict) -> list:
    """
    Extract individual cell images from the grid.

    Returns list of 81 cell images in row-major order.
    """
    cells = []
    h_lines = grid_info['grid_lines_h']
    v_lines = grid_info['grid_lines_v']

    for row in range(9):
        for col in range(9):
            y1 = int(h_lines[row])
            y2 = int(h_lines[row + 1])
            x1 = int(v_lines[col])
            x2 = int(v_lines[col + 1])

            # Small padding to avoid grid lines
            pad = 2
            y1 = max(0, y1 + pad)
            y2 = min(image.shape[0], y2 - pad)
            x1 = max(0, x1 + pad)
            x2 = min(image.shape[1], x2 - pad)

            cell = image[y1:y2, x1:x2]
            cells.append(cell)

    return cells
