# Frontend

React + Vite + TypeScript frontend. `src/App.tsx` composes the ranked market,
news feed, and selected-star chart/details. Styles live in `src/styles/theme.css`
and the chart component's stylesheet.

The market is connected to the backend's real prices and stellar lifecycle
data. Selection stays on the same star while rankings change. Price changes
are absolute CR differences from the previous received tick; the initial
snapshot has no comparison baseline.

The news column loads recent headlines from `/state` and receives new ones over
the WebSocket. Headlines and bodies come from the backend (Gemma or its server
fallback), with the real event tick and links to every related star. The
frontend does not invent headlines, wall-clock dates or price impacts. Star
insights still use a placeholder because the backend does not provide them.

News is shown newest event tick first and limited to 50 items. Reconnects load a
fresh snapshot; buffered live news is merged by ID so overlapping snapshots
do not duplicate stories. Headlines can arrive after later price ticks because
the model writes asynchronously. Expanding a story stays attached to its ID as
new stories arrive. Events includes lifecycle changes and events; Rumours shows
rumours. The backend publishes lifecycle and event news. Empty feeds show a
real empty state, and malformed news does not disconnect working prices.

The selected star's candle chart marks related news within its visible history.
Markers use real event ticks; grouped markers sit at their earliest story tick
and offer each headline separately. Click a marker or its headline choice to
open, reveal and focus that story in the news feed, including if a filter had
hidden it. Closely spaced stories are grouped so their buttons stay usable on
narrow charts. Markers do not imply that a story caused a particular price move.

Players can join with a nickname, buy and sell fractional shares, and see cash,
net worth and holdings. The browser remembers the player ID; a server restart
clears that session after the server reports the player is missing. Balances
refresh every five seconds and after joining, trading or reconnecting.

Buy orders have quantity shortcuts for 1, 5, 10 and 25 shares alongside typed
entry. Sell orders use a slider from 1 share to the selected star's current
holding, including a fractional maximum. Manual entry remains available for
fractional sales; holdings below 1 share use it automatically. Choosing a
quantity does not submit an order.
Buy shortcuts and submission are disabled when the latest quote already exceeds
available cash. A quote that fits can still be rejected if execution-price
impact or a later tick pushes the final cost higher. Rejected orders retain the
current portfolio and allow the player to choose a smaller quantity and retry.

Order estimates use the latest displayed price. Trading pressure changes the
execution price, so the server validates each order and returns the updated
portfolio. The current API does not return an execution receipt. Black-hole
orders and sells exceeding the displayed holdings are disabled. Rejected orders
show the server's reason. Lost order responses are never retried automatically;
the account must refresh before another order is allowed.

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
  `GET /assets/{id}/history`, and consumes tick/news messages from `/ws`. It opens
  the socket first and buffers both kinds while the snapshot loads.
- `src/market/news.ts` validates `{id, t, kind, headline, body, asset_ids}` from
  the backend and maintains bounded, deduplicated news. News ticks are event
  ticks and never advance the market clock or price history.
- `src/market/candles.ts` builds OHLC candles from the actual tick/price samples,
  grouped into 10 simulation ticks per candle. The chart uses tick numbers,
  preserves gaps, and does not invent timestamps or volume.
- Lifecycle labels and colours follow the server stage. Spectral type and
  temperature are labelled as birth values because the server keeps them fixed.
- `src/player/api.ts` validates player responses; `session.ts` handles persisted
  identity and request ordering; `usePlayerSession.ts` handles polling and
  reconnects. The server remains responsible for balances and fills.
- `tests/` covers validation, snapshot/tick/history merging, server restart
  handling, candle aggregation, player/order recovery, news ordering/replay, and
  chart marker placement/grouping.
  Compatibility regressions read the backend's actual stage and news-kind
  definitions. Tests use Node's
  built-in runner; no extra test dependency is needed.

## Demo controls

Open `http://localhost:5173/?director=1` to show a control that advances the
selected star to its next stage. It uses the existing
`POST /director/force_stage` endpoint. Changes appear on the next market tick;
terminal stages disable the button. This query flag only controls UI visibility,
not access to the backend endpoint. The normal page hides these controls.

## Backend teammate handoff

These remain backend work; this frontend change does not alter server code:

- Handle a positive sell quantity within the server's float tolerance when the
  player has no holding. Currently, for example, selling `1e-10` unowned shares
  reaches deletion of a missing dictionary entry and raises `KeyError`. The UI
  blocks unowned sells, but the API should reject them consistently too.
- Consider returning a trade receipt alongside the portfolio, including actual
  filled quantity, unit price and total. The frontend currently confirms an
  order and shows the returned balance without inventing an execution price.
- The news contract is now connected. Future event/rumour producers can publish
  the same `NewsItem` shape; current filters already support their kinds. The
  frontend displays lifecycle and price data received from the server.

Vite proxies `/api/*` to `http://127.0.0.1:8000/*` and `/ws` to the backend
WebSocket. Production hosting must route `/state`, `/assets/*`, `/join`, `/trade`,
`/portfolio/*`, `/director/*` and `/ws` to the backend on the frontend's origin.
The built app uses those production paths; use `npm run dev` for the configured
local API proxy.
