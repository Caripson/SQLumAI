import asyncio
import os
import uvicorn


async def run_api(stop_event: asyncio.Event):
    try:
        from src.version import __version__
    except Exception:
        __version__ = "0.0.0"
    print(f"[sqlumai] API server starting (version {__version__})")
    config = uvicorn.Config("src.api:app", host=os.getenv("API_HOST", "0.0.0.0"), port=int(os.getenv("API_PORT", "8080")), log_level="info")
    server = uvicorn.Server(config)

    async def _serve():
        await server.serve()

    task = asyncio.create_task(_serve())
    await stop_event.wait()
    if server.should_exit is False:
        server.should_exit = True
    await task
