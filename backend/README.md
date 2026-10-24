# Backend

Owner: backend teammate.

Requires Python 3.11 or later. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
python -m uvicorn app.main:app --app-dir backend --reload
```

On macOS/Linux, activate with `source .venv/bin/activate`. Run the tests with
`cd backend` then `python -m pytest`.

Check [health](http://127.0.0.1:8000/health) or open the
[API docs](http://127.0.0.1:8000/docs).

## Layout

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app, routes, `/ws` broadcast, tick loop |
| `app/models.py` | Request/response shapes shared with the frontend |
| `app/market.py` | In-memory game state: stars, players, trades, net worth |
| `app/pricing.py` | Price formula and per-tick luminosity noise |
| `app/seed.py` | Starting stars (one main-sequence star per spectral type) |
| `app/config.py` | Game constants; `TICK_SECONDS` env var (default 1.0) |

Pricing follows `docs/main_sequence_pricing_data.md`:
`price = 100 × (log10(L/L☉) + 5)`, with 1000 shares per star.

## API

The frontend dev server proxies `/api/*` here, so `/join` is `/api/join` from
the browser.

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/join` | `{nickname}` | `{player_id}` |
| GET | `/state` | | `{t, assets: Asset[], leaderboard: {nickname, net_worth}[]}` |
| GET | `/assets/{id}/history` | | `{t, price}[]` (last 600 ticks) |
| GET | `/portfolio/{player_id}` | | `Portfolio` |
| POST | `/trade` | `{player_id, asset_id, side: "buy"\|"sell", qty}` | `Portfolio` |

```text
Asset     { id, name, kind: "star", spectral_type, mass, temperature, L, price,
            shares_total, shares_available }
Portfolio { player_id, nickname, cash, holdings: {asset_id: qty}, net_worth }
```

Errors use FastAPI's `{"detail": ...}` body: 400 for a rejected trade (not
enough cash, shares or holdings), 404 for an unknown player/asset, 422 for an
invalid body. Quantities may be fractional; trades fill at the current price.

**WebSocket `/ws`** (server → client):

```json
{"type": "tick", "t": 12, "assets": [{"id": "sol-nova", "price": 500.4, "L": 1.002}]}
{"type": "leaderboard", "rows": [{"nickname": "zaki", "net_worth": 10012.5}]}
```

`tick` is sent every tick and `leaderboard` every 5 ticks. Load `/state` once on
start, then apply `tick` messages on top.

## Not built yet

Stellar lifecycle stages, random events, nebulae, news feed, director
endpoints, Gemma integration and persistence. State resets when the server
restarts.
