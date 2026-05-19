"""APScheduler-backed job scheduler for Eworks OS campaigns."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manages background scheduled jobs for campaign automation."""

    def __init__(self):
        self._scheduler = None
        self._running = False

    def _get_scheduler(self):
        """Lazily create the APScheduler BackgroundScheduler."""
        if self._scheduler is None:
            try:
                from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
                from apscheduler.jobstores.memory import MemoryJobStore  # type: ignore
                from apscheduler.executors.pool import ThreadPoolExecutor  # type: ignore
            except ImportError as exc:
                raise RuntimeError(
                    "apscheduler is not installed. Run: pip install apscheduler"
                ) from exc

            jobstores = {"default": MemoryJobStore()}
            executors = {"default": ThreadPoolExecutor(max_workers=4)}
            job_defaults = {"coalesce": True, "max_instances": 1}

            from apscheduler.schedulers.background import BackgroundScheduler
            self._scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
            )
        return self._scheduler

    def add_campaign_job(
        self,
        campaign_id: int,
        cron_expression: str = "0 9 * * 1-5",
        func=None,
        job_id: str | None = None,
    ) -> str:
        """Add a cron-based job to run a campaign.

        Args:
            campaign_id: ID of the campaign to run.
            cron_expression: Standard cron string (e.g. '0 9 * * 1-5').
            func: Callable to invoke — defaults to a placeholder log function.
            job_id: Optional explicit job ID.

        Returns:
            The assigned job ID.
        """
        scheduler = self._get_scheduler()
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expression!r}")

        minute, hour, day, month, day_of_week = parts

        job_id = job_id or f"campaign_{campaign_id}"

        if func is None:
            def _default_func():
                logger.info("Campaign %d scheduled run triggered", campaign_id)
            func = _default_func

        job = scheduler.add_job(
            func,
            trigger="cron",
            id=job_id,
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            replace_existing=True,
        )
        logger.info("Job %s added for campaign %d (%s)", job_id, campaign_id, cron_expression)
        return job.id

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job by ID. Returns True if removed."""
        scheduler = self._get_scheduler()
        try:
            scheduler.remove_job(job_id)
            logger.info("Job %s removed", job_id)
            return True
        except Exception as exc:
            logger.warning("Could not remove job %s: %s", job_id, exc)
            return False

    def list_jobs(self) -> list[dict[str, Any]]:
        """Return a list of scheduled jobs as dicts."""
        scheduler = self._get_scheduler()
        jobs = scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in jobs
        ]

    def start(self) -> None:
        """Start the background scheduler."""
        scheduler = self._get_scheduler()
        if not self._running:
            scheduler.start()
            self._running = True
            logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the background scheduler gracefully."""
        if self._scheduler and self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Scheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._running
