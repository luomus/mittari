

The purpose of this web app is to test new kind of statistics and visualizations before they are implemented into a production system. Therefore it does not need to be polished or production-ready.

Keep the app simple. Don't implement features that are not requested.

Avoid extensive error handling.

No fallback logic. No backwards compatibility.

api.laji.fi requires a token to be used. The token is stored in `.env.local` (local) and `.env.openshift` (production) as LAJI_API_ACCESS_TOKEN.

The app is run locally with Docker Compose, or with **uv** (`uv sync` then `uv run --env-file .env.local …` as in the README). Use one of those so dependencies and `.env.local` are applied; ad‑hoc `python wsgi.py` without a venv or env file is not supported.

The production app is deployed to CSC OpenShift Rahti.

For important issues, ask for clarification or advice instead of making assumptions.

Avoid doing excessive smoke tests or running complex commands unless requested.