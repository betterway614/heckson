# YOU TIME

YOU TIME is an AI life-cinema prototype. It lets a user record daily memories as text and images, stores those memories through a FastAPI backend, and turns selected memories into diary or story-generation tasks that can be polished into different social-writing styles.

The project now includes a Vue3 frontend, a FastAPI + SQLAlchemy backend, and a SQLite-friendly local setup so the full integration flow can run without a local PostgreSQL service.

## What The App Does

1. A user writes a memory and optionally uploads images.
2. The frontend creates a `Memory` record and uploads related media files.
3. The user chooses a story style and creates a `Generation` task from one or more memories.
4. The backend starts the VLM/LLM workflow and exposes progress through Server-Sent Events.
5. The frontend displays the generated diary/story, supports polish styles, allows prompt edits, and can extract emotion labels.
6. Diary and collection views query historical memories and generations by date.

## Architecture

```text
frontend/
  src/App.vue              Vue3 application shell and user flows
  api/client.ts            TypeScript API client for FastAPI endpoints
  types/api.ts             Shared frontend API types

app/
  main.py                  FastAPI application and router registration
  api/                     Memories, media, templates, generation routes
  models/                  SQLAlchemy ORM models
  schemas/                 Pydantic request and response schemas
  services/                ASR, VLM, LLM, image, TTS service wrappers
  workflows/               Multi-step diary and image generation workflows
  templates/               Style and polish templates

tests/
  test_api/                API endpoint tests
  *_smoke.py               Workflow and integration smoke tests
```

The backend owns persistence and AI workflow orchestration. The frontend is intentionally thin: it calls the public API, listens to SSE progress, and renders the current user journey.

## Tech Stack

- Backend: FastAPI, SQLAlchemy asyncio, Pydantic, SSE streaming
- Database: SQLite by default for local development; PostgreSQL remains supported
- Frontend: Vue3, Vite, TypeScript
- AI integrations: DashScope-compatible service wrappers for LLM, VLM, image, ASR, and TTS tasks
- Tests: Pytest, pytest-asyncio, HTTPX ASGI transport

## Local Setup

### 1. Clone and create a Python environment

```bash
git clone https://github.com/betterway614/heckson.git
cd heckson
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

The default database is SQLite:

```env
DATABASE_URL=sqlite+aiosqlite:///./you_time.db
```

To use PostgreSQL instead:

```env
DATABASE_URL=postgresql+asyncpg://betterway:password@localhost:5432/you_time
```

AI features require a DashScope key:

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
```

If the key is omitted, database-backed API routes can still be exercised, but real AI workflow calls may fail when they reach external model services.

### 3. Start the backend

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

Useful endpoints:

- `GET /health`
- `POST /api/memories/`
- `GET /api/memories/?date=YYYY-MM-DD`
- `GET /api/memories/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /api/memories/{memory_id}/media`
- `POST /api/media/upload`
- `GET /api/generations/?date=YYYY-MM-DD`
- `POST /api/generations/`
- `GET /api/generations/{generation_id}/stream`
- `POST /api/generations/{generation_id}/polish-diary`
- `POST /api/generations/{generation_id}/extract-emotion`
- `GET /api/templates/styles`

### 4. Start the Vue frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server will print the local URL. By default, the frontend calls `http://localhost:8000`. To change that:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Data Model Concepts

- `User`: currently represented by a fixed test user ID until authentication is added.
- `Memory`: one dated memory entry with optional text, mood tag, metadata, and related media.
- `Media`: uploaded image/audio assets associated with a memory.
- `Generation`: a diary/story generation job built from memory IDs, style keys, progress state, VLM metadata, editable prompt fields, and final output status.
- `Output`: generated artifacts produced by later workflow stages.

## Frontend Flow

The Vue app has four main views:

- `今日记录`: create memories, upload images, select a style, and launch generation.
- `日记`: choose a date, load memories from `GET /api/memories/`, and load generation records from `GET /api/generations/`.
- `故事详情`: view original text, request polish styles, save edited prompt text, and extract emotion labels.
- `故事集`: load memories from the last 30 days and group them by date.

Frontend style keys are mapped before generation:

| Frontend key | Backend style key |
| --- | --- |
| `warm` | `watercolor` |
| `cool` | `manga_jp` |
| `humor` | `cartoon` |
| `dramatic` | `comic_shuangwen` |

Polish tabs map to backend polish styles:

| Tab | Backend style key |
| --- | --- |
| `polished` | `polished` |
| `wechat` | `moments` |
| `xiaohongshu` | `xiaohongshu` |

## Testing

Run backend tests:

```bash
pytest
```

Run frontend build checks:

```bash
cd frontend
npm install
npm run build
```

The backend test suite uses the configured database URL and creates a test database/file. SQLite is the lowest-friction local path.

## Development Notes

- `app/db_types.py` provides cross-database UUID and JSON handling so SQLite and PostgreSQL can share the same ORM models.
- SQLite is intended for local development and review. PostgreSQL is still the better fit for shared environments.
- The backend currently uses a fixed user ID: `00000000-0000-0000-0000-000000000001`.
- Generation workflows may call external AI services. Keep those calls isolated from tests unless the test is explicitly an integration or smoke test.
- The frontend API client is the single integration layer for Vue components; add new route methods there before calling endpoints from components.

## Repository Scripts

The `scripts/` directory contains database helpers and quickstart notes. Use these when inspecting or resetting local data, but prefer the README flow above for the main full-stack setup.
