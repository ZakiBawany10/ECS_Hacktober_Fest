# Hackathon

October 24, 2026

## 1 Main Sequence.

| Spectral type | $T_{\mathrm{eff}}$ (K) | $L/L_\odot$ | $M/M_\odot$ |
|:--------------|----------------------:|------------:|------------:|
| O | 32,000 to 45,000 | $5 \times 10^4$ to $7 \times 10^5$ | 19 to 60 |
| B | 10,000 to 31,000 | 60 to $4.5 \times 10^4$ | 2.7 to 18 |
| A | 7,400 to 9,700 | 8 to 40 | 1.75 to 2.2 |
| F | 6,000 to 7,200 | 1.5 to 7.2 | 1.1 to 1.6 |
| G | 5,400 to 5,900 | 0.55 to 1.35 | 0.90 to 1.06 |
| K | 3,900 to 5,300 | 0.08 to 0.46 | 0.59 to 0.88 |
| M | 2,400 to 3,900 | $3 \times 10^{-4}$ to 0.07 | 0.08 to 0.57 |

**Table 1:** Representative effective temperatures, bolometric luminosities and masses of main-sequence stars (luminosity class V), using rounded dwarf calibrations [?]. The O-star range covers O3-O9.5.

we will take logs of luminosity to get a linear scale in base 10

**Table 2: Amended Luminosity**

| Spectral type | $T_{\mathrm{eff}}$ (K) | $\log_{10}(L/L_\odot)$ | $M/M_\odot$ |
|:--------------|----------------------:|----------------------:|------------:|
| O | 32,000 to 45,000 | 4.70 to 5.85 | 19 to 60 |
| B | 10,000 to 31,000 | 1.78 to 4.65 | 2.7 to 18 |
| A | 7,400 to 9,700 | 0.90 to 1.60 | 1.75 to 2.2 |
| F | 6,000 to 7,200 | 0.18 to 0.86 | 1.1 to 1.6 |
| G | 5,400 to 5,900 | $-0.26$ to 0.13 | 0.90 to 1.06 |
| K | 3,900 to 5,300 | $-1.10$ to $-0.337$ | 0.59 to 0.88 |
| M | 2,400 to 3,900 | $-3.52$ to $-1.15$ | 0.08 to 0.57 |

**Table 3: Amended Luminosity**

To scale this to have all positive relative values, add 5 to the amended luminosities. This means that the smallest M stars have a relative value of 1.48.

$$
P = 100 \times \left(5 + \log_{10}(L/L_\odot)\right)
\tag{1}
$$

**Figure 1:** $P$ = Price of share, $L$ = luminosity $L_\odot$ = solar luminosity

The price per share will now be:

$100 \times \left(5 + \log_{10}\left(\frac{L}{L_\odot}\right)\right)$ !!

I will also suggest that each star has the same number of shares associated to it. However, if scaling by mass makes more sense, then i may suggest we change that.

For now, each star has 1000 shares attached to it.

## 2 exotics

the way i would like to add the next stages of life to the main sequence is to assign types of "Giant star" to the types of main sequence.

M,K,G, become red giants F,B become Blue Giants B become Red Hyper Giants O become Blue Hyper Giants

the values for our adjusted luminosities and therefore the price per share

| Stellar type | $T_{\mathrm{eff}}$ (K) | $\log_{10}(L/L_\odot)+5$ | $M_{\mathrm{init}}/M_\odot$ |
|:-------------|----------------------:|------------------------:|---------------------------:|
| Red giant | 3,000 to 5,000 | 6.00 to 9.00 | 0.8 to 8 |
| Blue giant | 10,000 to 45,000 | 7.00 to 11.00 | 3 to 70 |
| Red hypergiant | 3,000 to 4,000 | 10.00 to 10.70 | 20 to 40 |
| Blue hypergiant | 10,000 to 30,000 | 10.30 to 11.48 | 30 to 100 |

**Table 4:** Illustrative effective temperatures, shifted logarithmic bolometric luminosities and initial masses of giant and hypergiant stars. These overlapping ranges are representative rather than strict classification boundaries.

share price is of course 100 times $5 + \log_{10}(L/L_\odot)$ this stays

## 3 Proto star.

The way i would like this to work is that we will give the option to the user to "buy" into the star at the protostar stage. There will be news surrounding this in game. A protostar will have attached to it a constantly updating "predicted value" per share. The real value may very well be that value or it might deviate significantly depedning on market conditions or observational error.

