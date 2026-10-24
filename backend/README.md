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
| `app/pricing.py` | Price formula, trading pressure and per-tick luminosity noise |
| `app/lifecycle.py` | Luminosity bounds, stage durations and lifecycle paths |
| `app/seed.py` | Starting stars (one main-sequence star per spectral type) |
| `app/config.py` | Game constants and env vars |
| `app/ai/client.py` | Calls Gemma through Ollama's chat API with a JSON schema |
| `app/ai/prompts.py` | Prompts, reply schemas and template fallbacks |
| `app/ai/worker.py` | Background task that runs Gemma calls away from the tick loop |

## Gemma

Gemma writes the news text. It never sets prices or balances. It runs locally
through Ollama:

```sh
ollama pull gemma4:e4b-it-q4_K_M
ollama serve   # if the Ollama app isn't already running
```

| Env var | Default |
|---|---|
| `TICK_SECONDS` | `1.0` |
| `GEMMA_BASE_URL` | `http://localhost:11434` |
| `GEMMA_MODEL` | `gemma4:e4b-it-q4_K_M` |

Calls run in their own asyncio task, so a slow model never holds up the tick
loop. They use structured JSON output with thinking off: on an M5 with 16 GB a
headline takes about 1.5 s, and the first call after loading takes about 5 s, so
the worker warms the model up at startup. Each call is retried once. A headline
Gemma hasn't written within 5 s falls back to a template, so the game works
without Ollama. Tests use a fake client and don't need Ollama.

Pricing follows `docs/main_sequence_pricing_data.md`:
`price = 100 × (log10(L/L☉) + 5)`, with 1000 shares per star.

**Trading pressure** sits on top of that as a temporary multiplier:
`price = 100 × (log10(L/L☉) + 5) × impact`. Each trade moves `impact` by 1% per
10k traded (up for buys, down for sells), within 0.85 to 1.15, and it eases 10%
of the way back to 1 every tick. So a herd buying on a rumour really moves the
price, and it drifts back once the buying stops. A trade fills at the price
after its own impact, so an instant buy-then-sell always loses a little. The
constants are in `app/config.py`.

## Lifecycle

Each star's luminosity is generated within bounds: at startup from its spectral
type's main-sequence range (Table 1 of the pricing doc), and again whenever it
enters a new stage. After a stage change, L eases towards the new value through
the twinkle's mean reversion. A black hole has no light: its L and price sit at
0 and don't move. The spectral type
decides the path (sections 2 and 4 of the pricing doc); mass is display only:

```text
O        main_sequence → blue_hypergiant → supernova → black_hole
B        main_sequence → red_hypergiant → supernova → black_hole
A, F     main_sequence → blue_giant → supernova → neutron_star
G, K, M  main_sequence → red_giant → white_dwarf
```

Giant and hypergiant bounds come from Table 4 of the pricing doc, except that a
hypergiant's lower bound is never below the top of its main-sequence range, so
becoming one is always a rally. White dwarf and neutron star bounds come from
Table 5 (prices 0 to 700 and 0 to 600).

Section 4's price moves are scripted as straight lines in price, with L set
from the price, so trading pressure, history and the WebSocket work as usual.
The twinkle pauses while a script runs:

- **Supernova (O, B, A, F):** the price jumps to 3× its value just before the
  supernova, fades slowly to 2.7× over 27–33 s, then drops over 8 s to the
  remnant's price (0 for a black hole). The star stays a tradeable supernova
  until the drop ends, so players can sell on the way down.
- **White dwarf (G, K, M):** the price declines from the giant's value to the
  white dwarf's over 45 s.

The constants are in `app/lifecycle.py`. A supernova's L is huge (around
10²⁸ L☉ for a 3300 price). Stage
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
| POST | `/director/force_stage` | `{asset_id}` | `Asset` after moving it to its next stage |

```text
Asset     { id, name, kind: "star", stage, spectral_type, mass, temperature, L,
            price, shares_total, shares_available }
stage     "main_sequence" | "red_giant" | "blue_giant" | "red_hypergiant"
          | "blue_hypergiant" | "supernova" | "white_dwarf" | "neutron_star"
          | "black_hole"
Portfolio { player_id, nickname, cash, holdings: {asset_id: qty}, net_worth }
```

Errors use FastAPI's `{"detail": ...}` body: 400 for a rejected trade (not
enough cash, shares or holdings, or the star is a black hole), 404 for an unknown player/asset, 422 for an
invalid body. Quantities may be fractional. A trade fills at the price after its
own impact, so it costs slightly more than `qty × price`: spending all your cash
at the shown price fails with "Not enough cash".

`/director/*` endpoints drive the game by hand for testing and the demo. They
have no auth. `force_stage` returns 400 if the star is already in its final
stage. For example:

```sh
curl -X POST localhost:8000/director/force_stage -H 'Content-Type: application/json' -d '{"asset_id": "kestrel"}'
```

**WebSocket `/ws`** (server → client):

```json
{"type": "tick", "t": 12, "assets": [{"id": "sol-nova", "stage": "main_sequence", "price": 500.4, "L": 1.002}]}
{"type": "leaderboard", "rows": [{"nickname": "zaki", "net_worth": 10012.5}]}
```

`tick` is sent every tick and `leaderboard` every 5 ticks. Load `/state` once on
start, then apply `tick` messages on top.

## Not built yet

Nebulae and protostars, random events, news feed, more director
endpoints, Gemma integration and persistence. State resets when the server
restarts.
