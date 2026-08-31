"""
S41 - Consent-Based Alternative Credit & Financial Health Assistant
Backend entrypoint.

Run locally:
    uvicorn app.main:app --reload

Swagger/OpenAPI docs (PRD Section 46):
    http://localhost:8000/docs
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.database import engine, Base
from app import models as _models  # noqa: F401 - registers all models on Base.metadata

from app.utils.errors import APIError, ErrorCode
from app.utils.response import error_response

from app.routes import auth, users, consents, financial_data, transactions, analytics, credit_readiness, recommendations, assistant, demo

# Table creation: for the SQLite hackathon/demo path we still auto-create
# tables on startup for zero-friction local runs. For a real database
# (PostgreSQL etc.) use Alembic migrations instead - see backend/alembic
# and README "Database Migrations". Auto-creating with create_all() AND
# running Alembic against the same DB would conflict (Alembic wouldn't
# know those tables already exist), so we only do one or the other based
# on DATABASE_URL.
if settings.DATABASE_URL.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="S41 - Consent-Based Financial Health & Credit Readiness API",
    description=(
        "A consent-based financial health and credit-readiness assistant for students and "
        "micro-entrepreneurs. This is a decision-support and education platform - not a lender, "
        "credit bureau, or automatic loan approval system."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global exception handlers -> standard response envelope (PRD Section 22/27)
# ---------------------------------------------------------------------------
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.message, exc.error_code),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first_error.get("loc", []) if p != "body")
    message = f"Invalid input for '{field}': {first_error.get('msg', 'validation failed')}" if field else "Invalid input."
    return JSONResponse(
        status_code=422,
        content=error_response(message, ErrorCode.VALIDATION_ERROR, data={"errors": exc.errors()}),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=error_response("Something went wrong while processing your request.", ErrorCode.CALCULATION_ERROR),
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(consents.router)
app.include_router(financial_data.router)
app.include_router(transactions.router)
app.include_router(analytics.router)
app.include_router(credit_readiness.router)
app.include_router(recommendations.router)
app.include_router(assistant.router)
app.include_router(demo.router)


@app.get("/")
def root():
    return {
        "product": "S41 Consent-Based Financial Health & Credit Readiness Assistant",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
