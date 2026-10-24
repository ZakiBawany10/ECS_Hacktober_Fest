# Star Market — Project Spec (for scaffolding)

> A live, multiplayer stock market where the assets are stars. Prices come from each star's **luminosity and size**. Stars age through a real stellar lifecycle, random cosmic events hit them, and new **dust clouds (nebulae)** appear with hidden outcomes. **Gemma 4** generates events, headlines and nebula clues. Deterministic code owns all prices, trades and balances.

Hackathon context: theme "Fusion", main prize = best use of open-weight AI (Gemma 4), secondary = spooky. ~6 hours, 3 people. Judges are CS/engineering academics.

---

## 1. Core loop

1. Players open the web app (desktop or phone), enter a nickname and get **10,000 credits**.
2. The universe runs **live** on a server clock. No turns, no "advance year" button.
3. Every tick (~1s) every star's price updates from its physical stats plus small noise.
4. Stars **age through lifecycle stages** on their own (massive stars age fast, small ones barely change).
5. **Random events** fire every ~20–40s (meteor strikes, flares, alien Dyson spheres…) and change stars' luminosity/size.
6. **Nebulae** (dust clouds) spawn when a slot is free. Their outcome is hidden. Gemma drip-feeds ambiguous clues. On resolution they become a star (or vanish).
7. A **live news feed** carries every event, lifecycle change and clue. Reading the news is the edge.
8. **Live leaderboard** by net worth.

**Max 20 listed assets** at any time, nebulae included. Demo target: ~12 stars + 2–3 nebulae.

---

## 2. Tech stack

| Layer | Choice |
|---|---|
| Frontend | React + Vite + TypeScript, Zustand for state |
| Star map | HTML canvas (2D, glow effects) — optional upgrade to react-three-fiber |
| Charts | `lightweight-charts` (TradingView) |
| Backend | Python 3.11+, FastAPI, native WebSockets, asyncio tick loop |
| Storage | SQLite (via `sqlite3` or SQLModel); in-memory state is authoritative, DB is persistence/history |
| AI | Gemma 4 through an OpenAI-compatible endpoint (Ollama / llama.cpp server / hosted). Configured by env vars |
| Deploy | Single machine on the venue network; frontend served by Vite dev server or as static build from FastAPI |

Env vars: `GEMMA_BASE_URL`, `GEMMA_MODEL`, `TICK_SECONDS` (default 1.0), `DIRECTOR_KEY`.

---

## 3. File structure

```
star-market/
├── README.md
├── docs/
│   ├── SPEC.md                    # this file
│   └── lifecycle.png              # stellar lifecycle diagram (reference)
├── backend/
│   ├── requirements.txt           # fastapi, uvicorn[standard], pydantic, httpx, sqlmodel
│   ├── app/
│   │   ├── main.py                # FastAPI app, startup: load seed, start tick loop + AI worker
│   │   ├── config.py              # env vars, game constants
│   │   ├── models.py              # Pydantic models: Asset, Player, Trade, NewsItem, EventProposal, WS messages
│   │   ├── db.py                  # SQLite setup, persistence helpers
│   │   ├── state.py               # in-memory GameState singleton (assets, players, clock, queues)
│   │   ├── sim/
│   │   │   ├── tick_loop.py       # main loop: age stars, noise, apply shocks, fire events, broadcast
│   │   │   ├── lifecycle.py       # stage state machine + stage stat ranges + durations
│   │   │   ├── pricing.py         # price formula, noise, player price impact
│   │   │   ├── events.py          # event catalogue, bounds, apply/decay shocks
│   │   │   ├── nebula.py          # spawn, hidden outcome roll, clue schedule, resolution
│   │   │   └── market.py          # buy/sell, portfolios, net worth, leaderboard, delisting conversions
│   │   ├── ai/
│   │   │   ├── client.py          # Gemma HTTP client (JSON mode, timeout, retry once)
│   │   │   ├── worker.py          # async worker keeping event/clue queues filled
│   │   │   ├── validate.py        # schema + bounds validation, clamping, fallbacks
│   │   │   ├── prompts/
│   │   │   │   ├── universe.txt   # star names + lore for seed data
│   │   │   │   ├── event.txt      # choose + narrate next event
│   │   │   │   ├── clue.txt       # nebula clues given hidden outcome
│   │   │   │   └── headline.txt   # lifecycle stage-change headlines
│   │   │   └── fallbacks.json     # pre-written events/clues/headlines if Gemma fails
│   │   ├── api/
│   │   │   ├── routes_player.py   # POST /join, GET /portfolio/{player_id}
│   │   │   ├── routes_market.py   # POST /trade, GET /state, GET /assets/{id}/history
│   │   │   ├── routes_director.py # pause, speed, fire event, force stage, spawn nebula
│   │   │   └── ws.py              # /ws connection manager + broadcast
│   │   └── data/
│   │       └── seed_universe.json # starting stars (some deliberately mid/late-life)
│   └── tests/
│       ├── test_pricing.py
│       ├── test_lifecycle.py
│       ├── test_market.py
│       └── test_validate.py
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx                # layout: map | asset panel | news feed | leaderboard
        ├── types.ts               # mirror of backend models.py (keep in sync!)
        ├── api/
        │   ├── ws.ts              # WebSocket client, reconnect, dispatch to store
        │   └── rest.ts            # join, trade, state, history
        ├── state/
        │   └── store.ts           # Zustand: assets, prices, news, player, leaderboard
        ├── components/
        │   ├── JoinScreen.tsx     # nickname entry (+ QR code on host screen)
        │   ├── StarMap.tsx        # canvas; colour = stage, size = R, glow = L, flash on events
        │   ├── AssetPanel.tsx     # selected asset: stage, L, R, mass class, lifecycle position
        │   ├── PriceChart.tsx     # lightweight-charts live line/candles
        │   ├── TradeTicket.tsx    # buy/sell qty
        │   ├── NewsFeed.tsx       # scrolling live headlines, colour-coded by kind
        │   ├── Portfolio.tsx      # holdings, cash, P&L
        │   ├── Leaderboard.tsx
        │   └── DirectorPanel.tsx  # hidden route /director?key=...
        └── styles/
            └── theme.css          # dark space theme
```