## 4 Supernovae

I would like it that M,K and G type stars go from giant straight to its remnant phase, everything else will supernova.

Supernova will see a temporary $\times 3$ increase in price until a given point. after this given point in time the price should reasonably quickly decay to a value to illustrate the formation of a stellar remnant.

Type M, G, K become white dwarfs. Type F,A become neutron stars Type B and O become black holes

| Remnant type | $T_{\mathrm{eff}}$ (K) | $\log_{10}(L/L_\odot)+5$ | $M_{\mathrm{rem}}/M_\odot$ |
|:-------------|----------------------:|------------------------:|--------------------------:|
| White dwarf | 4,000 to 150,000 | 0.00 to 7.00 | 0.2 to 1.3 |
| Neutron star | $10^5$ to $3 \times 10^6$ | 0.00 to 6.00 | 1.1 to 2.3 |

**Table 5:** Illustrative surface temperatures, shifted logarithmic thermal bolometric luminosities and current masses of cooling stellar remnants. These age-dependent ranges exclude accretion-powered emission, non-thermal pulsar emission and magnetar activity.

Black holes have a Luminosity of 0 therefore their price should be 0 forever. After an initial supernova, the price should very slowly fall for about 30 seconds plus or minus 3 seconds. Then a sharp linear decrease tending towards the price of the Giants' associated remnant based on its type. This applies to all stars that experience supernova (F,A,B,O). For stars that don't (M, K, G), a reasonably slow linear decrease to the associated stellar remnant.


> Defines every price-moving event: how it works, how it moves the price, how long it lasts, and what the news feed says. Use alongside `STAR_MARKET_SPEC.md`; **this file replaces the event catalogue in section 6 of the spec.**
>
> All durations are **real-time seconds at 1× speed**. A standard game is **20 minutes** (`GAME_LENGTH_S = 1200`). All prices are fictional game mechanics.

## Summary

| # | Event | Duration | Typical price impact | How often | Hidden outcome |
|---|---|---|---|---|---|
| 5.1 | Dyson Sphere | up to ~300s | down to ~0% of baseline, or back to baseline | ≥1 per game, max 2 at once | Completes (20%) / abandoned (80%) |
| 5.2 | Star Merger | ~60s | both holders +20–26% | 1–2 per game | Merges (85%) / near miss (15%) |
| 5.3 | Remnant Supernova (white dwarf) | 120–240s build-up + 10s blast | up to ×4 build-up, ×15 spike, then 0 | when conditions met, max 1 at once | Detonates / stalls; destroyed / zombie star |
| 5.4 | Intelligent Life | long-running (minutes) | ×1.05 → ×1.20 → ×1.45 | ~1 per 3–4 min, max 3 civ stars | Advances / stagnates / dies out |
| 5.5 | Black Hole Feeding | 60–90s | target −24% then 0 or partial recovery; black hole up | needs a black hole; 90s cooldown | Full disruption (60%) / escape (40%) |
| 5.6 | Mysterious Dimming | 60–120s | dips of −6% to −14% | ~1 per 3 min, max 1 at once | Dust (85%) / early Dyson (15%) |
| 5.7 | Gamma-Ray Burst | instant (+20s aftershock) | kills life premiums in the beam; market-wide −5% | rare, tied to big supernovae | Beam direction |
| 5.8 | Mass Transfer | 90–150s | donor ≈ −25%, gainer ≈ +29% (pair trade) | ~1 per 3 min | Total amount + duration |
| 5.9 | Magnetar Starquake | ~40s | spike +30–80% (rarely +150%), settles slightly lower | each magnetar every 90–180s | Size of flare |
| 5.10 | Minor events | 20–30s | ±5–50% temporary | fill the gaps | — |

---

## 5.0 Event framework (applies to every event)

### 5.0.1 Scheduling
- A **scheduler** runs every ~30s (Poisson, mean gap 30s). It builds the list of events that are currently *eligible* (rules in each section), then picks one by weight:

  | Event | Weight |
  |---|---|
  | Meteor strike / stellar flare (5.10) | 25 / 20 |
  | Mysterious dimming | 10 |
  | Mass transfer | 10 |
  | Star merger | 8 |
  | Intelligent life (new emergence) | 8 |
  | Black hole feeding | 8 |
  | Dyson sphere | 4 (×5 if target has a level-3 civilisation) |

