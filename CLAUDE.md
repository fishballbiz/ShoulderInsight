# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart Shoulder Rehabilitation AI Diagnostic Platform for Huifu Rehabilitation Clinic. Automates analysis of medical rehabilitation app screenshots using Google Gemini API to extract training data.

## Development Commands

```bash
# Build and start services (detached mode)
./dc up

# Build Docker image
./dc build dev

# Enter development container (bash)
./dc dev

# View logs
./dc logs

# Stop services
./dc down

# Run Django management commands
./dc manage collectstatic

# Deploy to GCP Cloud Run
./dc publish
```

## Architecture

### Stack
- Django 5.2+ with Daphne (ASGI)
- File-based sessions (no database)
- Google GenAI SDK (Gemini API)
- WeasyPrint for PDF generation
- Bootstrap 5 + Vanilla JS frontend

### Apps
- **diagnosis**: Core workflow - image upload, AI analysis, result display

### Workflow
```
Upload (operator + image) → Analyzing (AJAX triggers AI) → Result (display extracted data)
```

### Key Files
- `diagnosis/ai_service.py` - Gemini API integration
- `diagnosis/prompts.py` - AI extraction prompt template
- `diagnosis/views.py` - Upload, analyzing, result views

### URL Routes
- `/diagnosis/upload/` - Single image upload form
- `/diagnosis/analyzing/<uuid>/` - Processing page with AJAX trigger
- `/diagnosis/api/analyze/<uuid>/` - AI analysis API endpoint
- `/diagnosis/result/<uuid>/` - Results display

## Configuration

### Environment
- `MEDIA_ROOT` - Image upload directory (default: `/media`)
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode flag

### File Storage
- Uploads: `{MEDIA_ROOT}/uploads/{uuid}.{ext}`
- Sessions: `/tmp/django_sessions` (file-based)

## Localization

- Language: Traditional Chinese (zh-hant)
- Timezone: Asia/Taipei
