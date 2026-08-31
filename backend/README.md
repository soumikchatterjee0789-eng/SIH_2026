# S41 Backend — Consent-Based Alternative Credit & Financial Health Assistant

A FastAPI backend for a consent-based financial health and credit-readiness
assistant for students and micro-entrepreneurs. This is a **financial
decision-support and education platform** — not a lender, credit bureau, or
automatic loan approval system.

Core principles baked into every module: **Consent + Explainability +
Correctability + Financial Health + Responsible Borrowing.**

---

## 1. Tech Stack

- **Python 3.11+** / **FastAPI**
- **SQLAlchemy 2.0** ORM + **Alembic** migrations
- **SQLite** for local/demo use, **PostgreSQL**-ready via `DATABASE_URL`
- **JWT** auth (`python-jose`) + **bcrypt** password hashing (`passlib`)
- **Pydantic v2** for request/response validation
- **Financial Analytics Engine** — **pandas** for grouping/aggregating
  income, expense, and transaction records into monthly cash-flow series
  and category breakdowns (`services/analytics_service.py`); **NumPy**
  for the mean/variability statistics behind income and expense
  stability scoring (`services/credit_readiness_service.py`);
  **scikit-learn** (`IsolationForest`) for flagging unusually high
  category spend against a user's own history
  (`services/spending_insights_service.py`)
- **pytest** + `httpx`/`TestClient` for automated tests

The Credit Readiness Score itself stays a transparent, deterministic,
weighted rule-based calculation — never an opaque ML prediction (PRD
Section 35 / Section 4.5 "Score Separation"). Pandas/NumPy/scikit-learn
are used for data processing and pattern-detection *inputs* to that score
and to recommendations, and every number they produce is surfaced back to
the person in the explanation, not hidden behind a bare model output.

---

## 2. Quick Start

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then edit SECRET_KEY etc. for real use

uvicorn app.main:app --reload
```

The API is now running at `http://localhost:8000`.
Interactive OpenAPI/Swagger docs: **http://localhost:8000/docs**

For local SQLite development, tables are created automatically on startup
via `Base.metadata.create_all()` — no extra step needed. For PostgreSQL or
any other real database, use Alembic instead (see "Database Migrations"
below); `create_all()` only fires when `DATABASE_URL` starts with `sqlite`,
specifically so it never conflicts with Alembic-managed schemas.

### Run tests

```bash
pytest -v
```

All tests use an isolated `test_s41.db` SQLite file and never touch your
dev database. 19/19 tests pass as of this build.

---

## 2a. Database Migrations (Alembic)

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/).
It reads `DATABASE_URL` from the same `app/config/settings.py` used by the
app, so there's no second place to configure a DB connection.

```bash
cd backend

# Point at whatever DB you're migrating (defaults to the SQLite dev DB
# if DATABASE_URL isn't set — see app/config/settings.py):
export DATABASE_URL="postgresql://user:pass@host:5432/s41"   # Windows: set DATABASE_URL=...

alembic upgrade head        # apply all migrations (creates every table + index)
alembic downgrade base      # roll all the way back (drops everything Alembic created)
alembic current             # show which revision the DB is on
alembic history              # list all revisions
```

**After changing a model** (adding a column, index, table, etc.):

```bash
alembic revision --autogenerate -m "short description of the change"
```

Then open the generated file in `alembic/versions/` and read it —
autogenerate is a strong starting point, not a guarantee. It won't detect
things like column renames (it sees those as drop + add) or data
migrations, and it won't backfill existing rows. Fix those by hand before
running `alembic upgrade head`.

The initial migration (`alembic/versions/..._initial_schema.py`) creates
all 15 tables and every index used by the app, including the composite
indexes analytics/consent/credit-readiness queries rely on
(`(user_id, data_category)` on consents, `(user_id, record_date)` on each
financial record type, `(user_id, type, transaction_date)` on
transactions, `(user_id, is_current)` on credit scores, etc.) — these
speed up exactly the lookups `consent_service.get_active_consent_categories()`,
`analytics_service`, and `credit_readiness_service` run on every request.

---

## 3. Environment Variables

See `.env.example`. Key ones:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `sqlite:///./s41_dev.db` for local dev, or a `postgresql://...` URL in production |
| `SECRET_KEY` | JWT signing key — **must** be overridden in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime |
| `FRONTEND_ORIGINS` | Comma-separated CORS allow-list |
| `AI_API_KEY` | Optional — only used for future natural-language phrasing. Everything works correctly without it. |

Never commit `.env` — it's in `.gitignore`. Never hard-code secrets in code.

---

