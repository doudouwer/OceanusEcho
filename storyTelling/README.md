# OceanusEcho StoryTelling

A three-act data narrative application showcasing the OceanusEcho music ecosystem through story-driven visualizations.

> For full project architecture, data models, and backend API design, see the root [README.md](../README.md) and the `docs/` directory.

---

## Architecture Overview

This is a standalone frontend app (independent from `frontend/`), sharing the FastAPI + Neo4j backend:

```
┌─────────────────────────────────────────────────────────┐
│  Browser                                                 │
│                                                          │
│  ┌──────────────────┐    ┌──────────────────────────┐   │
│  │ storyTelling     │    │ frontend                 │   │
│  │ http://:5174     │    │ http://:5173             │   │
│  │                  │    │                          │   │
│  │ Three-Act Narrative│    │ Full interactive dashboard│   │
│  └────────┬─────────┘    └────────────┬───────────┘   │
│           │  /api/* proxy              │ /api/* proxy  │
│           └──────────────┬─────────────┘               │
│                          ▼                              │
│               ┌──────────────────┐                      │
│               │ FastAPI          │                      │
│               │ http://:8000     │                      │
│               └────────┬─────────┘                      │
│                        │ bolt                           │
│                        ▼                                 │
│               ┌──────────────────┐                      │
│               │ Neo4j            │                      │
│               │ bolt://:7687     │                      │
│               └──────────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

| Service | Port | Description |
|---------|------|-------------|
| `storyTelling/` | **5174** | This app — three-act narrative (recommended demo entry) |
| `frontend/` | **5173** | Full interactive dashboard with search and cross-panel linking |
| `backend/` (FastAPI) | **8000** | Backend API, shared by both frontends |
| Neo4j | **7687** (Bolt) / **7474** (Browser) | Graph database |

---

## Quick Start

### Prerequisites

- Python 3.9+ (backend)
- Docker + Docker Compose (Neo4j)
- Node.js 18+ (frontend)
- `MC1_release/MC1_graph.json` data file in the project root (first run only)

### Step 1 — Start Neo4j + FastAPI backend

```bash
# From project root
./scripts/start.sh --import
```

This launches:
1. **Neo4j** (via Docker Compose)
2. **FastAPI backend** (`uvicorn`, port 8000)

> Include `--import` on first run to load `MC1_graph.json` into Neo4j. On subsequent restarts, run `./scripts/start.sh` without `--import`.

### Step 2 — Start the StoryTelling narrative UI

```bash
cd storyTelling
npm install   # first run or after dependency changes
npm run dev
# → http://localhost:5174
```

### Step 3 (optional) — Start the full dashboard

```bash
# in a new terminal
cd frontend
npm install   # first run or after dependency changes
npm run dev
# → http://localhost:5173
```

The **"Explore the Ecosystem"** button in the top-right of the StoryTelling UI links here.

---

## Stopping All Services

```bash
# Stop Neo4j and FastAPI
./scripts/stop.sh

# Stop frontend: Ctrl+C in the terminal running npm run dev
```

---

## Port Conflicts

Override default ports manually:

```bash
# Backend
API_PORT=8001 ./scripts/start.sh --import

# To change storyTelling or frontend ports, edit their respective vite.config.ts
```

> Note: after changing the storyTelling port, update the `href` target in `storyTelling/src/App.tsx` to match.

---

## The Three-Act Structure

| Act | Title | Story | Panels |
|-----|-------|-------|--------|
| **I** | Rise of a Star | Sailor Shift's career trajectory and influence network | Career Arc / Influence Galaxy |
| **II** | Genre Diffusion | Oceanus Folk's spread pattern and cross-genre fusion | Genre Flow / Influence Galaxy |
| **III** | Tomorrow's Stars | Rising star prediction and profile comparison | Star Profiler / Career Arc / Influence Galaxy |

---

## API Verification

Once the backend is running, verify all endpoints:

```bash
cd backend
python -m scripts.test_services
```

---

## File Structure

```
storyTelling/
├── src/
│   ├── App.tsx         # Root component: Act state machine, panel rendering, data fetching
│   ├── api.ts          # API client: typed wrappers for all 5 backend endpoints
│   ├── storyData.ts    # Act definitions, narration copy, and scene scripts
│   ├── styles.css      # Full stylesheet: design system, animations, all component styles
│   └── main.tsx        # React entry point
├── index.html
├── vite.config.ts      # Vite config: port 5174, /api proxy → 8000
├── tsconfig.json
└── package.json
```
