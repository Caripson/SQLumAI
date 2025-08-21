import asyncio
import os
import logging

log = logging.getLogger("scheduler")


async def _run_job(fn, name: str):
    try:
        log.info(f"job {name}: start")
        fn()
        log.info(f"job {name}: done")
    except SystemExit as e:
        log.warning(f"job {name}: exited: {e}")
    except Exception as e:
        log.exception(f"job {name}: failed: {e}")


async def run_scheduler(stop_event: asyncio.Event):
    interval_sec = int(os.getenv("SCHEDULE_INTERVAL_SEC", "3600"))
    # Lazy imports to avoid heavy deps on startup
    from scripts.read_xevents import main as read_xevents
    from scripts.aggregate_profiles import main as aggregate_profiles
    from scripts.generate_daily_report import main as generate_report
    from scripts.publish_feedback import main as publish_feedback
    from scripts.generate_dryrun_report import main as dryrun_report
    from scripts.llm_summarize_profiles import main as llm_summary
    from scripts.llm_insights import main as llm_insights

    while not stop_event.is_set():
        await _run_job(read_xevents, "xevents")
        await _run_job(aggregate_profiles, "aggregate")
        await _run_job(generate_report, "report")
        await _run_job(dryrun_report, "dryrun_report")
        await _run_job(llm_summary, "llm_summary")
        await _run_job(llm_insights, "llm_insights")
        await _run_job(publish_feedback, "feedback")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_sec)
        except asyncio.TimeoutError:
            continue
