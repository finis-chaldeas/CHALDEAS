"""
CHALDEAS - Main FastAPI Application

The entry point for the Chaldeas historical knowledge system.
Implements World-Centric Architecture with FGO-inspired naming.
"""
# Load environment variables first
from dotenv import load_dotenv
load_dotenv("../.env")

import os
import sentry_sdk

# Initialize Sentry for error tracking (disabled by default)
sentry_dsn = os.getenv("SENTRY_DSN")
sentry_enabled = os.getenv("SENTRY_ENABLED", "false").lower() == "true"
if sentry_dsn and sentry_enabled:
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=os.getenv("ENVIRONMENT", "development"),
        traces_sample_rate=0.1,  # 10% of requests for performance monitoring
        profiles_sample_rate=0.1,
    )
    print(f"[Sentry] Initialized for {os.getenv('ENVIRONMENT', 'development')}")
elif sentry_dsn:
    print("[Sentry] DSN configured but SENTRY_ENABLED=false, error tracking disabled")
else:
    print("[Sentry] DSN not configured, error tracking disabled")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
import uuid

from app.config import get_settings

logger = logging.getLogger(__name__)
from app.api.v1.router import api_router
from app.api.v1_new import router as v1_new_router

settings = get_settings()

# Rate limiter — keyed by client IP
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title=settings.project_name,
    description="""
    CHALDEAS: World-Centric Historical Knowledge System

    A system for exploring world history, philosophy, science, mythology,
    and biographical information across time and space.

    ## Systems

    - **CHALDEAS**: World state management (immutable snapshots)
    - **SHEBA**: Observation and query processing
    - **LAPLACE**: Explanation and source attribution
    - **TRISMEGISTOS**: Content showcase & archive
    - **PAPERMOON**: Proposal verification
    - **LOGOS**: LLM-based action proposer
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(v1_new_router)  # V1 New (Historical Chain) - already has /api/v1 prefix


# ============== Global Exception Handlers ==============

def _trace_id() -> str:
    """Generate a short trace ID for error correlation."""
    return uuid.uuid4().hex[:8]


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors."""
    tid = _trace_id()
    logger.error(f"[{tid}] Database error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Database error occurred", "type": "database_error", "trace_id": tid}
    )


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors (duplicates, FK violations)."""
    tid = _trace_id()
    logger.warning(f"[{tid}] Integrity error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=409,
        content={"detail": "Data conflict - duplicate or invalid reference", "type": "integrity_error", "trace_id": tid}
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    tid = _trace_id()
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "type": "validation_error", "trace_id": tid}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions."""
    tid = _trace_id()
    logger.error(f"[{tid}] Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": "internal_error", "trace_id": tid}
    )


@app.get("/")
async def root():
    """Root endpoint - system status."""
    return {
        "system": "CHALDEAS",
        "status": "operational",
        "version": "0.1.0",
        "subsystems": {
            "chaldeas": "online",  # World state
            "sheba": "standby",    # Observer
            "laplace": "standby",  # Explainer
            "trismegistos": "online",  # Archive showcase
            "papermoon": "standby",    # Authority
            "logos": "standby",        # Actor
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
