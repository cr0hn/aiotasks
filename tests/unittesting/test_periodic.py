"""Comprehensive unit tests for Periodic Tasks.

Tests cover:
- IntervalSchedule creation and is_due logic
- CrontabSchedule creation and cron expression parsing
- PeriodicScheduler task management
- Schedule execution timing
- Error handling and edge cases
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from aiotasks.periodic import (
    CrontabSchedule,
    IntervalSchedule,
    PeriodicScheduler,
    PeriodicTask,
    crontab,
    every,
)


class TestIntervalSchedule:
    """Test IntervalSchedule class."""

    def test_create_interval_seconds(self):
        """Test creating interval with seconds."""
        schedule = IntervalSchedule(seconds=30)

        assert schedule.seconds == 30
        assert schedule.total_seconds == 30

    def test_create_interval_minutes(self):
        """Test creating interval with minutes."""
        schedule = IntervalSchedule(minutes=5)

        assert schedule.minutes == 5
        assert schedule.total_seconds == 300  # 5 * 60

    def test_create_interval_hours(self):
        """Test creating interval with hours."""
        schedule = IntervalSchedule(hours=2)

        assert schedule.hours == 2
        assert schedule.total_seconds == 7200  # 2 * 3600

    def test_create_interval_days(self):
        """Test creating interval with days."""
        schedule = IntervalSchedule(days=1)

        assert schedule.days == 1
        assert schedule.total_seconds == 86400  # 24 * 3600

    def test_create_interval_mixed(self):
        """Test creating interval with mixed units."""
        schedule = IntervalSchedule(hours=1, minutes=30, seconds=45)

        expected = 3600 + 1800 + 45  # 5445 seconds
        assert schedule.total_seconds == expected

    def test_create_interval_zero_raises_error(self):
        """Test that zero interval raises error."""
        with pytest.raises(ValueError, match="Interval must be positive"):
            IntervalSchedule(seconds=0)

    def test_create_interval_negative_raises_error(self):
        """Test that negative interval raises error."""
        with pytest.raises(ValueError, match="Interval must be positive"):
            IntervalSchedule(seconds=-10)

    def test_is_due_first_run(self):
        """Test is_due returns True for first run."""
        schedule = IntervalSchedule(seconds=60)

        is_due, next_run = schedule.is_due(last_run=None)

        assert is_due is True
        assert next_run == 60

    def test_is_due_after_interval(self):
        """Test is_due after interval has elapsed."""
        schedule = IntervalSchedule(seconds=60)

        # Last run was 70 seconds ago
        last_run = datetime.utcnow() - timedelta(seconds=70)

        is_due, next_run = schedule.is_due(last_run=last_run)

        assert is_due is True
        assert next_run > 0

    def test_is_due_before_interval(self):
        """Test is_due before interval has elapsed."""
        schedule = IntervalSchedule(seconds=60)

        # Last run was 30 seconds ago
        last_run = datetime.utcnow() - timedelta(seconds=30)

        is_due, next_run = schedule.is_due(last_run=last_run)

        assert is_due is False
        assert next_run == pytest.approx(30, abs=1)

    def test_every_helper_function(self):
        """Test every() helper function."""
        schedule = every(minutes=10)

        assert isinstance(schedule, IntervalSchedule)
        assert schedule.total_seconds == 600


class TestCrontabSchedule:
    """Test CrontabSchedule class."""

    def test_create_crontab_defaults(self):
        """Test creating crontab with defaults (all *)."""
        schedule = CrontabSchedule()

        assert schedule.minute == "*"
        assert schedule.hour == "*"
        assert schedule.day_of_month == "*"
        assert schedule.month == "*"
        assert schedule.day_of_week == "*"

    def test_create_crontab_specific_time(self):
        """Test creating crontab with specific time."""
        schedule = CrontabSchedule(hour="7", minute="30")

        assert schedule.hour == "7"
        assert schedule.minute == "30"

    def test_parse_wildcard(self):
        """Test parsing wildcard *."""
        schedule = CrontabSchedule(minute="*")

        # Should match all minutes 0-59
        assert len(schedule._minute) == 60
        assert 0 in schedule._minute
        assert 59 in schedule._minute

    def test_parse_specific_value(self):
        """Test parsing specific value."""
        schedule = CrontabSchedule(minute="15")

        assert schedule._minute == {15}

    def test_parse_step_values(self):
        """Test parsing step values */n."""
        schedule = CrontabSchedule(minute="*/15")

        # Should be 0, 15, 30, 45
        assert schedule._minute == {0, 15, 30, 45}

    def test_parse_range(self):
        """Test parsing range."""
        schedule = CrontabSchedule(hour="9-17")

        # Should be 9, 10, 11, ... 17
        assert schedule._hour == {9, 10, 11, 12, 13, 14, 15, 16, 17}

    def test_parse_list(self):
        """Test parsing comma-separated list."""
        schedule = CrontabSchedule(hour="6,12,18")

        assert schedule._hour == {6, 12, 18}

    def test_matches_current_time(self):
        """Test matching current time."""
        now = datetime.utcnow()

        # Create schedule matching current minute and hour
        schedule = CrontabSchedule(
            minute=str(now.minute),
            hour=str(now.hour),
        )

        # Should match
        assert schedule._matches(now) is True

    def test_does_not_match_different_time(self):
        """Test not matching different time."""
        now = datetime.utcnow()

        # Create schedule for different hour
        different_hour = (now.hour + 1) % 24
        schedule = CrontabSchedule(hour=str(different_hour))

        # Should not match
        assert schedule._matches(now) is False

    def test_is_due_matching_time(self):
        """Test is_due when time matches."""
        now = datetime.utcnow()

        schedule = CrontabSchedule(
            minute=str(now.minute),
            hour=str(now.hour),
        )

        is_due, next_run = schedule.is_due(last_run=None)

        assert is_due is True
        assert next_run == 60.0

    def test_is_due_not_matching_time(self):
        """Test is_due when time doesn't match."""
        now = datetime.utcnow()

        # Schedule for different minute
        different_minute = (now.minute + 1) % 60
        schedule = CrontabSchedule(minute=str(different_minute))

        is_due, next_run = schedule.is_due(last_run=None)

        assert is_due is False
        assert next_run == 60.0

    def test_is_due_already_ran_this_minute(self):
        """Test is_due when already ran this minute."""
        now = datetime.utcnow()

        schedule = CrontabSchedule(
            minute=str(now.minute),
            hour=str(now.hour),
        )

        # Simulate already ran this minute
        last_run = now

        is_due, _next_run = schedule.is_due(last_run=last_run)

        assert is_due is False

    def test_crontab_helper_function(self):
        """Test crontab() helper function."""
        schedule = crontab(hour="9", minute="30")

        assert isinstance(schedule, CrontabSchedule)
        assert schedule.hour == "9"
        assert schedule.minute == "30"

    def test_crontab_every_15_minutes(self):
        """Test crontab for every 15 minutes."""
        schedule = crontab(minute="*/15")

        assert schedule._minute == {0, 15, 30, 45}

    def test_crontab_weekday_at_9am(self):
        """Test crontab for weekday at 9am."""
        schedule = crontab(hour="9", minute="0", day_of_week="1-5")

        assert schedule._hour == {9}
        assert schedule._minute == {0}
        assert schedule._day_of_week == {1, 2, 3, 4, 5}


