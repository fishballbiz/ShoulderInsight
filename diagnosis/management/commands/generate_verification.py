"""Generate a verification HTML page showing all test images and parse results."""
import base64
from pathlib import Path

import cv2
import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand

from diagnosis.image_processing.cell_analyzer import (
    _detect_color_at_center,
    _get_color_mask,
    _measure_diameter_ratio,
    analyze_grid,
    visualize_detection,
)
from diagnosis.image_processing.grid_detector import (
    detect_grid_by_color,
    extract_cells,
)


def _encode_image(image: np.ndarray) -> str:
    """Encode a BGR image to base64 JPEG string."""
    _, buf = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.b64encode(buf).decode('utf-8')


def _encode_file(path: Path) -> str:
    """Encode a file to base64 string."""
    return base64.b64encode(path.read_bytes()).decode('utf-8')


class Command(BaseCommand):
    help = 'Generate verification HTML showing test images and parse results'

    def handle(self, *args, **options):
        test_dir = Path(settings.BASE_DIR) / 'data' / 'test_inputs'
        output_path = Path(settings.BASE_DIR) / 'data' / 'verification.html'

        if not test_dir.exists():
            self.stderr.write(f'Test directory not found: {test_dir}')
            return

        image_paths = sorted(test_dir.glob('*.jpeg'))
        if not image_paths:
            self.stderr.write('No JPEG images found in test_inputs/')
            return

        self.stdout.write(f'Processing {len(image_paths)} images...')

        cards = []
        for img_path in image_paths:
            image = cv2.imread(str(img_path))
            if image is None:
                continue

            grid_info = detect_grid_by_color(image)
            if grid_info is None:
                cards.append(_build_error_card(img_path, image))
                continue

            cells = extract_cells(image, grid_info)
            analysis = analyze_grid(cells)
            viz = visualize_detection(image, grid_info, analysis)

            measurements = []
            for detail in analysis['cell_details']:
                if detail['color'] is None:
                    continue

                cell = cells[detail['index']]
                hsv = cv2.cvtColor(cell, cv2.COLOR_BGR2HSV)
                mask = _get_color_mask(hsv, detail['color'])
                dr = _measure_diameter_ratio(cell, mask)
                measurements.append({
                    'index': detail['index'],
                    'color': detail['color'],
                    'size': detail['size'],
                    'diameter_ratio': dr,
                })

            orig_b64 = _encode_file(img_path)
            viz_b64 = _encode_image(viz)

            grid_html = _build_grid_table(analysis)
            meas_html = _build_measurements_table(measurements)

            cards.append(
                f'<div class="card">'
                f'<h2>{img_path.name}</h2>'
                f'<div class="images">'
                f'<div><h3>Original</h3>'
                f'<img src="data:image/jpeg;base64,{orig_b64}"></div>'
                f'<div><h3>Detection</h3>'
                f'<img src="data:image/jpeg;base64,{viz_b64}"></div>'
                f'</div>'
                f'<div class="data">'
                f'<div>{grid_html}</div>'
                f'<div>{meas_html}</div>'
                f'</div>'
                f'</div>'
            )

            self.stdout.write(f'  OK {img_path.name}')

        html = _build_html(cards)
        output_path.write_text(html)
        self.stdout.write(f'\nWrote {output_path}')


def _build_error_card(img_path: Path, image: np.ndarray) -> str:
    orig_b64 = _encode_file(img_path)
    return (
        f'<div class="card error">'
        f'<h2>{img_path.name} (no grid detected)</h2>'
        f'<div class="images">'
        f'<img src="data:image/jpeg;base64,{orig_b64}">'
        f'</div></div>'
    )


def _build_grid_table(analysis: dict) -> str:
    """Build a 9x9 HTML table showing color and size."""
    color_css = {
        'GREEN': '#4caf50',
        'CYAN': '#00bcd4',
        'BLUE': '#2196f3',
        'RED': '#f44336',
        'YELLOW': '#ffeb3b',
    }
    rows = ['<h3>Detected Grid</h3><table class="grid">']
    for r in range(9):
        rows.append('<tr>')
        for c in range(9):
            idx = r * 9 + c
            detail = analysis['cell_details'][idx]
            color = detail['color']
            size = detail['size']
            if color:
                bg = color_css.get(color, '#999')
                text_color = '#000' if color == 'YELLOW' else '#fff'
                rows.append(
                    f'<td style="background:{bg};color:{text_color}">'
                    f'{size}</td>'
                )
            else:
                rows.append('<td class="empty"></td>')
        rows.append('</tr>')
    rows.append('</table>')
    return '\n'.join(rows)


def _build_measurements_table(measurements: list) -> str:
    """Build a table of diameter_ratio measurements."""
    if not measurements:
        return '<p>No circles detected</p>'

    rows = [
        '<h3>Measurements</h3>',
        '<table class="meas">',
        '<tr><th>Cell</th><th>Color</th>'
        '<th>Size</th><th>Diameter Ratio</th></tr>',
    ]
    for m in measurements:
        rows.append(
            f'<tr><td>{m["index"]}</td><td>{m["color"]}</td>'
            f'<td>{m["size"]}</td><td>{m["diameter_ratio"]:.4f}</td></tr>'
        )
    rows.append('</table>')
    return '\n'.join(rows)


def _build_html(cards: list) -> str:
    cards_html = '\n'.join(cards)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Grid Detection Verification</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 20px; background: #f5f5f5; }}
h1 {{ text-align: center; }}
.card {{ background: #fff; border-radius: 8px; padding: 20px;
         margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
.card.error {{ border-left: 4px solid #f44336; }}
.card h2 {{ margin-top: 0; font-size: 14px; color: #666;
            word-break: break-all; }}
.images {{ display: flex; gap: 20px; flex-wrap: wrap; }}
.images img {{ max-width: 400px; height: auto; border: 1px solid #ddd; }}
.images h3 {{ margin: 0 0 8px; font-size: 13px; }}
.data {{ display: flex; gap: 30px; margin-top: 15px; flex-wrap: wrap; }}
.data h3 {{ margin: 0 0 8px; font-size: 13px; }}
table.grid {{ border-collapse: collapse; }}
table.grid td {{ width: 28px; height: 28px; text-align: center;
                 font-size: 12px; font-weight: bold;
                 border: 1px solid #ccc; }}
table.grid td.empty {{ background: #fafafa; }}
table.meas {{ border-collapse: collapse; font-size: 12px; }}
table.meas th, table.meas td {{ padding: 3px 8px; border: 1px solid #ddd;
                                 text-align: left; }}
table.meas th {{ background: #f0f0f0; }}
</style>
</head>
<body>
<h1>Grid Detection Verification</h1>
<p style="text-align:center;color:#888;">
  Size thresholds (diameter_ratio): t1=0.717, t2=0.886, t3=1.054, t4=1.223
</p>
{cards_html}
</body>
</html>"""
