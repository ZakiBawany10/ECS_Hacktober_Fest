import os

TICK_SECONDS = float(os.getenv("TICK_SECONDS", "1.0"))

STARTING_CASH = 10_000.0
SHARES_PER_STAR = 1_000.0

# Price per share = PRICE_SCALE × (log10(L/L☉) + LOG_LUMINOSITY_OFFSET).
# See docs/main_sequence_pricing_data.md.
PRICE_SCALE = 100.0
LOG_LUMINOSITY_OFFSET = 5.0

# Twinkle noise, in log10(L) units per tick, pulled back towards the star's base L.
TWINKLE_SIGMA = 0.003
TWINKLE_REVERSION = 0.05

HISTORY_LENGTH = 600  # price points kept per asset (10 minutes at 1 tick/s)
LEADERBOARD_EVERY_TICKS = 5

# Trading pressure: each trade nudges a star's price multiplier, which then decays back to 1.
# A 10k buy lifts the price by IMPACT_PER_10K (1%), and sells push it down the same way.
IMPACT_PER_10K = 0.01
IMPACT_CAP = 0.15  # the multiplier stays within 1 ± this
IMPACT_DECAY = 0.1  # fraction of the gap to 1 closed each tick

# Gemma runs locally through Ollama; see app/ai/. It only writes text: server code owns prices.
GEMMA_BASE_URL = os.getenv("GEMMA_BASE_URL", "http://localhost:11434")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma4:e4b-it-q4_K_M")
GEMMA_TIMEOUT_SECONDS = 10.0  # per HTTP attempt
GEMMA_KEEP_ALIVE = "30m"  # keeps the model loaded between calls; reloading it takes about 5 s
HEADLINE_DEADLINE_SECONDS = 5.0  # a headline Gemma hasn't written by then falls back to a template