---

## 4. Stellar lifecycle (state machine)

Based on the team's lifecycle diagram. Every star has a **mass class** fixed at birth, and that decides its path:

```
NEBULA ──► PROTOSTAR ──┬─► BLUE_MAIN_SEQ ─► RED_SUPERGIANT ─► SUPERNOVA ─┬─► NEUTRON_STAR
                       │     (8–20+ M☉)                                    └─► BLACK_HOLE   (>20–25 M☉)
                       ├─► YELLOW_DWARF ─► RED_GIANT ─► PLANETARY_NEBULA ─► WHITE_DWARF ─► BLACK_DWARF*
                       │     (~1 M☉)
                       ├─► RED_DWARF ─► RED_GIANT ─► PLANETARY_NEBULA ─► WHITE_DWARF ─► BLACK_DWARF*
                       │     (0.08–0.5 M☉)
                       ├─► BROWN_DWARF   (<0.08 M☉, terminal)
                       └─► DISSIPATED    (nebula failed to form a star, worthless)
```

\* Black dwarf is theoretical (the universe is too young). In-game it is the **delisting** state: a white dwarf eventually "fades out", its shares go to 0 and its slot frees up.

### Stage table (game units)

`L` = luminosity on a game scale (~1–1000), `R` = size on a game scale (~0.5–100). Durations are **real-time seconds at 1× speed** (compressed so the interesting stuff happens in a ~20 min session). Example prices use `BASE = 4`.

| Stage | L range | R | Duration (s) | Stage premium | ~Price | Asset "personality" |
|---|---|---|---|---|---|---|
| NEBULA | — | — | 120–180 | — | IPO 50, clue-driven | Venture bet |
| PROTOSTAR | 8–12 | 8 | 30–45 | 1 | ~37 | Uncertain |
| BROWN_DWARF | 1–3 | 3 | ∞ | 1 | ~9 | Penny stock |
| RED_DWARF | 8–12 | 4 | ∞ (never evolves in-session) | 1 | ~28 | **Bond**: stable, low vol |
| YELLOW_DWARF | 40–60 | 10 | 600–900 | 1 | ~105 | **Blue chip** |
| BLUE_MAIN_SEQ | 450–650 | 25 | 180–300 | 1 | ~640 | **Growth**: expensive, dies young |
| RED_GIANT | 180–260 | 50 | 120–180 | 1 | ~490 | Late-life rally |
| RED_SUPERGIANT | 750–950 | 90 | 60–120 | 1 | ~1,385 | Bubble before the pop |
| SUPERNOVA | L × 20–50 | 120 | 10–15 | 1 | spikes to ~12,000 | **Sell into the spike** |
| PLANETARY_NEBULA | 100 → decays | 60 | 45–60 | 1 | ~330 falling | Slow fade |
| WHITE_DWARF | 3–8 | 1.5 | 120–240 | 1 | ~12 | Dead money |
| NEUTRON_STAR | 1–3 | 0.5 | ∞ | 20 (pulsar) | ~90 | Rare remnant |
| BLACK_HOLE | 0 | — | ∞ | — | fixed 25 | **Hazard** (see events) |
| BLACK_DWARF / DISSIPATED | — | — | — | — | 0, delisted | Worthless |

