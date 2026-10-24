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
| `app/events.py` | Price-moving events: types, weights, effects and eligibility |
| `app/seed.py` | Starting stars (one main-sequence star per spectral type) |
| `app/spawn.py` | New stars: protostar forecasts, birth values and fallback names |
| `app/config.py` | Game constants and env vars |
| `app/ai/client.py` | Calls Gemma through Ollama's chat API with a JSON schema |
| `app/ai/prompts.py` | Prompts, reply schemas and template fallbacks |
| `app/ai/worker.py` | Background task that runs Gemma calls away from the tick loop |

## Gemma

Gemma writes the news text and names new stars. It never sets prices or
balances. The worker keeps a few Gemma names ready in `Market.name_pool`, so a
spawn never waits for the model; `FALLBACK_NAMES` in `app/spawn.py` covers it
when Gemma is down. It runs locally
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
without Ollama. Headlines are written one at a time, so if several stars change
stage at once, the later ones may get templates. Tests use a fake client and don't need Ollama.

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
O        protostar → main_sequence → blue_hypergiant → supernova → black_hole
B        protostar → main_sequence → red_hypergiant → supernova → black_hole
A, F     protostar → main_sequence → blue_giant → supernova → neutron_star
G, K, M  protostar → main_sequence → red_giant → white_dwarf
```

**New stars** spawn as protostars on average every 50 s while fewer than 20
stars are alive (remnants don't count), with every spectral type equally
likely. The 7 seeded stars start on the main sequence. A protostar lasts
60–90 s. Its true type and main-sequence brightness are rolled when it spawns
and kept on the server (section 3 of the pricing doc). Its price is a forecast
of its main-sequence price, which wobbles and narrows towards ignition but is
20–40% off 30% of the time. At ignition the price jumps to the true value.
Players can trade protostars at the forecast price. The API shows a protostar's
*projected* spectral type, mass and temperature, so it can change, and the true
values appear at ignition. Protostars get news when they're discovered,
halfway to ignition and at ignition.

**Black holes** are delisted 60 s after forming: they leave `/state` and tick
messages, and their shares are written off.

Typical lives, from the main sequence: O 4.5–7.5 min, B 5.5–8.5 min, A and F
10.5–15.5 min, G, K and M 12–18 min. Spawned stars add 1–1.5 min as protostars.

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

## Events

Events follow section 5 of the pricing doc. Code rolls every number; Gemma only
writes the news. An event moves a star's price through a named multiplier that
eases towards a target (`m += (target − m) × (1 − exp(−dt / tau))`), so:

```text
price = 100 × (log10(L/L☉) + 5) × event multipliers × trading pressure
```

Effects survive stage changes. The scheduler starts an event at random, on
average every 20 s (`EVENT_MEAN_GAP_SECONDS`; the doc says 30 s), picking a type
by weight among those with an eligible star:

| Type | Weight | Targets | Effect |
|---|---|---|---|
| `meteor_strike` | 25 | any star except a black hole | price −3% to −9%, recovers over ~30 s |
| `stellar_flare` | 20 | main-sequence stars | price +12% to +28%, fades over ~20 s |
| `coronal_collapse` | 10 | red giants and red hypergiants | 30–60% of the stage's remaining time removed |

Each event publishes an `event` news item. The other events in the doc aren't
built yet; magnetar starquakes and black hole feeding are left out on purpose.

## API

The frontend dev server proxies `/api/*` here, so `/join` is `/api/join` from
the browser.

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/join` | `{nickname}` | `{player_id}` |
| GET | `/state` | | `{t, assets: Asset[], leaderboard: {nickname, net_worth}[], news: NewsItem[]}` |
| GET | `/assets/{id}/history` | | `{t, price}[]` (last 600 ticks) |
| GET | `/portfolio/{player_id}` | | `Portfolio` |
| POST | `/trade` | `{player_id, asset_id, side: "buy"\|"sell", qty}` | `Portfolio` |
| POST | `/director/force_stage` | `{asset_id}` | `Asset` after moving it to its next stage |
| POST | `/director/fire_event` | `{type, asset_id}` | `Asset` after starting the event on it |
| POST | `/director/spawn_star` | `{spectral_type?}` | `Asset` of a new protostar (ignores the star limit) |

```text
Asset     { id, name, kind: "star", stage, spectral_type, mass, temperature, L,
            price, shares_total, shares_available }
stage     "protostar" | "main_sequence" | "red_giant" | "blue_giant" | "red_hypergiant"
          | "blue_hypergiant" | "supernova" | "white_dwarf" | "neutron_star"
          | "black_hole"
Portfolio { player_id, nickname, cash, holdings: {asset_id: qty}, net_worth }
NewsItem  { id, t, kind: "lifecycle" | "event" | "rumour" | "system", headline,
            body, asset_ids: string[], source, side: "human" | "alien" }
```

`news` in `/state` holds the last 50 items, oldest first. `t` is the tick the
news is about, which can be a tick or two before it was published. `lifecycle`
items cover stage changes (including forced ones) and `event` items cover
events; `rumour` and `system` aren't used yet.

Each item is reported by one of five outlets, picked at random (section 5.0.5 of
the pricing doc), and Gemma writes in its voice. `source` is the outlet's name:

| `source` | `side` | Voice |
|---|---|---|
| Galactic Financial Times | human | measured, market-focused |
| StarWire | human | sensational tabloid |
| Orbital Observatory Bulletin | human | cautious, scientific |
| Zr'kth Construction Authority | alien | imperial propaganda |
| Free Xeno Press | alien | sceptical dissident press |

Outlets spin the facts but never change what happened or which way a price is
moving.

Errors use FastAPI's `{"detail": ...}` body: 400 for a rejected trade (not
enough cash, shares or holdings, or the star is a black hole), 404 for an unknown player/asset, 422 for an
invalid body. Quantities may be fractional. A trade fills at the price after its
own impact, so it costs slightly more than `qty × price`: spending all your cash
at the shown price fails with "Not enough cash".

`/director/*` endpoints drive the game by hand for testing and the demo. They
have no auth. `force_stage` returns 400 if the star is already in its final
stage, and `fire_event` returns 400 if the event can't happen to that star (see
Events). For example:

```sh
curl -X POST localhost:8000/director/force_stage -H 'Content-Type: application/json' -d '{"asset_id": "kestrel"}'
```

**WebSocket `/ws`** (server → client):

```json
{"type": "tick", "t": 12, "assets": [{"id": "sol-nova", "stage": "main_sequence", "price": 500.4, "L": 1.002}]}
{"type": "leaderboard", "rows": [{"nickname": "zaki", "net_worth": 10012.5}]}
{"type": "news", "item": {"id": "…", "t": 41, "kind": "lifecycle", "headline": "Kestrel goes supernova", "body": "…", "asset_ids": ["kestrel"], "source": "StarWire", "side": "human"}}
{"type": "listed", "asset": {"id": "fathom", "stage": "protostar", "…": "a full Asset"}}
{"type": "delisted", "asset_id": "kestrel"}
```

`listed` arrives when a star spawns, before it appears in `tick` messages.
`delisted` arrives when a black hole leaves the market.

`tick` is sent every tick and `leaderboard` every 5 ticks. `news` is sent when
an item is published, usually about 1.5 s after the stage change (Gemma's
writing time), and at most 5 s after it. Load `/state` once on start, then apply
messages on top.

## Not built yet

Nebulae, the major events and rumours in section 5 of the pricing doc, a game
end and persistence. State resets when the server
restarts.
