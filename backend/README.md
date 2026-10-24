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
| `app/lifecycle.py` | Luminosity bounds, stage durations and lifecycle paths |
| `app/seed.py` | Starting stars (one main-sequence star per spectral type) |
| `app/config.py` | Game constants; `TICK_SECONDS` env var (default 1.0) |

Pricing follows `docs/main_sequence_pricing_data.md`:
`price = 100 × (log10(L/L☉) + 5)`, with 1000 shares per star.

## Lifecycle

Each star's luminosity is generated within bounds: at startup from its spectral
type's main-sequence range (Table 1 of the pricing doc), and again whenever it
enters a new stage. After a stage change, L eases towards the new value through
the twinkle's mean reversion; a supernova jumps straight to its value. A black
hole has no light: its L and price sit at 0 and don't move. The spectral type
decides the path (section 2 of the pricing doc); mass is display only:

```text
O        main_sequence → blue_hypergiant → supernova → black_hole
B        main_sequence → red_hypergiant → supernova → neutron_star
A, F     main_sequence → blue_giant → planetary_nebula → white_dwarf
G, K, M  main_sequence → red_giant → planetary_nebula → white_dwarf
```

Giant and hypergiant bounds come from Table 4 of the pricing doc, except that a
hypergiant's lower bound is never below the top of its main-sequence range, so
becoming one is always a rally. **The bounds
for supernova, planetary nebula, white dwarf and neutron star are placeholders**
(`STAGE_L_BOUNDS` in `app/lifecycle.py`) until the real values are ready. Stage
durations are compressed for the demo. `spectral_type`, `mass` and `temperature`
are birth values and don't change as a star evolves.

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
Asset     { id, name, kind: "star", stage, spectral_type, mass, temperature, L,
            price, shares_total, shares_available }
stage     "main_sequence" | "red_giant" | "blue_giant" | "red_hypergiant"
          | "blue_hypergiant" | "supernova" | "planetary_nebula" | "white_dwarf"
          | "neutron_star" | "black_hole"
Portfolio { player_id, nickname, cash, holdings: {asset_id: qty}, net_worth }
```

Errors use FastAPI's `{"detail": ...}` body: 400 for a rejected trade (not
enough cash, shares or holdings), 404 for an unknown player/asset, 422 for an
invalid body. Quantities may be fractional; trades fill at the current price.

**WebSocket `/ws`** (server → client):

```json
{"type": "tick", "t": 12, "assets": [{"id": "sol-nova", "stage": "main_sequence", "price": 500.4, "L": 1.002}]}
{"type": "leaderboard", "rows": [{"nickname": "zaki", "net_worth": 10012.5}]}
```

`tick` is sent every tick and `leaderboard` every 5 ticks. Load `/state` once on
start, then apply `tick` messages on top.

## Not built yet

Nebulae and protostars, random events, news feed, director
endpoints, Gemma integration and persistence. State resets when the server
restarts.