Rules:
- Stage transitions are **automatic** when `stage_elapsed >= stage_duration`. Durations are rolled within the range at stage entry.
- On transition, L and R **ease** to the new stage's values over ~10 ticks (no instant jumps), except SUPERNOVA, which spikes over 2–3 ticks.
- Supernova → NEUTRON_STAR or BLACK_HOLE decided by mass (`mass >= 22` → black hole).
- **Delisting conversions:** SUPERNOVA → remnant keeps the same asset id, so shares convert 1:1 automatically. BLACK_DWARF and DISSIPATED → shares go to 0 and the asset leaves the market, freeing a slot.
- Seed the universe with some stars already mid/late-life (e.g. one RED_SUPERGIANT ~60s from collapse, one RED_GIANT) so the lifecycle plays out during the demo.

---

## 5. Pricing

```
price = BASE × L^0.6 × R^0.4 × stage_premium × shock_multiplier × impact_multiplier
```

- `BASE = 4`. Exponents are tunable in `config.py`.
- **Twinkle noise** each tick: `L *= exp(N(0, 0.002))`, mean-reverting toward the stage's target L.
- **Event shocks** modify L and/or R (not price) and are applied gradually over `ramp_ticks`. Temporary shocks decay back over `decay_ticks`.
- **Player price impact (optional):** each trade nudges `impact_multiplier` by `±0.001 × qty_value / 1000`, decaying back to 1.0 over ~20 ticks.
- BLACK_HOLE price is fixed (no luminosity). NEBULA price is set by `nebula.py` (section 7).
- Record price history per tick (downsample to every 5 ticks for the DB).

---

## 6. Random events

Code decides **when** (Poisson process, mean gap 30s at 1× speed). Gemma decides **what** and **to whom** from the allowed catalogue, given current state + recent history, and writes the narrative. `validate.py` clamps everything to these bounds.

| type | Valid targets (stages) | Stat effect (bounds) | Shape | Notes |
|---|---|---|---|---|
| `METEOR_STRIKE` | any star | L −5% to −15% | temporary, decays ~30s | Most common |
| `STELLAR_FLARE` | main seq, dwarfs | L +20% to +50% | temporary spike, decays ~20s | A pump |
| `DYSON_SPHERE` | yellow dwarf, blue main seq | L −10% per stage, 3–5 stages ~20s apart | **permanent** | Aliens capture the light, so observed L drops. Spooky |
| `CORONAL_COLLAPSE` | red giant, red supergiant | stage duration −30% to −60% | accelerates lifecycle | Pulls a supernova/planetary nebula forward |
| `MASS_ACCRETION` | main seq, protostar | R +5% to +15%, L +5% to +20% | permanent | Feeding off a nearby cloud |
| `BLACK_HOLE_DRIFT` | star near a BLACK_HOLE | 3 stages: warning → L −20% → consumed (delisted, shares → 0) | multi-stage arc | Only if a black hole exists. Big tension |
| `ALIEN_SIGNAL` | any (incl. remnants) | none, **or** small ±10% | news-only rumour | Can be false (`is_true` hidden). Spooky prize |
| `NEBULA_SEEDING` | nebula | shifts outcome clue tone only | — | Fired after a nearby supernova; can't change the rolled outcome |

Multi-stage events (Dyson sphere, black hole drift) are **arcs**: Gemma returns all stages up front with timings. The tick loop schedules them, so the news gives early warning before the big move.

Persistent memory: the event prompt gets each star's last ~5 events and current stage, and is told to prefer follow-ups (e.g. a star already hit by meteors, or one that's late-life).

---

## 7. Nebulae (dust clouds = mystery IPOs)

- **Spawn** when listed assets < 20 (check every ~30s, max 3 live nebulae). Also spawn 1–2 shortly after any supernova ("enriched gas").
- **Hidden outcome rolled at creation** (server-side only, never sent to clients):