- **Self-triggered events** don't go through the scheduler: Remnant Supernova (5.3) starts when its conditions are met, GRB (5.7) fires from a qualifying supernova, and Magnetar Starquakes (5.9) run on each magnetar's own timer.
- **Caps:** max **4 major events** running at once across the universe; max **1 major event per asset** at a time. Intelligent life is a long-running *state*, not an event, so it doesn't count toward either cap.
- **Director panel** can force any event on any valid target, and force an outcome.

### 5.0.2 Hidden outcomes
Every event with an uncertain ending **rolls its outcome when it starts** and stores it server-side (never sent to clients). This keeps the game fair and lets Gemma write news that is consistent with what will actually happen.

### 5.0.3 How events move prices
Price formula (from the spec, extended):

```
price = BASE × L^0.6 × R^0.4 × stage_premium × civ_multiplier × Π(event_multipliers) × impact_multiplier
```

Events move price in one of two ways:
1. **Stat changes** (mass, L, R): permanent physical changes (mergers, mass transfer, stripping). The price follows the formula.
2. **Event multipliers**: named entries in `asset.multipliers` (e.g. `dyson`, `dimming`, `quake`), each with a `target` value. Every tick: `m += (target − m) × (1 − exp(−dt / tau))`, where `tau` is the easing time constant given in each section. When an event ends, its multiplier eases back to 1.0 and is removed.

Twinkle noise is always on, so charts never move in perfectly smooth curves.

### 5.0.4 Main-sequence stars: brightness and size from mass
Needed for mergers and mass transfer. **For main-sequence stars (red dwarf, yellow dwarf, blue main sequence), L and R come from mass, not from the stage table:**

```
L = 50 × M^1.2        R = 10 × M^0.6
```

| Mass (M☉) | L | R | Price |
|---|---|---|---|
| 0.3 (red dwarf) | 11.8 | 4.9 | ~33 |
| 1 (yellow dwarf) | 50 | 10 | ~105 |
| 3 (yellow dwarf) | 187 | 19.3 | ~302 |
| 8 (blue) | 606 | 34.8 | ~773 |
| 12 (blue) | 986 | 44.4 | ~1,141 |

Mass bands decide the lifecycle path: **brown dwarf < 0.08 ≤ red dwarf < 0.5 ≤ yellow dwarf < 8 ≤ blue main sequence**. The curve is continuous, so crossing a band never causes a price cliff. Post-main-sequence stages (giants, remnants) keep using the stage table.

### 5.0.5 News system
Every event pushes `NewsItem`s to the feed. Key moments are flagged `flash: true` and show as a pop-up banner.

**Division of labour:** code computes the *facts* (true progress, the number each source reports). Gemma only writes the *words*, given the facts, the source's persona and the hidden outcome.

**In-game sources:**

| Source | Side | Style | Bias rule |
|---|---|---|---|
| **Galactic Financial Times (GFT)** | Human | Measured, market-focused | Accurate, but reports one update late |
| **StarWire** | Human | Fast, sensational tabloid | First to report; exaggerates magnitudes by +5 to +15% |
| **Orbital Observatory Bulletin** | Human | Scientific, cautious | Accurate to ±3%; hedges ("data suggests…") |
| **Zr'kth Construction Authority** | Alien | Official alien state feed; propaganda | Overstates alien progress/success by +5 to +15% |
| **Free Xeno Press** | Alien | Dissident, sceptical | Understates progress by −5 to −10%; reports setbacks early |

**Accuracy limits (hard rules in `validate.py`):**
- Reported numbers may be off from the truth by **at most ±15 percentage points**.
- No source may claim a **terminal outcome** (completed, abandoned, destroyed, merged) that hasn't happened.
- Sources may *hint* at an upcoming outcome only where an event section says so.
- Bias is about tone and emphasis. Sources can disagree on degree but never on direction.

---

## 5.1 Dyson Sphere

An alien civilisation encloses a star in a megastructure that captures its light. To outside observers the star dims, so its price falls.

**Eligibility:** any listed star (not nebulae, remnants or black holes) with no other major event running. Stars with a level-3 civilisation (5.4) are 5× more likely to be picked.

