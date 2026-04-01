import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.limiter import limiter
from app.routers import admin, analytics, applications, auth, jobs, profile, users

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Queue an initial scrape on startup if the jobs table is empty."""
    from sqlalchemy import func, select

    from app.database import AsyncSessionLocal
    from app.models.job import Job

    try:
        async with AsyncSessionLocal() as db:
            job_count = (await db.execute(select(func.count()).select_from(Job))).scalar()
        if job_count == 0:
            from app.tasks.scrape_tasks import scrape_all_sources
            scrape_all_sources.delay()
            logger.info("Empty job database — initial scrape queued")
    except Exception as exc:
        logger.warning("Could not queue initial scrape on startup: %s", exc)

    yield


app = FastAPI(
    title="Job Matcher API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(analytics.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
