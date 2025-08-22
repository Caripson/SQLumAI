import asyncio
import logging


def test_run_job_paths(caplog):
    caplog.set_level(logging.INFO)
    from src.runtime.scheduler import _run_job

    async def go():
        # success
        def ok():
            return None
        await _run_job(ok, "ok")
        # SystemExit
        def se():
            raise SystemExit("bye")
        await _run_job(se, "se")
        # Exception
        def bad():
            raise ValueError("boom")
        await _run_job(bad, "bad")

    asyncio.run(go())
    text = "\n".join(t[2] for t in caplog.record_tuples)
    assert "start" in text and "done" in text and "exited" in text and "failed" in text