**Frequency and caps:**
- Low chance per scheduler slot (weight 4).
- **At least 1 per game:** if no Dyson sphere has started by `0.4 × GAME_LENGTH_S` (minute 8), the next scheduler slot is forced to start one.
- **Max 2 at the same time.**

**Hidden outcome (rolled at start):**
- **Completed: 20%.**
- **Abandoned: 80%.** The stop point is rolled uniformly between 15% and 85% progress.

**Build timeline:** full build takes **300s**. Progress follows a front-loaded curve, fast at first and slowing as more gets built:

```
progress(t) = 1 − (1 − t / 300)²
dyson_multiplier target = 1 − 0.97 × progress      (tau = 3s)
```

| Time | Progress | Price vs baseline |
|---|---|---|
| 0s | 0% | 100% |
| 30s | 19% | 82% |
| 60s | 36% | 65% |
| 120s | 64% | 38% |
| 180s | 84% | 19% |
| 240s | 96% | 7% |
| 300s (complete) | 100% | **~3%** |

**Fake-out stalls:** in either outcome, progress can **pause 0–2 times for 15–30s**. A stall doesn't always mean abandonment, which keeps players guessing.

**Endings:**
- **Completed:** the multiplier settles at 0.03 permanently and the star is tagged `ENCLOSED`. The asset stays listed as near-dead money. Its lifecycle keeps ticking underneath: if the star later goes supernova or red giant, the sphere is destroyed and the multiplier returns to 1.0. That's a long-shot comeback.
- **Abandoned:** the multiplier target snaps back to 1.0 with `tau = 5s`, a **sharp rally** to the previous baseline within ~15s. "Previous baseline" means the price the star would have had without the sphere, so other movements during the build still count.

**News:**
- **Start:** flash. "Unidentified structures detected around [star]".
- **Updates every 20–30s** (about 10–15 over a full build), each from a random source with its bias applied to the reported % complete.
- **Stall:** reported by Free Xeno Press first ("construction crews idle"), and by the others one update later.
- **Hints:** if abandonment is coming within the next 30s, Free Xeno Press has a 50% chance of hinting at problems ("funding disputes", "workforce unrest").
- **Completed / abandoned:** flash.

---

## 5.2 Star Merger

Two stars in a tight orbit spiral together and merge into one bigger, brighter star. In real astronomy these become "blue stragglers": stars brighter and younger-looking than they should be.

**Eligibility:** two main-sequence stars (red, yellow or blue) that are either a seeded **binary pair** (`binary_partner` set in `seed_universe.json`) or within `MERGE_DISTANCE` (8% of map width) of each other. Neither may have another major event running. Seed **2–3 binary pairs** so mergers can actually happen.

**Frequency and caps:** weight 8, **max 1 merger at a time**, typically 1–2 per game.

**Hidden outcome:** **merge 85%**, **near miss 15%** (orbits stabilise and nothing merges).

**Timeline (~60s):**

| Phase | Time | What happens | Price effect |
|---|---|---|---|
| Orbital decay | 0–25s | Stars drawn together | `merger_hype` multiplier on both → 1.05 (tau 8s) |
| Contact binary | 25–50s | Shared envelope, unstable | Volatility ×3 (noise sigma ×3) on both |
| Merge | 50–60s | Flash on the map, assets combine | See below |

**Merged star:**
- Mass = M_A + M_B. Stage = the band of the new mass (it can cross into blue, which means a **shorter life** and a supernova later).
- L and R come from the mass curve (5.0.4), with a **permanent straggler boost: L × 1.5**.
- The lifecycle timer resets to a fresh main-sequence duration for the new band.
- The surviving asset keeps the **larger star's id**; Gemma gives it a new name. The smaller asset is removed (converted, not zeroed) and its slot frees up.

**Share conversion (by mass contribution):** a holder of `q` shares of star A receives `q × M_A / (M_A + M_B)` shares of the merged star.

| Example | Before | Merged price | Per old share | Change |
|---|---|---|---|---|
| Yellow 1 M☉ + yellow 1 M☉ | 105 each | ~261 | ~130 | **+24%** both |
| Red 0.3 M☉ + yellow 1 M☉ | 33 / 105 | ~172 | 40 / 133 | **+20% / +26%** |

**Near miss:** at 50s the hype multiplier eases to 0.97 (tau 10s), then back to 1.0 over 30s. It's a small give-back.

