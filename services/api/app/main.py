from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .agents.llm import AgentError
from .config import get_settings
from .db import Base, engine
from .routers import auth, coach, code, interviews, plan, profile, progress, quiz, tasks, topics, voice


def _apply_lightweight_migrations() -> None:
    """Dev convenience for existing SQLite files: add columns create_all won't."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("user_profiles")}
    if "locale" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE user_profiles ADD COLUMN locale VARCHAR(10) DEFAULT 'en'"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience; production uses Alembic migrations (database/).
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth.router, profile.router, topics.router, tasks.router,
               interviews.router, progress.router, coach.router,
               quiz.router, plan.router, voice.router, code.router):
    app.include_router(router)


@app.exception_handler(AgentError)
async def agent_error_handler(request: Request, exc: AgentError) -> JSONResponse:
    # Provider failures (no quota, bad key, rate limit) surface as a readable
    # message instead of a raw 500 traceback.
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "mock_ai": not settings.ai_enabled,
        "local_mode": settings.local_mode,
        "llm_provider": settings.llm_provider if settings.ai_enabled else None,
    }
