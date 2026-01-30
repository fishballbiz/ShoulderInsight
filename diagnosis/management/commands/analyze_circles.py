"""Management command to analyze circle sizes from test input images."""
from pathlib import Path

import cv2
import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand

from diagnosis.image_processing.cell_analyzer import (
    _detect_color_at_center,
    _get_color_mask,
)
from diagnosis.image_processing.grid_detector import detect_grid_by_color, extract_cells


class Command(BaseCommand):
    help = 'Analyze circle sizes from test_inputs and output circle_sizes.txt'

    def handle(self, *args, **options):

        test_dir = Path(settings.BASE_DIR) / 'data' / 'test_inputs'
        output_path = Path(settings.BASE_DIR) / 'data' / 'circle_sizes.txt'

        if not test_dir.exists():
            self.stderr.write(f'Test directory not found: {test_dir}')
            return

        image_paths = sorted(test_dir.glob('*.jpeg'))
        if not image_paths:
            self.stderr.write('No JPEG images found in test_inputs/')
            return

        self.stdout.write(f'Found {len(image_paths)} images')

        rows = []
        all_ratios = []

        for img_path in image_paths:
            image = cv2.imread(str(img_path))
            if image is None:
                self.stdout.write(f'  SKIP {img_path.name}: could not load')
                continue

            grid_info = detect_grid_by_color(image)
            if grid_info is None:
                self.stdout.write(f'  SKIP {img_path.name}: no grid detected')
                continue

            cell_size = grid_info['cell_size']
            cells = extract_cells(image, grid_info)

            for idx, cell in enumerate(cells):
                if cell.size == 0:
                    continue

                center_color, _ = _detect_color_at_center(cell)
                if center_color is None:
                    continue

                hsv = cv2.cvtColor(cell, cv2.COLOR_BGR2HSV)
                mask = _get_color_mask(hsv, center_color)
                cell_area = cell.shape[0] * cell.shape[1]
                colored_pixels = cv2.countNonZero(mask)
                pixel_ratio = colored_pixels / cell_area

                diameter_gu = np.sqrt(pixel_ratio) * 2

                rows.append(
                    f'{img_path.name} | {idx:2d} | {center_color:6s} '
                    f'| {pixel_ratio:.4f} | {diameter_gu:.3f}'
                )
                all_ratios.append(pixel_ratio)

            self.stdout.write(f'  OK {img_path.name}: cell_size={cell_size}px')

        with open(output_path, 'w') as f:
            f.write('image_file | cell_index | color | pixel_ratio '
                    '| diameter_grid_units\n')
            f.write('-' * 72 + '\n')
            for row in rows:
                f.write(row + '\n')

        self.stdout.write(f'\nWrote {len(rows)} measurements to {output_path}')

        if all_ratios:
            all_ratios.sort()
            n = len(all_ratios)
            self.stdout.write(f'\nSummary ({n} circles):')
            self.stdout.write(f'  Min ratio: {all_ratios[0]:.4f}')
            self.stdout.write(f'  Max ratio: {all_ratios[-1]:.4f}')
            self.stdout.write(f'  Median:    {all_ratios[n // 2]:.4f}')

            rng = all_ratios[-1] - all_ratios[0]
            t1 = all_ratios[0] + rng * 0.20
            t2 = all_ratios[0] + rng * 0.40
            t3 = all_ratios[0] + rng * 0.60
            t4 = all_ratios[0] + rng * 0.80

            self.stdout.write(f'\nSuggested 5-level thresholds:')
            self.stdout.write(f'  Size 1: < {t1:.4f}')
            self.stdout.write(f'  Size 2: {t1:.4f} - {t2:.4f}')
            self.stdout.write(f'  Size 3: {t2:.4f} - {t3:.4f}')
            self.stdout.write(f'  Size 4: {t3:.4f} - {t4:.4f}')
            self.stdout.write(f'  Size 5: > {t4:.4f}')

            bins = [0, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35,
                    0.40, 0.50, 0.60, 0.80, 1.0]
            self.stdout.write(f'\nDistribution:')
            for i in range(len(bins) - 1):
                count = sum(
                    1 for r in all_ratios if bins[i] <= r < bins[i + 1]
                )
                bar = '#' * count
                self.stdout.write(
                    f'  {bins[i]:.2f}-{bins[i + 1]:.2f}: {count:3d} {bar}'
                )
