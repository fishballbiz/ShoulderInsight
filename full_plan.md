# Smart Shoulder Rehabilitation AI Diagnostic Platform - Comprehensive Plan

## 1. Executive Summary

**Project Name:** Smart Shoulder Rehabilitation AI Diagnostic Platform
**Client:** Huifu Rehabilitation Clinic
**Goal:** Build a production-ready, containerized web application that automates the analysis of medical rehabilitation app screenshots using Generative AI (Google Vertex AI/Gemini).

### Problem Statement
Therapists currently spend excessive time (40 mins/report) manually transcribing data from the "Open Shoulder App" screenshots into medical records. The raw data is difficult for patients to understand, leading to poor compliance.

### Solution
A web-based service where therapists upload screenshots. The system uses AI to:
1.  **Extract Data (OCR):** Read numerical values (training counts, angles).
2.  **Interpret Visuals:** Analyze heatmaps for pain zones.
3.  **Diagnose:** Cross-reference data with a clinical knowledge base of 11 shoulder pathologies.
4.  **Report:** Generate a professional PDF report (reducing time to 3 mins).

---

## 2. Business Requirements & Logic

### Key Objectives
1.  **Adaptability:** Accept screenshots as input (no API integration required).
2.  **Extensibility:** Architecture must support future expansion (knee, spine).
3.  **Model Agnostic:** Backend abstraction to allow swapping AI models.
4.  **Efficiency:** Drastic reduction in report generation time.
5.  **Patient-Centric:** Translate technical terms into natural language.

### Core Features
-   **Context-Aware Upload:** Three distinct slots for different screenshot types:
    -   **Slot A:** Basic Info / Training Volume (Tables, Text).
    -   **Slot B:** Trajectory & Heatmap (Visual Charts).
    -   **Slot C:** Comprehensive Analysis (Comparison).
-   **AI Analysis:** Two-stage process (Image-to-Data -> Data-to-Insight).
-   **Reporting:** Dashboard view and PDF generation.

---

## 3. Technical Architecture

### Stack Overview
| Layer | Technology | Details |
|-------|------------|---------|
| **Infrastructure** | Docker & Docker Compose | Local development, dev-prod parity |
| **Backend** | Python 3.12+, Django 5.0+ | Core application logic |
| **Server** | Daphne (ASGI) | Async server for Django |
| **Database** | PostgreSQL 15 | Containerized database |
| **Frontend** | HTML5, Bootstrap 5, Vanilla JS | Lightweight, responsive UI |
| **AI** | Google Cloud Vertex AI SDK | Gemini Pro Vision models |
| **Storage** | Google Cloud Storage (GCS) | Image and PDF storage (local volume for dev) |
| **PDF Engine** | WeasyPrint | Professional report generation |

---

## 4. Implementation Roadmap

### Step 1: Project Initialization & Infrastructure
**Goal:** Set up a containerized Django environment.
-   **Dockerfile:** Base `python:3.12-slim`, install system deps (`libpango`, `libopenjp2` for WeasyPrint).
-   **docker-compose.yml:** Services for `db` (Postgres 15) and `web` (Daphne).
-   **Django Setup:** Initialize project `config` and apps `accounts`, `diagnosis`.

### Step 2: Database Modeling
**Goal:** Store diagnostic data and analysis results.
-   **`accounts.CustomUser`:** Extend AbstractUser (is_therapist, hospital_name).
-   **`diagnosis.DiagnosticEvent`:** Track patient, therapist, status, timestamp.
-   **`diagnosis.UploadedImage`:** Store image and `slot_type` (A, B, or C).
-   **`diagnosis.AnalysisResult`:** Store raw JSON data, clinical summary, and risk assessment.

### Step 3: Frontend Implementation
**Goal:** Responsive UI for uploading and viewing.
-   **Upload Page (`upload.html`):** 3-slot dropzone form using Vanilla JS. Tags images with `slot_type`.
-   **Dashboard (`result.html`):** Display quantitative tables, risk traffic light system, and editable AI summary.
-   **Styling:** Bootstrap 5 via CDN.

### Step 4: AI Core Logic (The "Brain")
**Goal:** Implement `ai_service.py` interfacing with Vertex AI.
-   **Stage 1 (Image-to-Data):**
    -   Slot A: Extract Date, Sessions, Actions.
    -   Slot B: Analyze heatmap (Zone 1 vs Zone 2), extract Hold Time.
-   **Stage 2 (Data-to-Insight):**
    -   Aggregate data.
    -   System Prompt: Apply 11 Shoulder Pathologies Rules.
    -   Output: Natural language summary and risk assessment.

### Step 5: Report Generation
**Goal:** Generate professional outputs.
-   **PDF Generation:** Use WeasyPrint to render `report_pdf.html` into a downloadable PDF.
-   **Review:** Allow therapists to edit the AI suggestion before finalizing.

### Step 6: Configuration & Security
-   **Environment Variables:** Manage secrets (DB creds, API keys) via `.env`.
-   **GCP Integration:** Mount Service Account JSON for Vertex AI and GCS access.

---

## 5. Verification Plan

### Automated Testing
-   **Unit Tests:** Test Django models and utility functions.
-   **Integration Tests:** Mock Vertex AI responses to test the full pipeline from upload to report generation without incurring costs/latency.

### Manual Verification
1.  **Infrastructure:** `docker-compose up --build` runs without errors.
2.  **Upload Flow:** Drag & drop images into all 3 slots, verify previews, submit form.
3.  **AI Processing:** Verify that "Processing" status updates to "Completed" and data is correctly extracted (mocked or real).
4.  **PDF Output:** Download PDF and verify layout, fonts, and data accuracy.