| Outcome | Probability | Resolves to | ~Price |
|---|---|---|---|
| DISSIPATED | 40% | delisted | 0 |
| BROWN_DWARF | 20% | brown dwarf | ~9 |
| RED_DWARF | 22% | red dwarf | ~28 |
| YELLOW_DWARF | 13% | yellow dwarf | ~105 |
| BLUE_MAIN_SEQ | 5% | blue main seq | ~640 |

  IPO price 50 → expected value ~53.5 (~1.07×): slightly positive, very high variance.
- **Clues:** 3–4 clues over the nebula's life, written by Gemma **with the true outcome in the prompt**. ~70% of clues point the right way and ~30% mislead. Each clue carries a hidden `signal` in [-1, 1].
- **Nebula price** = `50 × (1 + 0.15 × Σ signals)` + noise, so the market reacts to the clues.
- **Resolution:** non-dissipated outcomes go NEBULA → PROTOSTAR (same asset id, shares carry over), then into the rolled stage. The universe visibly grows.

---

## 8. Gemma 4 roles

| Role | When | Input | Output (JSON) |
|---|---|---|---|
| Universe generation | Pre-hackathon / startup | count, mass classes | names, short lore per star (cache into `seed_universe.json`) |
| Event engine | Background worker, keeps queue 2–3 deep | universe snapshot + recent events + catalogue | `EventProposal` |
| Nebula clue writer | On nebula spawn | true outcome, nebula name, clue count | list of `{text, signal, delay_s}` |
| Headline writer | Stage transitions | star, old→new stage, holders' context | `{headline, body}` |
| Analyst (stretch) | Player asks "why did X move?" | asset history + events from DB | short answer |

**Gemma is never on the tick loop's critical path.** The worker pre-generates into queues. If a queue is empty or output fails validation, use `fallbacks.json`.

### EventProposal schema

```json
{
  "type": "DYSON_SPHERE",
  "targets": ["sol-7"],
  "severity": 0.6,
  "is_true": true,
  "stages": [
    {"t_plus_s": 0,  "headline": "Unusual structures detected orbiting Sol-7", "body": "...", "effects": {"L_pct": -0.10}},
    {"t_plus_s": 20, "headline": "Sol-7 dimming accelerates", "body": "...", "effects": {"L_pct": -0.10}},
    {"t_plus_s": 40, "headline": "CONFIRMED: Sol-7 is being enclosed", "body": "...", "effects": {"L_pct": -0.12}}
  ],
  "reasoning": "Sol-7 is a stable yellow dwarf with high luminosity; prior flare drew attention..."
}
```

Validation (`validate.py`): `type` in catalogue; targets exist, are listed and are valid stages for the type; effects clamped to the catalogue bounds; ≤5 stages; headline ≤ 90 chars. Show `reasoning` in the UI's event detail; it's good for judges.

---

## 9. Data models (backend `models.py` ↔ frontend `types.ts`)

```text
Asset        { id, name, kind: "star"|"nebula"|"remnant", stage, mass, L, R,
               stage_started_at, stage_duration, price, listed: bool,
               flags: { dyson_progress?, hazard?, pulsar? }, lore,
               x, y  # map position, fixed at spawn
               # server-only: hidden_outcome, clue_signals }
Player       { id, nickname, cash, holdings: {asset_id: qty}, joined_at }
Trade        { id, player_id, asset_id, side: "buy"|"sell", qty, price, t }
NewsItem     { id, t, kind: "event"|"lifecycle"|"clue"|"rumour"|"system",
               headline, body, asset_ids, severity }
PricePoint   { asset_id, t, price }
```

Trading rules: long-only (no shorting), fractional quantities allowed, fill at the current server price at receipt, cash can't go negative. Net worth = cash + Σ qty × price.

---

## 10. API

**REST**
- `POST /join {nickname}` → `{player_id}`
- `GET /state` → full snapshot (assets, recent news, leaderboard, sim clock)
- `GET /assets/{id}/history` → price points
- `POST /trade {player_id, asset_id, side, qty}` → updated portfolio or error
- `GET /portfolio/{player_id}`
- Director (require `DIRECTOR_KEY`): `POST /director/pause`, `/director/speed {x}`, `/director/fire_event {type, target}`, `/director/force_stage {asset_id, stage}`, `/director/spawn_nebula {outcome?}`

