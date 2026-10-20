"""Main FastAPI entry point for ImpactLab."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from impactlab.api.routes import experiments, impact, profiles, sessions
from impactlab.api.ws import ws_manager
from impactlab.config import settings
from impactlab.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize database and dependencies on startup."""
    init_db()
    yield


app = FastAPI(
    title="ImpactLab API",
    description="Limit Order Book Simulator & Market Impact Analysis (NSE-style)",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Format HTTP errors with consistent error object."""
    code_map = {
        400: "BAD_REQUEST",
        404: "NOT_FOUND",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
    }
    error_code = code_map.get(exc.status_code, "ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": error_code, "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format schema validation errors consistently."""
    errors = exc.errors()
    msg = errors[0].get("msg", "Validation error") if errors else "Validation failed"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": {"code": "VALIDATION_ERROR", "message": msg}},
    )


# Health check
@app.get("/health", tags=["system"])
@app.get(f"{settings.api_v1_prefix}/health", tags=["system"])
def health() -> dict[str, str]:
    """Health and liveness endpoint."""
    return {"status": "ok", "app": settings.app_name}


# WebSocket stream
@app.websocket("/ws/sessions/{session_id}")
async def websocket_session_stream(websocket: WebSocket, session_id: str) -> None:
    """WebSocket stream pushing real-time order book ladders and executed trades."""
    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            # Keep connection alive; can receive client heartbeat
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)


# Include API v1 routers
app.include_router(profiles.router, prefix=settings.api_v1_prefix)
app.include_router(sessions.router, prefix=settings.api_v1_prefix)
app.include_router(impact.router, prefix=settings.api_v1_prefix)
app.include_router(experiments.router, prefix=settings.api_v1_prefix)
