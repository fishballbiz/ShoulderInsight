# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart Shoulder Rehabilitation AI Diagnostic Platform for Huifu Rehabilitation Clinic. Automates analysis of medical rehabilitation app screenshots using Google Vertex AI (Gemini Pro Vision) to generate diagnostic reports.

## Development Commands

```bash
# Build and start all services
./dc up

# Build Docker image
./dc build dev

# Enter development container (bash)
./dc dev

# Run Django management commands
./dc manage migrate
./dc manage createsuperuser
./dc manage makemigrations

# View logs
./dc logs

# Stop services
./dc down
```

## Architecture

### Stack
- Django 5.2+ with Daphne (ASGI)
- PostgreSQL 15
- Google Cloud Vertex AI SDK
- WeasyPrint for PDF generation
- Bootstrap 5 + Vanilla JS frontend

### Apps
- **accounts**: Custom User model with Role and Clinic relationships
- **diagnosis**: Core workflow - Patient → Examination → Image/Diagnosis

### Key Models

**accounts.User**: Extends AbstractUser with `role` (ForeignKey to Role) and `clinic` (ForeignKey to Clinic)

**diagnosis workflow**:
```
Patient (1) → (N) Examination (UUID PK) → (N) Image (slot_type: SLOT_A/B/C)
                                       → (1) Diagnosis (raw_data, clinical_summary, risk_assessment)
```

Examination status flow: `PENDING → PROCESSING → COMPLETED/FAILED`

### Image Slots
- **SLOT_A**: Basic Info / Training Volume (tables, text)
- **SLOT_B**: Trajectory & Heatmap (visual charts)
- **SLOT_C**: Comprehensive Analysis (comparison)

### URL Routes
- `/diagnosis/upload/` - 3-slot image upload form
- `/diagnosis/analyzing/<uuid>/` - Processing status with auto-redirect
- `/diagnosis/result/<uuid>/` - Results dashboard

## Localization

- Language: Traditional Chinese (zh-hant)
- Timezone: Asia/Taipei
- All model verbose_name and admin labels are in Chinese

## File Structure Patterns

- Templates: `{app}/templates/{app}/*.html`
- Image uploads: `uploads/YYYY/MM/DD/{uuid}.ext`
- Static files served via Django in DEBUG mode
