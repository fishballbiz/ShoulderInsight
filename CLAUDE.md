# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart Shoulder Rehabilitation AI Diagnostic Platform for Huifu Rehabilitation Clinic. Analyzes medical rehabilitation app screenshots to detect shoulder diseases from pain point patterns on a 9x9 grid.

## Development Commands

```bash
./dc up              # Build and start (detached, removes orphans)
./dc down            # Stop services
./dc dev             # Enter container bash shell
./dc logs            # Tail logs
./dc manage <cmd>    # Run Django management commands
./dc publish         # Deploy to GCP Cloud Run (asia-east1)
```

No `collectstatic` needed in dev — Django's runserver serves static files directly.

## Architecture

### Stack
- Django 5.2+ with Daphne (ASGI), no database (file-based sessions)
- Google GenAI SDK (Gemini 2.5-flash) for training metadata extraction
- OpenCV (headless) for grid detection and cell analysis
- WhiteNoise + GCS bucket for static files in production
- Bootstrap 5 + Vanilla JS frontend, Traditional Chinese (zh-hant)

### Data Flow
```
Upload (multiple images) → Analyzing (AJAX POST) → Result (per-hand diagnosis)

analyze_api:
  for each image:
    parse_grid()        → grid_color[81], grid_size[81]
    analyze_training_image() → training metadata from Gemini

  _build_median_grid()  → median size per cell across all images
  accumulate_disease_scores() → per-hand disease ranking
```

### Key Modules

**`diagnosis/image_processing/`** — OpenCV grid detection pipeline
- `grid_detector.py`: 3-tier grid detection (gray color → Hough lines → contour fallback)
- `cell_analyzer.py`: HSV color detection at cell center (40% region), radius-based size via `minEnclosingCircle` (diameter_ratio = 2*radius/cell_width)

**`diagnosis/disease_mapping.py`** — Scoring engine
- Loads 11 diseases from `data/diseases.json` (each has a 81-cell grid pattern)
- Hand separation: CYAN=left, GREEN=right (patient's perspective, color determines hand, not severity)
- Scoring: `circle_size(1-5) × color_weight(RED=3, YELLOW=2, BLUE=1)`
- Multi-image: builds median grid, scores once from that
- Severity: <4 hidden, 4-8 light, 9-18 mild, >18 serious
- Shows top 2 per hand; within 3 points gap = both primary

**`diagnosis/ai_service.py`** — Gemini API (key at `/secret/gemini_api.key`)

**`diagnosis/views.py`** — All state lives in `request.session` (examination_id, image_paths, parsed_grids, ai_results, accumulated_scores)

### URL Routes
- `/diagnosis/upload/` — Multi-image upload form
- `/diagnosis/analyzing/<uuid>/` — Loading page, triggers AJAX analysis
- `/diagnosis/api/analyze/<uuid>/` — Batch analysis endpoint (POST)
- `/diagnosis/result/<uuid>/` — Per-hand disease results with grid visualization
- `/diagnosis/diseases/` — All disease definitions reference
- `/diagnosis/grid-poc/` — Grid detection debug/test page

### Data Files
- `data/diseases.json` — 11 disease definitions with grid_color patterns
- `data/interpretation_rules/` — Reference images per disease + `rules.md`
- `data/test_inputs/` — Test images for grid detection POC

## Configuration

- `MEDIA_ROOT` env var (default `/media`) — uploaded images
- `STATIC_ROOT` fixed at `/tmp/staticfiles` — only used in Docker build
- Sessions at `/tmp/django_sessions` (file-based, no DB)
- Gemini API key at `/secret/gemini_api.key` (not in repo)

## Design Decisions

- **No database**: Each examination is session-scoped. Stateless Cloud Run deployment.
- **Median grid merging**: Prevents single outlier image from skewing diagnosis across multiple uploads.
- **Cell center detection**: Only checks center 40% of each cell to avoid edge artifacts.
- **Calibrated size thresholds**: Computed per batch from actual pixel ratios, dividing into 5 equal parts.