**News:** start flash ("[A] and [B] spiralling inward"); 2–3 updates on orbital period shrinking (StarWire overstates how close it is); outcome flash.

---

## 5.3 Remnant Supernova (white dwarf explodes)

A white dwarf pulls gas off a nearby companion until it hits about **1.4 solar masses** (the Chandrasekhar limit) and detonates in a Type Ia supernova. Normally this **leaves nothing behind**.

**White dwarf mass:** set when a star becomes a white dwarf: `wd_mass = min(1.35, 0.45 + 0.12 × progenitor_mass)`. So a 1 M☉ star leaves a 0.57 white dwarf, a 5 M☉ star leaves 1.05, and a 7.5 M☉ star leaves 1.35.

**Eligibility (self-triggered):** a white dwarf with `wd_mass ≥ 1.2` **and** a companion star within `ACCRETION_DISTANCE` (8% of map width). Starting it automatically creates a linked **Mass Transfer (5.8)** with the companion as donor. Max 1 at a time.

**Hidden outcome (rolled at start):**
- **Detonates: 75%.** The ignition threshold is rolled between 1.37 and 1.40, so it isn't exactly predictable.
- **Stalls: 25%.** The companion runs dry before the limit; transfer stops at a random mass between 1.25 and 1.36.
- If it detonates: **total destruction 80%**, or **zombie star 20%** (a real, weaker Type Iax explosion that leaves a battered survivor).

**Build-up (120–240s):** the white dwarf gains mass steadily from 1.2 towards the threshold. Infalling gas makes it glow brighter (accretion glow):

```
p = (wd_mass − 1.2) / (threshold − 1.2)
L_obs = L × (1 + 9 × p²)                → price up to ~×4 near the limit (~12 → ~49)
```

The UI shows a **mass meter**: "1.31 / ~1.4 M☉".

**Detonation:** L × 100 over 3 ticks, held for 10s, so the price spikes to **~×15 of the build-up level** (~12 base → ~780 at peak). Then:
- **Destroyed:** delisted, shares → 0, slot freed. Spawns 1–2 nebulae nearby.
- **Zombie star:** converts to stage `ZOMBIE_STAR` (L 2, R 0.8, fixed flicker), price ~5. Spooky headline. Shares carry over 1:1.

**Stall:** the glow fades over 30s (tau 10s) back to normal white dwarf levels. The companion keeps whatever mass it lost.

**News:** start ("[WD] feeding on [companion]"); mass readings every ~20s (Orbital Observatory accurate, StarWire overstates proximity to the limit); flash on detonation or stall.

---

## 5.4 Intelligent Life

Life emerges on planets around a star and grows into a civilisation. Markets price in the value of a living system. It runs as a **long-lived state** on the star (`civ_level` 0–3), not a one-off event.

**Eligibility for emergence:** red or yellow dwarfs that have been in their stage for ≥ 60s, `civ_level = 0`, no major event running. Blue stars are excluded because they live too briefly for life to develop.

**Frequency and caps:** emergence weight 8 (roughly one every 3–4 min); **max 3 civilisation stars** at once.

**Progression:**

| Level | Name | `civ_multiplier` | Next step |
|---|---|---|---|
| 1 | Microbial life detected | ×1.05 | After 60–90s: 60% advance, 40% stay |
| 2 | Intelligent life confirmed | ×1.20 | After 60–90s: 50% advance, 50% stay |
| 3 | Spacefaring civilisation | ×1.45 | Top level |

Multipliers ease to their new value with tau = 4s. A civilisation that "stays" gets one more roll after another 60–90s.

**Risks (checked every 60s):**
- **Self-destruction** (levels 2–3): 5% per check. Multiplier → 1.0 with tau 2s, a sharp drop. Spooky "signal goes silent" headline.
- **Dyson sphere** (level 3 only): the star is 5× more likely to be chosen for 5.1.
- **Flare sterilisation:** a stellar flare (5.10) on a red dwarf with a level 1–2 civilisation has a 30% chance of wiping it out.
- **Gamma-ray burst:** a hit from 5.7 wipes out a civilisation at any level.
- **Host star leaves main sequence** (becomes a red giant): 50% chance the civilisation **migrates** to the nearest eligible star within 15% of map width (that star gets the same level and multiplier), 50% it goes extinct.

**News:** discovery flash; level-ups as flashes; Zr'kth Construction Authority and Free Xeno Press cover alien civilisations from opposite sides (one boastful, one sceptical).

