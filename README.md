# Atelier — Sketch to Sewing Pattern

A multi-agent AI system that converts fashion sketches or garment photos into complete sewing patterns with step-by-step instructions and a printable PDF.

Built with FastAPI, LangGraph, and Claude's vision API.

![Atelier app screenshot](assets/Screenshot%202026-06-28%20at%2011.43.13 AM.png)

---

## How it works

A LangGraph pipeline coordinates four specialised Claude agents in sequence:

```
Image Upload
     │
     ▼
Vision Agent        → identifies garment type, silhouette, construction details
     │
     ▼
Measurement Agent   → calculates pattern piece dimensions from body measurements
     │
     ▼
Pattern Agent       → drafts each piece with seam allowances, notches & markings
     │
     ▼
Instructions Agent  → writes ordered sewing steps tailored to your skill level
     │
     ▼
PDF Renderer        → assembles everything into a printable A4 pattern PDF
```

Each agent receives only the output it needs from the previous step — clean, typed handoffs via Pydantic models through shared LangGraph state.

---

## Tech stack

| Layer       | Technology                         |
|-------------|------------------------------------|
| Backend     | FastAPI + Uvicorn                  |
| AI Pipeline | LangGraph                          |
| AI Model    | Claude (Anthropic) — vision + text |
| PDF         | ReportLab                          |
| Validation  | Pydantic v2                        |
| Templating  | Jinja2                             |
| Config      | pydantic-settings                  |

---

## Project structure

```
app/
├── api/
│   └── routes/
│       ├── health.py        # GET /health
│       └── pattern.py       # POST /api/v1/generate, GET /api/v1/download/{filename}
├── graph/
│   ├── state.py             # Shared LangGraph state (PatternState)
│   ├── graph.py             # Pipeline assembly & compilation
│   ├── nodes/
│   │   ├── vision.py
│   │   ├── measurement.py
│   │   ├── pattern.py
│   │   ├── instructions.py
│   │   └── pdf_renderer.py
│   └── utils.py             # Shared JSON extraction utility
├── schemas/
│   ├── requests.py          # Inbound API contract
│   └── responses.py         # Outbound API contract + state mapper
├── services/
├── config.py                # pydantic-settings config
└── main.py                  # FastAPI app factory
```

---

## Getting started

### Prerequisites

- Python 3.11+
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (recommended)
- An [Anthropic API key](https://console.anthropic.com)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/image-to-sewing-pattern-converter
cd image-to-sewing-pattern-converter

# 2. Create and activate conda environment
conda create -n atelier python=3.11
conda activate atelier

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 5. Run the app
python run.py
```

Visit `http://localhost:8000` to use the app.  
API docs available at `http://localhost:8000/docs`.

### Docker

```bash
docker compose up --build
```

---

## API

### `POST /api/v1/generate`

Accepts `multipart/form-data`:

| Field            | Type   | Description                              |
|------------------|--------|------------------------------------------|
| `image`          | file   | Garment photo or fashion sketch          |
| `bust`           | float  | Bust/chest measurement in cm             |
| `waist`          | float  | Waist measurement in cm                  |
| `hips`           | float  | Hips measurement in cm                   |
| `height`         | float  | Height in cm                             |
| `shoulder_width` | float  | Shoulder width in cm                     |
| `skill_level`    | string | `beginner` / `intermediate` / `advanced` |

Returns a JSON response with garment analysis, pattern pieces, sewing steps, materials list, and a `pdf_path` for download.

### `GET /api/v1/download/{filename}`

Downloads the generated PDF pattern.

### `GET /health`

Returns app version and model info.

---

## Design decisions

**Why LangGraph?**  
The pipeline has clear sequential dependencies — each agent needs the previous agent's output. LangGraph's conditional edges let the pipeline abort early and cleanly if any agent fails, rather than propagating bad data downstream.

**Why separate request/response schemas from state models?**  
Internal state carries raw image data, intermediate outputs, and pipeline metadata that should never be exposed via the API. The schema boundary is explicit and the `state_to_response` mapper is the only place that crosses it.

**Why ReportLab over WeasyPrint?**  
WeasyPrint requires system-level Pango/Cairo libraries that are difficult to install reliably on Apple Silicon with Miniconda. ReportLab is pure Python with no system dependencies, making local development and Docker builds much simpler.

---

## Known limitations

- Pattern pieces are described with dimensions but not rendered as drawable SVG shapes
- No user authentication — PDFs are stored locally and accessible by filename
- Pipeline runs synchronously — large/complex garments can take 30–60 seconds

---

## Roadmap

- [ ] SVG pattern piece rendering
- [ ] Async job queue (Celery + Redis) for long-running pipelines
- [ ] User accounts and pattern history
- [ ] Multi-size grading

---

## License

MIT