**WebSocket `/ws`** (server → client)
```json
{"type": "tick", "t": 1234, "assets": [{"id": "sol-7", "price": 104.2, "L": 51.3, "R": 10, "stage": "YELLOW_DWARF"}]}
{"type": "news", "item": { ...NewsItem }}
{"type": "asset_listed", "asset": { ...Asset }}
{"type": "asset_delisted", "asset_id": "neb-3", "reason": "DISSIPATED"}
{"type": "stage_change", "asset_id": "betel-2", "from": "RED_SUPERGIANT", "to": "SUPERNOVA"}
{"type": "leaderboard", "rows": [{"nickname": "zaki", "net_worth": 12450.3}]}
```
Leaderboard broadcast every 5 ticks; tick every tick.

---

## 11. Tick loop (pseudocode)

```python
async def tick_loop():
    while True:
        if not state.paused:
            dt = TICK_SECONDS * state.speed
            for a in state.listed_assets():
                lifecycle.advance(a, dt)          # may emit stage_change + queue headline
                events.apply_active_shocks(a)     # ramp/decay
                pricing.twinkle(a)
                a.price = pricing.compute(a)
            events.maybe_fire_next(state)         # Poisson timer -> pop from AI queue or fallback
            events.run_scheduled_arc_stages(state)
            nebula.update(state)                  # clues, price, resolution, spawning
            market.decay_price_impact(state)
            await ws.broadcast_tick(state)
            if state.tick % 5 == 0:
                await ws.broadcast_leaderboard(state); db.save_history(state)
        await asyncio.sleep(TICK_SECONDS)
```

---

## 12. Frontend layout

```
┌──────────────────────────────┬──────────────────────┐
│                              │  ASSET PANEL         │
│         STAR MAP             │  stage · L · R · mass│
│  (canvas: colour = stage,    │  lifecycle position  │
│   size = R, glow = L,        │  PRICE CHART         │
│   flash/ripple on events)    │  TRADE TICKET        │
├──────────────────────────────┼──────────────────────┤
│  NEWS FEED (live, scrolling) │  PORTFOLIO │ LEADERBOARD │
└──────────────────────────────┴──────────────────────┘
```
Mobile: single column (map → selected asset → trade → news). Stage colours: blue/yellow/red per diagram, purple haze for nebulae, white for white dwarfs, black ring with accretion glow for black holes.

---

## 13. Team split

- **Frontend:** `frontend/` — map, chart, trade ticket, news feed, leaderboard, director panel. Build against a mock WS stream first.
- **Backend / sim:** `backend/app/sim`, `api`, `state.py`, `db.py` — tick loop, lifecycle, pricing, trading, WS broadcast, director endpoints.
- **AI:** `backend/app/ai` — Gemma client, prompts, worker queues, validation, fallbacks, seed universe generation.

**First 30 minutes:** agree on `models.py`/`types.ts`, the WS message shapes (section 10) and the EventProposal schema (section 8). Then everyone builds in parallel against mocks.

---

## 14. Build order (≈6h)

| Time | Milestone |
|---|---|
| 0:00–0:30 | Schemas agreed, repo scaffolded, Gemma endpoint answering a test prompt |
| 0:30–2:00 | Tick loop + pricing + lifecycle with seed data; WS broadcasting; frontend renders map + live prices from mock then real WS |
| 2:00–3:00 | Join + trading + portfolio + leaderboard; AI worker producing validated events into the queue |
| 3:00–4:00 | Event catalogue wired end to end; news feed; supernova → remnant conversion |
| 4:00–4:45 | Nebulae (spawn, hidden roll, clues, resolution) |
| 4:45–5:30 | Director panel, fallbacks, polish visuals (event flashes, supernova effect) |
| 5:30–6:00 | Rehearse demo, freeze code |

**Cut first if behind:** player price impact → black hole drift → analyst chat → 3D map.

---

## 15. Demo script (~3 min)

1. QR code on screen, judges join on phones, everyone gets 10k credits.
2. Point out asset personalities: red dwarf = bond, yellow dwarf = blue chip, blue giant = growth, nebula = venture.
3. A Dyson sphere arc starts on a yellow dwarf: early rumour, then dimming, then confirmation. Show the price bleed and Gemma's reasoning.
4. The seeded red supergiant goes **supernova**: price spikes ~8×, then the asset collapses into a neutron star/black hole. Show who sold into the spike on the leaderboard.
5. The supernova seeds a new nebula. Show clues arriving, then the reveal.
6. Close on the architecture: Gemma proposes, code validates and bounds, physics drives price, history feeds the next event.

Director panel stays open on a laptop to force the hero moments on cue.

---

## 16. Non-goals

- No real astrophysics simulation and no live astronomical data.
- No auth beyond nickname; no persistence across server restarts required.
- No shorting, options or order books.
- All values are fictional game mechanics.
