# Frontend

Minimal React + Vite + TypeScript app. Start work in `src/App.tsx`; styles live
in `src/styles/theme.css`.

Use Node.js 22.12+ and its included npm package manager. From this directory:

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend runs independently of the backend.

```powershell
npm run typecheck
npm run build
```

After installing Node.js, close and reopen your terminal so it can find `node`
and `npm`. If PowerShell blocks `npm.ps1`, use `npm.cmd` in place of `npm`.

The development server proxies `/api/*` to `http://127.0.0.1:8000/*`.
For example, `/api/health` reaches the backend's `/health` endpoint.