class TestPeriodicTask:
    """Test PeriodicTask class."""

    def test_create_periodic_task(self):
        """Test creating a periodic task."""
        schedule = every(hours=1)
        task = PeriodicTask(
            name="test_task",
            schedule=schedule,
            task="my_task",
        )

        assert task.name == "test_task"
        assert task.schedule is schedule
        assert task.task == "my_task"
        assert task.enabled is True
        assert task.total_runs == 0

    def test_periodic_task_with_args(self):
        """Test periodic task with arguments."""
        task = PeriodicTask(
            name="task_with_args",
            schedule=every(minutes=5),
            task="process",
            args=(1, 2),
            kwargs={"key": "value"},
        )

        assert task.args == (1, 2)
        assert task.kwargs == {"key": "value"}

    def test_is_due_enabled_task(self):
        """Test is_due for enabled task."""
        task = PeriodicTask(
            name="enabled",
            schedule=every(seconds=10),
            task="task",
            enabled=True,
        )

        is_due, _next_run = task.is_due()

        assert is_due is True

    def test_is_due_disabled_task(self):
        """Test is_due for disabled task."""
        task = PeriodicTask(
            name="disabled",
            schedule=every(seconds=10),
            task="task",
            enabled=False,
        )

        is_due, next_run = task.is_due()

        assert is_due is False
        assert next_run == 0

    def test_mark_run(self):
        """Test marking task as run."""
        task = PeriodicTask(
            name="mark_test",
            schedule=every(minutes=1),
            task="task",
        )

        assert task.last_run is None
        assert task.total_runs == 0

        task.mark_run()

        assert task.last_run is not None
        assert task.total_runs == 1

        task.mark_run()

        assert task.total_runs == 2


