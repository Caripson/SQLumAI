import asyncio
import sys
import types


def test_run_scheduler_one_cycle(monkeypatch):
    # Create dummy modules with main functions
    calls = []
    def make_mod(name):
        m = types.SimpleNamespace()
        def main():
            calls.append(name)
        m.main = main
        return m
    for modname in (
        'scripts.read_xevents',
        'scripts.aggregate_profiles',
        'scripts.generate_daily_report',
        'scripts.publish_feedback',
        'scripts.generate_dryrun_report',
        'scripts.llm_summarize_profiles',
        'scripts.llm_insights',
    ):
        sys.modules[modname] = make_mod(modname)

    from src.runtime.scheduler import run_scheduler
    def run_once():
        async def _go():
            stop_event = asyncio.Event()
            async def stopper():
                await asyncio.sleep(0.01)
                stop_event.set()
            monkeypatch.setenv('SCHEDULE_INTERVAL_SEC', '1')
            t1 = asyncio.create_task(run_scheduler(stop_event))
            t2 = asyncio.create_task(stopper())
            await asyncio.gather(t1, t2)
        asyncio.run(_go())
    run_once()
    # Ensure at least some jobs executed
    assert any('aggregate_profiles' in x for x in calls) and any('generate_dryrun_report' in x for x in calls)