## 4. Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, routers, exception handlers
│   ├── database.py              # engine/session/Base
│   ├── config/
│   │   ├── settings.py          # env-based settings
│   │   └── thresholds.py        # FINANCIAL_HEALTH_THRESHOLDS, scoring weights (central config)
│   ├── models/                  # SQLAlchemy ORM models (one file per entity group)
│   ├── schemas/                 # Pydantic request/response models
│   ├── routes/                  # FastAPI routers (one file per API resource)
│   ├── services/                # Business logic (analytics, scoring, consent, etc.)
│   └── utils/                   # response envelope, error codes, auth deps, security
├── tests/                       # pytest suite
├── requirements.txt
├── .env.example
└── README.md
```

---

## 5. Standard API Response Format

Every endpoint returns one consistent envelope (PRD §22):

**Success**
```json
{ "success": true, "data": { ... }, "message": "Request successful" }
```

**Error**
```json
{ "success": false, "data": null, "message": "...", "error_code": "..." }
```

Documented error codes: `INVALID_INPUT`, `INVALID_TRANSACTION`,
`CONSENT_REQUIRED`, `CONSENT_REVOKED`, `UNAUTHORIZED`, `DATA_NOT_FOUND`,
`INSUFFICIENT_DATA`, `CALCULATION_ERROR`, `ALREADY_EXISTS`, `VALIDATION_ERROR`.

---

## 6. API Contract Notes (read this before wiring up a frontend)

The PRD's Section 21 lists a flat, generic `/api/financial-data` family of
endpoints. Because income, expense, savings, and borrowing records each have
distinct fields, this implementation documents them as explicit
sub-resources under that same base path rather than one generic shape:

```
GET    /api/financial-data                  -> combined bundle (income/expenses/savings/borrowing, consent-filtered)
POST   /api/financial-data/income
GET    /api/financial-data/income
PUT    /api/financial-data/income/{id}
DELETE /api/financial-data/income/{id}
POST   /api/financial-data/expenses
GET    /api/financial-data/expenses
PUT    /api/financial-data/expenses/{id}
DELETE /api/financial-data/expenses/{id}
POST   /api/financial-data/savings
GET    /api/financial-data/savings
DELETE /api/financial-data/savings/{id}
POST   /api/financial-data/borrowing         (optional — requires 'borrowing' consent)
GET    /api/financial-data/borrowing
DELETE /api/financial-data/borrowing/{id}
```

This keeps the base path from the PRD stable while making every payload
shape explicit and independently documented in Swagger. If your frontend
team specifically needs the flat generic contract instead, treat this as
the one intentional architecture deviation and adjust `app/routes/financial_data.py`
— everything else follows the PRD's contract exactly.

### Full endpoint list

```
POST   /api/auth/register
POST   /api/auth/login            (OAuth2 form: username=email, password)
POST   /api/auth/login-json       (JSON body alternative)
POST   /api/auth/logout

GET    /api/users/me
PUT    /api/users/me

GET    /api/consents
POST   /api/consents
DELETE /api/consents/{consent_id}

GET    /api/financial-data                  (see above)
...financial-data sub-resources (see above)

POST   /api/transactions/upload   (multipart: file, confirm, batch_token)
GET    /api/transactions
PUT    /api/transactions/{id}
DELETE /api/transactions/{id}

GET    /api/analytics/summary
GET    /api/analytics/cash-flow
GET    /api/analytics/expenses
GET    /api/analytics/savings

