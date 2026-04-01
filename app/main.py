import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.api.routes import categories, files, rows, campaigns, webhooks
from app.services.worker import dispatch_due_emails

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# APScheduler – created once at module level, started/stopped via lifespan
# ---------------------------------------------------------------------------
scheduler = AsyncIOScheduler()


from datetime import datetime, timezone

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: launch the background email dispatcher every 5 minutes."""
    scheduler.add_job(
        dispatch_due_emails,
        trigger=IntervalTrigger(minutes=5),
        id="email_dispatcher",
        name="Dispatch due emails to n8n",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
    logger.info("[Scheduler] Email dispatcher started (every 5 min).")

    yield  # App is running

    # Shutdown: stop the scheduler gracefully
    scheduler.shutdown(wait=False)
    logger.info("[Scheduler] Email dispatcher stopped.")


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/hello")
def read_root():
    return {"message": f"Hello from {settings.PROJECT_NAME} Modular Backend!"}


from app.api.routes import categories, files, rows, campaigns, webhooks, templates

app.include_router(categories.router)
app.include_router(files.router)
app.include_router(rows.router)
app.include_router(campaigns.router)
app.include_router(webhooks.router)
app.include_router(templates.router)
