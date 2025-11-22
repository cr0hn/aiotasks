"""Periodic tasks scheduler (Celery Beat compatible).

Provides scheduling functionality for periodic/scheduled tasks,
similar to Celery Beat. Supports cron-like schedules and intervals.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

log = logging.getLogger("aiotasks")


@dataclass
class Schedule:
    """Base class for task schedules."""

    def is_due(self, last_run: datetime | None = None) -> tuple[bool, float]:
        """Check if schedule is due to run.

        Args:
            last_run: Last execution time

        Returns:
            Tuple of (is_due, seconds_to_next_run)
        """
        raise NotImplementedError


@dataclass
class IntervalSchedule(Schedule):
    """Interval-based schedule (run every N seconds/minutes/hours).

    Examples:
        >>> IntervalSchedule(seconds=30)  # Every 30 seconds
        >>> IntervalSchedule(minutes=5)   # Every 5 minutes
        >>> IntervalSchedule(hours=1)     # Every hour
    """

    seconds: float = 0
    minutes: float = 0
    hours: float = 0
    days: float = 0

    def __post_init__(self):
        """Calculate total seconds."""
        self.total_seconds = (
            self.seconds + self.minutes * 60 + self.hours * 3600 + self.days * 86400
        )

        if self.total_seconds <= 0:
            msg = "Interval must be positive"
            raise ValueError(msg)

    def is_due(self, last_run: datetime | None = None) -> tuple[bool, float]:
        """Check if interval has elapsed."""
        if last_run is None:
            return True, self.total_seconds

        now = datetime.utcnow()
        elapsed = (now - last_run).total_seconds()

        if elapsed >= self.total_seconds:
            # Calculate seconds to next run
            next_run = self.total_seconds - (elapsed % self.total_seconds)
            return True, next_run

        # Not due yet
        remaining = self.total_seconds - elapsed
        return False, remaining


@dataclass
class CrontabSchedule(Schedule):
    """Cron-style schedule.

    Examples:
        >>> CrontabSchedule(minute='*/15')  # Every 15 minutes
        >>> CrontabSchedule(hour='0', minute='0')  # Daily at midnight
        >>> CrontabSchedule(hour='*/2', minute='30')  # Every 2 hours at :30
        >>> CrontabSchedule(day_of_week='1', hour='9')  # Every Monday at 9am
    """

    minute: str = "*"  # 0-59
    hour: str = "*"  # 0-23
    day_of_month: str = "*"  # 1-31
    month: str = "*"  # 1-12
    day_of_week: str = "*"  # 0-6 (0=Sunday)

    def __post_init__(self):
        """Parse cron expressions."""
        self._minute = self._parse_field(self.minute, 0, 59)
        self._hour = self._parse_field(self.hour, 0, 23)
        self._day_of_month = self._parse_field(self.day_of_month, 1, 31)
        self._month = self._parse_field(self.month, 1, 12)
        self._day_of_week = self._parse_field(self.day_of_week, 0, 6)

    def _parse_field(self, field: str, min_val: int, max_val: int) -> set[int]:
        """Parse cron field (*, number, */n, range)."""
        if field == "*":
            return set(range(min_val, max_val + 1))

        if field.startswith("*/"):
            # Step values */5 means every 5
            step = int(field[2:])
            return set(range(min_val, max_val + 1, step))

        if "-" in field:
            # Range: 1-5
            start, end = map(int, field.split("-"))
            return set(range(start, end + 1))

        if "," in field:
            # List: 1,3,5
            return set(map(int, field.split(",")))

        # Single value
        return {int(field)}

    def _matches(self, dt: datetime) -> bool:
        """Check if datetime matches cron schedule."""
        return (
            dt.minute in self._minute
            and dt.hour in self._hour
            and dt.day in self._day_of_month
            and dt.month in self._month
            and dt.weekday() in self._day_of_week
        )

    def is_due(self, last_run: datetime | None = None) -> tuple[bool, float]:
        """Check if cron schedule matches current time."""
        now = datetime.utcnow()

        # If matches current minute, it's due
        if self._matches(now):
            # Already ran this minute?
            if last_run and last_run.replace(second=0, microsecond=0) == now.replace(
                second=0, microsecond=0
            ):
                return False, 60.0  # Wait for next minute

            return True, 60.0  # Due now, check again in 60s

        # Calculate next run time (simplified - check every minute)
        return False, 60.0


@dataclass
class PeriodicTask:
    """Periodic task definition.

    Examples:
        >>> PeriodicTask(
        ...     name="cleanup",
        ...     schedule=IntervalSchedule(hours=1),
        ...     task="tasks.cleanup_old_data",
        ... )
        >>>
        >>> PeriodicTask(
        ...     name="daily_report",
        ...     schedule=CrontabSchedule(hour="7", minute="30"),
        ...     task="tasks.generate_daily_report",
        ...     kwargs={"format": "pdf"},
        ... )
    """

    name: str
    schedule: Schedule
    task: str | Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    enabled: bool = True
    last_run: datetime | None = None
    total_runs: int = 0

    def is_due(self) -> tuple[bool, float]:
        """Check if task is due to run."""
        if not self.enabled:
            return False, 0

        return self.schedule.is_due(self.last_run)

    def mark_run(self) -> None:
        """Mark task as executed."""
        self.last_run = datetime.utcnow()
        self.total_runs += 1


class PeriodicScheduler:
    """Scheduler for periodic tasks (Celery Beat style).

    Manages and executes periodic tasks based on their schedules.

    Example:
        >>> scheduler = PeriodicScheduler(app)
        >>>
        >>> # Add periodic task
        >>> scheduler.add_task(
        ...     name="cleanup",
        ...     schedule=IntervalSchedule(hours=1),
        ...     task="cleanup_old_data",
        ... )
        >>>
        >>> # Start scheduler
        >>> await scheduler.start()
    """

    def __init__(self, app: Any):
        """Initialize scheduler.

        Args:
            app: AioTasks application instance
        """
        self.app = app
        self._tasks: dict[str, PeriodicTask] = {}
        self._running = False
        self._scheduler_task: asyncio.Task | None = None

    def add_task(
        self,
        name: str,
        schedule: Schedule,
        task: str | Callable,
        args: tuple = (),
        kwargs: dict | None = None,
        enabled: bool = True,
    ) -> PeriodicTask:
        """Add periodic task to scheduler.

        Args:
            name: Task name (unique identifier)
            schedule: Schedule object (IntervalSchedule or CrontabSchedule)
            task: Task function name or callable
            args: Positional arguments for task
            kwargs: Keyword arguments for task
            enabled: Whether task is enabled

        Returns:
            Created PeriodicTask instance

        Example:
            >>> scheduler.add_task(
            ...     name="hourly_cleanup",
            ...     schedule=IntervalSchedule(hours=1),
            ...     task="cleanup",
            ... )
        """
        if kwargs is None:
            kwargs = {}

        periodic_task = PeriodicTask(
            name=name,
            schedule=schedule,
            task=task,
            args=args,
            kwargs=kwargs,
            enabled=enabled,
        )

        self._tasks[name] = periodic_task
        log.info(f"Added periodic task: {name}")

        return periodic_task

    def remove_task(self, name: str) -> bool:
        """Remove periodic task.

        Args:
            name: Task name

        Returns:
            True if removed, False if not found
        """
        if name in self._tasks:
            del self._tasks[name]
            log.info(f"Removed periodic task: {name}")
            return True

        return False

    def get_task(self, name: str) -> PeriodicTask | None:
        """Get periodic task by name."""
        return self._tasks.get(name)

    def list_tasks(self) -> list[PeriodicTask]:
        """List all periodic tasks."""
        return list(self._tasks.values())

    async def start(self) -> None:
        """Start the periodic scheduler."""
        if self._running:
            log.warning("Scheduler already running")
            return

        self._running = True
        log.info("Starting periodic task scheduler")

        self._scheduler_task = asyncio.create_task(self._run_scheduler())

    async def stop(self) -> None:
        """Stop the periodic scheduler."""
        if not self._running:
            return

        self._running = False
        log.info("Stopping periodic task scheduler")

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

    async def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        log.info("Periodic scheduler running")

        while self._running:
            try:
                # Check all tasks
                for task in self._tasks.values():
                    if not task.enabled:
                        continue

                    is_due, next_run = task.is_due()

                    if is_due:
                        log.debug(f"Scheduling periodic task: {task.name}")
                        await self._execute_task(task)

                # Sleep for 1 second before next check
                # TODO: Could be optimized to sleep until next due task
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception:
                log.exception("Error in periodic scheduler")
                await asyncio.sleep(5)

        log.info("Periodic scheduler stopped")

    async def _execute_task(self, task: PeriodicTask) -> None:
        """Execute a periodic task.

        Args:
            task: PeriodicTask to execute
        """
        try:
            # Get task function
            if callable(task.task):
                task_func = task.task
            else:
                # Look up task by name in app
                if not hasattr(self.app, "_manager"):
                    log.error(f"Cannot execute task {task.name}: no manager")
                    return

                # Get task from registered tasks
                task_func = self.app._manager.task_available_tasks.get(task.task)
                if task_func is None:
                    log.error(f"Task not found: {task.task}")
                    return

            # Queue the task
            log.info(f"Executing periodic task: {task.name}")

            # Call delay() to queue the task
            if hasattr(task_func, "delay"):
                await task_func.delay(*task.args, **task.kwargs)
            else:
                log.error(f"Task {task.task} does not have delay() method")
                return

            # Mark task as run
            task.mark_run()

            log.debug(
                f"Periodic task {task.name} queued (total runs: {task.total_runs})"
            )

        except Exception:
            log.exception(f"Error executing periodic task: {task.name}")


# Convenience functions for creating schedules

def every(seconds: float = 0, minutes: float = 0, hours: float = 0, days: float = 0) -> IntervalSchedule:
    """Create interval schedule.

    Args:
        seconds: Interval in seconds
        minutes: Interval in minutes
        hours: Interval in hours
        days: Interval in days

    Returns:
        IntervalSchedule instance

    Examples:
        >>> every(seconds=30)  # Every 30 seconds
        >>> every(minutes=5)   # Every 5 minutes
        >>> every(hours=2)     # Every 2 hours
    """
    return IntervalSchedule(seconds=seconds, minutes=minutes, hours=hours, days=days)


def crontab(
    minute: str = "*",
    hour: str = "*",
    day_of_month: str = "*",
    month: str = "*",
    day_of_week: str = "*",
) -> CrontabSchedule:
    """Create crontab schedule.

    Args:
        minute: Minute (0-59, *, */n)
        hour: Hour (0-23, *, */n)
        day_of_month: Day of month (1-31, *, */n)
        month: Month (1-12, *, */n)
        day_of_week: Day of week (0-6, 0=Sunday)

    Returns:
        CrontabSchedule instance

    Examples:
        >>> crontab(minute='*/15')  # Every 15 minutes
        >>> crontab(hour='0', minute='0')  # Daily at midnight
        >>> crontab(hour='9', day_of_week='1')  # Every Monday at 9am
    """
    return CrontabSchedule(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month=month,
        day_of_week=day_of_week,
    )


__all__ = (
    "Schedule",
    "IntervalSchedule",
    "CrontabSchedule",
    "PeriodicTask",
    "PeriodicScheduler",
    "every",
    "crontab",
)
