# Frontend

React + Vite + TypeScript frontend. `src/App.tsx` composes the ranked market,
news feed, and selected-star chart/details. Styles live in `src/styles/theme.css`
and the chart component's stylesheet.

The market is connected to the backend's real prices and stellar lifecycle
data. Selection stays on the same star while rankings change. Price changes
are absolute CR differences from the previous received tick; the initial
snapshot has no comparison baseline.

News and star insights still use literal placeholder labels because the
backend does not provide them. No generated prices, dates, headlines, or
trading actions are included.

Use Node.js 22.12+ and its included npm package manager. From this directory:

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`. To receive live data, also run the backend on port
8000 in a separate terminal. From the repository root, after following the
backend setup in the root README:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload
```

The frontend keeps the last received prices during an interruption and
automatically reconnects. A fresh connection reloads the snapshot and history,
including after a backend restart. An open feed with no advancing tick for
30 seconds also reconnects. The interface provides a manual retry button.

```powershell
npm run typecheck
npm test
npm run build
```

After installing Node.js, close and reopen your terminal so it can find `node`
and `npm`. If PowerShell blocks `npm.ps1`, use `npm.cmd` in place of `npm`.

## Integration handoff

- `src/market/backend.ts` validates backend messages and maps them into frontend
  view models. Keep server field names at this boundary.
- `src/market/useLiveMarket.ts` loads `GET /state`, then each asset's
  `GET /assets/{id}/history`, and consumes tick messages from `/ws`. It opens the
  socket first and buffers ticks while the snapshot loads.
- `src/market/candles.ts` builds OHLC candles from the actual tick/price samples,
  grouped into 10 simulation ticks per candle. The chart uses tick numbers,
  preserves gaps, and does not invent timestamps or volume.
- Lifecycle labels and colours follow the server stage. Spectral type and
  temperature are labelled as birth values because the server keeps them fixed.
- `tests/` covers validation, snapshot/tick/history merging, server restart
  handling, and candle aggregation. Tests use Node's built-in runner.

Vite proxies `/api/*` to `http://127.0.0.1:8000/*` and `/ws` to the backend
WebSocket. Production hosting must route `/state`, `/assets/*`, and `/ws` to
the backend on the frontend's origin. `npm run preview` only previews the static
build; use `npm run dev` for the local API proxy.
