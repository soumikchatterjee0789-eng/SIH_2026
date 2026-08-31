# WiseGuardian — HTML/CSS/Vanilla JS

This version is a simple static frontend, now fully wired to the S41
FastAPI backend (`../backend`):

- HTML5 / CSS3 / Vanilla JavaScript
- No React, no Vite, no TypeScript, no Tailwind dependency
- Every screen (dashboard, consent manager, transactions, AI advisor)
  reads and writes real data through the backend's REST API — nothing
  is hardcoded/mock anymore.

## Run

1. Start the backend first (see `../backend/README.md`):
   ```bash
   cd ../backend
   uvicorn app.main:app --reload
   ```
   It must be reachable at `http://localhost:8000` (or update
   `API_BASE_URL` at the top of `js/script.js` if you run it elsewhere).

2. Serve this folder with a **real local web server** — do NOT just
   double-click `index.html`, since browsers send `Origin: null` for
   `file://` pages and the backend's CORS policy will reject the
   requests. Any of these work:
   ```bash
   # from inside Frontend/
   python3 -m http.server 5500
   # then open http://localhost:5500
   ```
   or use the VS Code **Live Server** extension (default port 5500).

3. Make sure the port you're serving on is listed in the backend's
   `FRONTEND_ORIGINS` env var (`.env`). `http://localhost:5500` and
   `http://127.0.0.1:5500` are included in `backend/.env.example` by
   default.

## What's connected

- **Auth** — register/login screen, JWT stored in `localStorage`,
  attached as `Authorization: Bearer <token>` on every request.
  401 responses automatically log the user out.
- **Consent Manager** — toggles call the real
  `POST /api/consents` / `DELETE /api/consents/{id}` endpoints;
  the audit log is built from actual `granted_at` / `revoked_at`
  timestamps.
- **Dashboard** — `analytics/summary`, `analytics/cash-flow`,
  `analytics/expenses`, `credit-readiness`, and `recommendations` are
  all fetched live and re-fetched after any data or consent change.
- **Data & Transactions** — the manual "Add Transaction" form posts to
  `financial-data/income` or `financial-data/expenses`. The CSV
  uploader implements the backend's two-step preview → confirm flow
  (`POST /api/transactions/upload`) exactly as documented in the
  backend README.
- **AI Advisor** — chat messages are sent to `POST /api/assistant/chat`
  and answered from real, structured backend data (no more scripted
  local responses).
- **Load Demo Data** button (home screen) calls `POST /api/demo/seed`
  so you can explore the whole app without entering real financial
  information.

If a request needs consent that hasn't been granted yet, the backend
returns `CONSENT_REQUIRED` / `CONSENT_REVOKED` and the UI surfaces that
message via a toast — grant the relevant category in **Consent
Manager** and retry.