---

## 5.5 Black Hole Feeding

A black hole tears apart a nearby star (a "tidal disruption event"). The star loses value and the black hole gains it.

**Change to the spec:** a black hole's price is no longer fixed. It now grows with mass:

```
black_hole_mass at birth = 0.4 × progenitor_mass
black_hole_price = 25 × (black_hole_mass / 10)
feeding_radius = 10% of map width × sqrt(black_hole_mass / 10)
```

**Eligibility:** a listed black hole, plus the nearest listed star within its feeding radius (not a nebula or another black hole) with no major event running. **One feeding per black hole at a time, 90s cooldown** after each.

**Hidden outcome:** **full disruption 60%**, **escape 40%**.

**Timeline (60–90s):**

| Phase | Time | Target star | Black hole |
|---|---|---|---|
| Tidal warning | 0–20s | L wobbles ±8% (volatility ×3), `tidal` multiplier → 0.95 | +3% |
| Stripping | 20–50s | R −30%, L −20% (eased over the phase): **price ≈ −24%** | Gains 25% of target's mass; accretion glow on the map |
| Outcome | 50–60s | See below | See below |

- **Full disruption:** target delisted, shares → 0, slot freed. The black hole gains the remaining target mass, so its price jumps (accretion flare on the map).
- **Escape:** the target survives at its stripped size and recovers half its losses over 60s (tau 20s). The black hole keeps what it took.

**News:** flash at the warning ("[star] drifting towards [black hole]"); update when stripping starts; outcome flash. StarWire calls every warning a death sentence. Orbital Observatory gives honest odds language ("trajectory uncertain").

---

## 5.6 Mysterious Dimming

A star dims in strange, irregular dips. Is it dust, or something building? Based on the real case of Tabby's star (KIC 8462852), whose odd dimming was briefly speculated to be an alien megastructure.

**Eligibility:** any main-sequence star with no major event running. **Max 1 at a time**, weight 10.

**Hidden cause (rolled at start):**
- **Dust/comet swarm: 85%.** Ends after 60–120s.
- **Early Dyson sphere: 15%.** Converts into a full 5.1 Dyson Sphere when the dimming phase ends. This counts toward the Dyson cap; if the cap is full, the cause is forced to dust.

**Shape:** 3–5 dips over the event. Each dip is L −10% to −22% (price −6% to −14%) lasting 5–15s, then returns to near baseline in between.
- **Dust:** dip depths and timings are random.
- **Early Dyson:** dips get **progressively deeper and more regular**. Sharp players can spot this.

**Ending:** dust clears with price back to baseline within 15s; or a Dyson flash and the 5.1 timeline starts.

**News:** heavy on speculation, a good place for Gemma to write. StarWire leans "ALIEN MEGASTRUCTURE?", Orbital Observatory leans "likely dust". Neither is allowed to state the cause outright.

---

## 5.7 Gamma-Ray Burst

A collapsing massive star fires a narrow beam of gamma rays across space, sterilising anything alive in its path.

**Trigger (self-triggered):** when a star with **mass ≥ 25** goes supernova, there's a 50% chance it also emits a GRB. The director can force one. Expect 0–2 per game.

**Beam:** a cone **60° wide**, random direction, reaching 25% of map width from the source. The map draws the beam for ~3s.

**Effects (instant, over 2–3 ticks):**
- **Stars in the beam:** any civilisation is wiped out (`civ_multiplier` → 1.0 with tau 1s). Stars without life only get a temporary −5% (`radiation` multiplier, recovering over 20s).
- **Market-wide panic:** every other star −5% for 20s (tau 3s down, 10s recovery), **except red dwarfs, which get +5% (flight to safety)**. It's a systemic shock: the whole market drops at once.
- **Source supernova:** its spike is boosted ×1.5.

**News:** no warning (GRBs are sudden). Flash at impact naming the stars hit, then 1–2 follow-ups on the extinctions.

---

## 5.8 Mass Transfer

One star pulls gas off its neighbour. The donor shrinks and the gainer grows, so their prices move in **opposite directions**. Players can trade the pair: sell the donor, buy the gainer.

**Eligibility:** two stars within `TRANSFER_DISTANCE` (8% of map width), where:
- the **donor** is an expanded star (red giant or red supergiant) and the **gainer** is a neighbour; or
- the event was started by a Remnant Supernova (5.3), with the white dwarf as gainer.

