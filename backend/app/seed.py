# One main-sequence star per spectral type, with mass and temperature inside the ranges in
# docs/main_sequence_pricing_data.md. Mass is in solar units, temperature in K; both are display only.
# Each star's L is generated at startup within its spectral type's bounds, and the spectral type
# decides its lifecycle path (see lifecycle.MAIN_SEQUENCE_L_BOUNDS and lifecycle.LIFECYCLE_PATHS).
# seconds_left (optional) starts a star late in its main-sequence life so the demo shows a transition early.
SEED_STARS = [
    {"id": "kestrel", "name": "Kestrel", "spectral_type": "O", "mass": 40.0, "temperature": 40_000.0, "seconds_left": 40},
    {"id": "brightwater", "name": "Brightwater", "spectral_type": "B", "mass": 8.0, "temperature": 20_000.0},
    {"id": "altra", "name": "Altra", "spectral_type": "A", "mass": 2.0, "temperature": 8_500.0, "seconds_left": 90},
    {"id": "fenwick", "name": "Fenwick", "spectral_type": "F", "mass": 1.3, "temperature": 6_500.0},
    {"id": "sol-nova", "name": "Sol Nova", "spectral_type": "G", "mass": 1.0, "temperature": 5_800.0},
    {"id": "kora", "name": "Kora", "spectral_type": "K", "mass": 0.75, "temperature": 4_600.0},
    {"id": "ember", "name": "Ember", "spectral_type": "M", "mass": 0.3, "temperature": 3_200.0},
]