@pytest.mark.asyncio()
class TestPeriodicScheduler:
    """Test PeriodicScheduler class."""

    async def test_create_scheduler(self):
        """Test creating a scheduler."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")
        scheduler = PeriodicScheduler(app)

        assert scheduler.app is app
        assert len(scheduler._tasks) == 0
        assert scheduler._running is False

    async def test_add_task(self):
        """Test adding a periodic task."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")
        scheduler = PeriodicScheduler(app)

        task = scheduler.add_task(
            name="test_task",
            schedule=every(minutes=5),
            task="my_task",
        )

        assert task.name == "test_task"
        assert "test_task" in scheduler._tasks
        assert scheduler.get_task("test_task") is task

    async def test_remove_task(self):
        """Test removing a periodic task."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")
        scheduler = PeriodicScheduler(app)

        scheduler.add_task("remove_me", every(hours=1), "task")

        removed = scheduler.remove_task("remove_me")

        assert removed is True
        assert scheduler.get_task("remove_me") is None

    async def test_remove_nonexistent_task(self):
        """Test removing non-existent task."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")
        scheduler = PeriodicScheduler(app)

        removed = scheduler.remove_task("nonexistent")

        assert removed is False

    async def test_list_tasks(self):
        """Test listing all tasks."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")
        scheduler = PeriodicScheduler(app)

        scheduler.add_task("task1", every(minutes=5), "task1")
        scheduler.add_task("task2", every(hours=1), "task2")
        scheduler.add_task("task3", crontab(hour="9"), "task3")

        tasks = scheduler.list_tasks()

        assert len(tasks) == 3
        assert {t.name for t in tasks} == {"task1", "task2", "task3"}

    async def test_start_and_stop_scheduler(self):
        """Test starting and stopping scheduler."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")
        scheduler = PeriodicScheduler(app)

        await scheduler.start()
        assert scheduler._running is True

        await asyncio.sleep(0.1)  # Let it run briefly

        await scheduler.stop()
        assert scheduler._running is False

    async def test_scheduler_executes_due_tasks(self):
        """Test that scheduler executes due tasks."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")

        execution_count = {"count": 0}

        @app.task()
        async def test_task():
            execution_count["count"] += 1
            return "done"

        # Add task that runs every second
        app.add_periodic_task(
            name="frequent",
            schedule=every(seconds=1),
            task="test_task",
        )

        # Start scheduler
        await app.start_scheduler()

        # Wait for 2.5 seconds
        await asyncio.sleep(2.5)

        # Stop scheduler
        await app.stop_scheduler()

        # Should have run at least 2 times
        assert execution_count["count"] >= 2

    async def test_disabled_task_not_executed(self):
        """Test that disabled tasks are not executed."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")

        execution_count = {"count": 0}

        @app.task()
        async def disabled_task():
            execution_count["count"] += 1

        # Add disabled task
        app.add_periodic_task(
            name="disabled",
            schedule=every(seconds=1),
            task="disabled_task",
            enabled=False,
        )

        await app.start_scheduler()
        await asyncio.sleep(2)
        await app.stop_scheduler()

        # Should not have run
        assert execution_count["count"] == 0

    async def test_task_with_arguments(self):
        """Test periodic task with arguments."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")

        received_args = {"args": None, "kwargs": None}

        @app.task()
        async def task_with_params(*args, **kwargs):
            received_args["args"] = args
            received_args["kwargs"] = kwargs

        app.add_periodic_task(
            name="parameterized",
            schedule=every(seconds=1),
            task="task_with_params",
            args=(1, 2, 3),
            kwargs={"key": "value"},
        )

        app.run()  # Start worker
        await app.start_scheduler()
        await asyncio.sleep(1.5)
        await app.stop_scheduler()
        app.stop()

        # Verify arguments were passed
        assert received_args["args"] == (1, 2, 3)
        assert received_args["kwargs"] == {"key": "value"}


@pytest.mark.asyncio()
class TestPeriodicEdgeCases:
    """Test edge cases for periodic tasks."""

    async def test_very_short_interval(self):
        """Test with very short interval."""
        schedule = IntervalSchedule(seconds=0.1)

        is_due, next_run = schedule.is_due(last_run=None)

        assert is_due is True
        assert next_run == 0.1

    async def test_crontab_boundary_values(self):
        """Test crontab with boundary values."""
        schedule = CrontabSchedule(
            minute="0",
            hour="0",
            day_of_month="1",
            month="1",
        )

        assert 0 in schedule._minute
        assert 0 in schedule._hour
        assert 1 in schedule._day_of_month
        assert 1 in schedule._month

    async def test_multiple_schedulers_same_app(self):
        """Test creating multiple schedulers for same app."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")

        scheduler1 = PeriodicScheduler(app)
        scheduler2 = PeriodicScheduler(app)

        scheduler1.add_task("task1", every(minutes=1), "task1")
        scheduler2.add_task("task2", every(minutes=1), "task2")

        # Each scheduler has its own tasks
        assert len(scheduler1.list_tasks()) == 1
        assert len(scheduler2.list_tasks()) == 1

    async def test_task_execution_during_scheduler_stop(self):
        """Test behavior when stopping scheduler during execution."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")

        async def long_task():
            await asyncio.sleep(5)

        app.add_periodic_task("long", every(seconds=1), long_task)

        await app.start_scheduler()
        await asyncio.sleep(0.5)
        await app.stop_scheduler()  # Should cancel cleanly

        # Should complete without errors


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