Neither star may have another major event running (except a linked 5.3). Weight 10.

**Hidden outcome (rolled at start):** total mass transferred is 10–30% of the donor's mass, and duration is 90–150s.

**Rate:** mass moves evenly over the duration.
- **Donor:** loses mass; L and R shrink in proportion (e.g. 30% mass lost → L −30%, R −15%).
- **Gainer:** gains mass. If main-sequence, L and R follow the mass curve (5.0.4). If it crosses a mass band, its lifecycle path changes (e.g. into blue: bigger, but shorter-lived).

**Example:** a red giant gives 0.3 M☉ to a 1 M☉ yellow dwarf. The donor ends **~−25%**, the gainer ends **~+29%** (1 → 1.3 M☉).

**Ends** early if either star changes stage.

**News:** start ("[donor] spilling gas onto [gainer]"); updates every ~30s with the current transfer rate; end notice. GFT frames it as a pair trade.

---

## 5.9 Magnetar Starquake

A magnetar (a neutron star with an extreme magnetic field) cracks its crust and releases a giant flare. The price spikes, then settles slightly lower.

**Magnetars:** when a neutron star forms, it has a 40% chance of being a magnetar. The flag is hidden until its first quake.

**Pulsar spin-down:** all neutron stars' pulsar premium (×20 in the spec) **decays by 1% per minute**. They're a slow bleed between quakes, not free money.

**Frequency:** each magnetar quakes every **90–180s** (its own timer, outside the scheduler).

**Timeline (~40s):**

| Phase | Time | Price effect |
|---|---|---|
| Precursor (60% of quakes) | 10–20s before | No price move; news reports "X-ray bursts detected" |
| Flare | 2 ticks | **+30% to +80%** (10% chance of a giant flare: **+150%**) via `quake` multiplier |
| Settle | ~30s | Eases (tau 8s) to a new baseline **0–5% below** the pre-quake price |

**News:** precursor note when one happens; flash on the flare; StarWire overstates the flare's size.

---

## 5.10 Minor events (background)

Small, frequent events that keep the feed and the charts active between the big ones. These stay from spec section 6.

| Event | Targets | Effect | Duration |
|---|---|---|---|
| `METEOR_STRIKE` | any star | L −5% to −15% → price −3% to −9% | Recovers over ~30s |
| `STELLAR_FLARE` | main-sequence stars | L +20% to +50% → price +12% to +28% | Decays over ~20s; can sterilise life on red dwarfs (5.4) |
| `CORONAL_COLLAPSE` | red giant / supergiant | Stage duration −30% to −60% | Brings the next lifecycle stage forward |
| `ALIEN_SIGNAL` | any | None, or ±10% | News-only rumour; may be false (spooky) |
| `NEBULA_SEEDING` | nebula | Changes clue tone only | Fired after a nearby supernova |

**Removed from spec section 6:** `DYSON_SPHERE` (now 5.1), `MASS_ACCRETION` (now 5.8), `BLACK_HOLE_DRIFT` (now 5.5).

---

## Implementation notes for Codex

- `backend/app/sim/events/`: make this a package with one module per event (`dyson.py`, `merger.py`, `remnant_supernova.py`, `civ.py`, `black_hole.py`, `dimming.py`, `grb.py`, `mass_transfer.py`, `magnetar.py`, `minor.py`) plus `scheduler.py` and `base.py`. `base.py` defines an `Event` class with `eligible(state)`, `start(state, rng)`, `tick(state, dt)`, `is_done()` and `news_moments()`.
- `backend/app/sim/news.py`: source registry and bias rules (5.0.5). Calls the AI worker for text with fallback templates.
- New `Asset` fields: `mass`, `binary_partner`, `civ_level`, `multipliers: dict[str, {value, target, tau}]`, `is_magnetar` (hidden), `wd_mass`, `tags` (e.g. `ENCLOSED`).
- New stage: `ZOMBIE_STAR`.
- All constants (weights, probabilities, durations, distances, taus) go in `config.py` so they can be tuned live.
- Seed the RNG per game (`GAME_SEED`) so a demo run can be replayed.
- Tests: the Dyson price path matches the 5.1 table; merger share conversion conserves mass-weighted holdings; reported news numbers never exceed ±15 points from the truth; no terminal claim appears before its event resolves.
