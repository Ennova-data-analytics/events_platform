import logging
from apscheduler.schedulers.background import BackgroundScheduler

from core.config import settings
from domain.services.recruitment.jobs import (
    run_interview_reminders, run_booking_nudges, run_gdpr_retention,
)

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    """
    Start the recruitment background jobs. Single-process by design — if you run
    multiple uvicorn workers, enable this on only one (or move to a dedicated
    worker) to avoid duplicate sends. Disable via RECRUITMENT_SCHEDULER_ENABLED.
    """
    global _scheduler
    if not settings.RECRUITMENT_SCHEDULER_ENABLED:
        logger.info("Recruitment scheduler disabled by config")
        return
    if _scheduler:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(run_interview_reminders, "interval", hours=1, id="interview_reminders", replace_existing=True)
    _scheduler.add_job(run_booking_nudges, "interval", hours=6, id="booking_nudges", replace_existing=True)
    _scheduler.add_job(run_gdpr_retention, "cron", hour=3, minute=0, id="gdpr_retention", replace_existing=True)
    _scheduler.start()
    logger.info("Recruitment scheduler started (reminders hourly, nudges 6h, retention daily)")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
