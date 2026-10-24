# Team guidance

This is a hackathon project with a React/TypeScript frontend and a Python/FastAPI
backend. Read `README.md` for setup and `docs/STAR_MARKET_SPEC.md` for the game idea.

## Current scope

The code intentionally contains only minimal boilerplate. The specification is
a design reference, not a request to implement every feature. Follow the current
teammate's request and build incrementally. Do not restore game models, sample
data, events, pricing or other feature scaffolding just because the spec lists
them.

## Suggested work areas

- **Frontend:** work in `frontend/`. Build the interface and connect it to API
  shapes agreed with the backend teammate.
- **Backend:** work in `backend/`. Grow the FastAPI app as needed for the current
  task. Keep shared game state, trade validation and balances on the server.
- **AI integration:** work alongside the backend teammate; add an AI module when
  implementation starts. Focus on the Gemma connection, prompts and validated
  outputs. The model can propose content and events; ordinary server code owns
  prices and balances. Keep model calls separate from time-sensitive game work.

These are broad ownership guidelines. Exact files, APIs, data structures,
storage and implementation order are for the team to decide as work progresses.

## Working together

- Agree small input/output shapes before connecting frontend, backend and AI work.
- Keep changes focused on the assigned task and flag changes that affect another
  teammate's area.
- Prefer simple solutions and add dependencies only when needed.
- Keep local secrets out of Git and update setup instructions when commands change.
- Check the code you change and leave a short handoff describing what works and
  what remains unfinished.
