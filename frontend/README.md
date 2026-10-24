# Frontend

React + Vite + TypeScript frontend. `src/App.tsx` composes the ranked market,
news feed, and selected-star chart/details. Styles live in `src/styles/theme.css`
and the chart component's stylesheet.

The default screen uses literal placeholder labels only. It has no generated
prices, dates, headlines, simulated feed, or backend requests. Selection,
ranking controls, news filters, and headline expansion work locally.

When integration is agreed, supply a `MarketView` to `App`. The existing
`src/market/types.ts` contains frontend view models, not an assumed backend API.
The UI sorts assets and animates changes in rank, preserves the selected star,
and renders supplied OHLC history. Adapt backend messages at this boundary;
news timestamps are expected in epoch milliseconds. Candle history is rendered
as supplied, without guessing its interval or generating missing points.

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
