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