GET    /api/credit-readiness              (recomputes live, persists, returns factors)
GET    /api/credit-readiness/explanation  (returns current stored score's factors only)

GET    /api/recommendations

POST   /api/assistant/chat
GET    /api/assistant/history

POST   /api/demo/seed             (seeds clearly-labelled synthetic data, PRD §29)
```

---

## 7. Consent Enforcement (PRD §4.1 / §8)

Every write (and most reads) to income, expenses, savings, borrowing, and
transactions requires an **active** consent record for that specific
category. This is enforced via the `require_consent(category)` FastAPI
dependency in `app/utils/deps.py` — not scattered ad-hoc checks. Revoking a
consent immediately blocks further use of that category's data
(`CONSENT_REVOKED`), and attempting an action before ever granting consent
returns `CONSENT_REQUIRED`.

Consent categories: `income`, `expenses`, `transactions`, `savings`, `borrowing`.

---

## 8. Financial Health Engine (PRD §11–13)

All formulas live in `app/services/analytics_service.py`:

- `Net Cash Flow = Total Income − Total Expenses`
- `Savings Rate = (Net Cash Flow / Total Income) × 100` — **returns `null`
  if income is 0**, never divides by zero.
- `Expense Ratio = (Total Expenses / Total Income) × 100`
- `Emergency Buffer = Emergency Savings / Average Monthly Essential Expenses`
  (in months)
- Classification (`HEALTHY` / `STABLE` / `NEEDS_ATTENTION` / `HIGH_RISK`) is
  driven entirely by `FINANCIAL_HEALTH_THRESHOLDS` in
  `app/config/thresholds.py` — no thresholds are hard-coded elsewhere.

The frontend must never recompute these numbers itself (PRD §32) — always
render what the API returns.

---

## 9. Credit Readiness Engine (PRD §14–17)

Lives in `app/services/credit_readiness_service.py`. Deterministic, weighted,
fully explainable — **not** a black-box ML model (PRD §35 explicitly prefers
this for a hackathon MVP).

- Weights are centrally configured in `CREDIT_READINESS_WEIGHTS`
  (`app/config/thresholds.py`) and sum to 100.
- Six factors: Income Stability, Cash Flow Health, Savings Capacity, Expense
  Stability, Existing Repayment Burden, Emergency Buffer.
- Every factor returns a signed point impact, a direction, and a
  human-readable explanation — returned together with the score
  (PRD §16 example format).
- **Never** uses protected/sensitive attributes (PRD §15) — the data model
  doesn't store them, and the engine asserts against `PROHIBITED_SCORING_ATTRIBUTES`
  defensively.
- If there isn't enough consented data yet, the API returns
  `INSUFFICIENT_DATA` — **never** a fabricated score of 0 (PRD §28).
- Every `GET /api/credit-readiness` call recomputes live from current data
  and persists a new score record (history preserved via `is_current`), so
  a correction to income/expenses is reflected on the very next fetch
  (PRD §17 example: "score changed from 64 → 71 because...").
- The response always carries a disclaimer distinguishing this indicator
  from a bureau/CIBIL credit score (PRD §4.5).

---

## 10. AI Assistant (PRD §19–20)

`app/services/assistant_service.py` is a rule-based Q&A layer that always
computes structured answers from `analytics_service` /
`credit_readiness_service` / `recommendation_service` first — it **never**
invents transactions, scores, or guarantees. If there isn't enough data to
answer, it says so explicitly rather than guessing (PRD §20).

This design intentionally works with **zero external API dependency** (PRD
§34: "the system must work even if advanced ML is unavailable"). An
`AI_API_KEY` hook exists in settings for a future iteration that *rephrases*
already-computed answers in more natural language — it must never be used
to invent the underlying numbers.

---

## 11. CSV Transaction Upload (PRD §10)

`POST /api/transactions/upload` implements the exact two-step flow from the
PRD:

1. **Preview** (`confirm=false`, default): parses and validates the CSV,
   returns per-row validity + errors. **Nothing is stored yet.**
2. **Confirm** (`confirm=true` + `batch_token` from step 1): stores only the
   previously-validated valid rows, applying simple keyword-based
   auto-categorization when a row's category is blank.

Required CSV columns: `date, description, amount, type` (`category` optional).
`type` must be `income` or `expense`. Dates accept `YYYY-MM-DD`, `DD-MM-YYYY`,
or `DD/MM/YYYY`.

---

## 12. Auditability (PRD §24)

Every meaningful mutation — data create/update/delete, consent grant/revoke,
score generation/recalculation, and user corrections — is written to the
`audit_logs` table via `app/services/audit_service.py`. This is intentionally
**not** exposed on any normal dashboard endpoint.

---

## 13. Security (PRD §38)

- Passwords are hashed with bcrypt, never stored in plaintext.
- JWT auth on every protected route via `get_current_user`.
- All input is validated through Pydantic schemas (rejecting negative
  amounts, invalid enums, malformed dates, etc.).
- CORS is restricted to `FRONTEND_ORIGINS`.
- No secrets are hard-coded — everything comes from environment variables
  (`app/config/settings.py`).
- SQL injection is not possible through normal use since all queries go
  through the SQLAlchemy ORM with parameter binding.

---

## 14. Demo Mode (PRD §29)

`POST /api/demo/seed` (requires auth) grants demo consents and inserts
clearly-labelled synthetic financial data (`[DEMO]` prefixes) for the
current user, so the whole product can be demonstrated end-to-end without
real financial information.

---

## 15. Deploying

```
Frontend  -> Vercel / Netlify
Backend   -> Render / Railway / AWS / Fly.io  (this repo)
Database  -> Managed PostgreSQL
```

Set `DATABASE_URL` to your PostgreSQL connection string, a strong random
`SECRET_KEY`, and the real `FRONTEND_ORIGINS` in your platform's environment
variable settings — never in code. Run `alembic upgrade head` once against
that `DATABASE_URL` (see "Database Migrations" above) to create the schema;
`create_all()` deliberately does nothing for a non-SQLite URL, so this step
is required before the API can serve any request that touches the DB. Also
install a PostgreSQL driver (`pip install psycopg2-binary`) since it isn't
in `requirements.txt` by default — the app stays DB-agnostic until you pick one.

---

## 16. Pushing to GitHub

```bash
cd backend
git init
git add .
git commit -m "Initial commit: S41 consent-based financial health backend"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

`.env`, `venv/`, and `*.db` files are already excluded via `.gitignore`, so
no secrets or local databases will be pushed.

---

## 17. What's Deliberately Out of Scope for This MVP

Per PRD §40 ("Nice to Have"), these are not implemented and can be added
later without breaking the existing contract: the scenario simulator,
voice/multilingual assistant, and external financial-data integrations.
Lightweight ML-based unusual-spending detection (scikit-learn
`IsolationForest`, see Section 1) *is* implemented — it flags a category
whose latest month is a clear statistical outlier vs. that user's own
history and surfaces the actual numbers in the explanation, rather than
gatekeeping the credit-readiness score itself, which stays a transparent
rule-based calculation. The consent/explainability/correctability
workflow (the PRD's non-negotiable core) is fully implemented and tested.
