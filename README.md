# Star Market

Minimal boilerplate for separate frontend and backend work.

- [Frontend](frontend/README.md): React + Vite + TypeScript. Start in `frontend/src/App.tsx`.
- [Backend](backend/README.md): FastAPI. Start in `backend/app/main.py`.
- [Project plan](docs/STAR_MARKET_SPEC.md): design reference for later implementation.
- [AI teammate guidance](AGENTS.md): rough ownership and collaboration guidelines.

## Frontend

Use Node.js 22.12+ and its included npm package manager. From the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

After installing Node.js, close and reopen your terminal so it can find `node`
and `npm`. If PowerShell blocks `npm.ps1`, use `npm.cmd` in place of `npm`.

## Backend

Use Python 3.11+. From the repository root on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload
```

On macOS/Linux, use `.venv/bin/python` instead.

Health endpoint: `http://localhost:8000/health`.
API documentation: `http://localhost:8000/docs`.
Tests: `cd backend`, then `..\.venv\Scripts\python -m pytest`.
