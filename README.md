# Cube Analytics Monorepo

This repository contains the services that make up the Cube analytics workflow:

| Workspace | Purpose | Entry point |
| --- | --- | --- |
| `dvdrental-cube` | Cube semantic layer and API | `npm run cube:dev` |
| `cubecore` | Generates Cube models from Neo4j metadata | `npm run core:generate` |
| `cubecoreai` | Interactive Gemini analytics client | `npm run ai:chat` |

## Setup

Install the JavaScript workspace from the repository root:

```powershell
npm install
```

Install Python dependencies for each workspace in its own virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r cubecore\requirements.txt -r cubecoreai\requirements.txt
```

Create `dvdrental-cube/.env` for Cube and configure the Python clients with
`GEMINI_API_KEY` from `cubecoreai/.env.example` before running them. Credentials
should remain in local environment files and never be committed.

## Run

Start the Cube API directly from the root:

```powershell
npm run cube:dev
```

Or start the Dockerized Cube service:

```powershell
npm run docker:up
```

Generate models and start the AI client with:

```powershell
npm run core:generate
npm run ai:chat
```