import asyncio
import os
import signal
from dotenv import load_dotenv

from src.proxy.tds_proxy import run_proxy
from src.proxy.tds_tls import run_tls_terminating_proxy
from src.runtime.api_runner import run_api
from src.runtime.scheduler import run_scheduler


async def main() -> None:
    load_dotenv()
    listen_host = os.getenv("PROXY_LISTEN_ADDR", "0.0.0.0")
    listen_port = int(os.getenv("PROXY_LISTEN_PORT", "61433"))
    sql_host = os.getenv("SQL_HOST", "localhost")
    sql_port = int(os.getenv("SQL_PORT", "1433"))
    enable_api = os.getenv("ENABLE_API", "true").lower() == "true"
    enable_scheduler = os.getenv("ENABLE_SCHEDULER", "false").lower() == "true"

    stop_event = asyncio.Event()

    def _handle_sig(*_):
        stop_event.set()

    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, _handle_sig)
        except NotImplementedError:
            # Signals not available (e.g., on Windows inside some environments)
            pass

    tls_term = os.getenv("TLS_TERMINATION", "false").lower() == "true"
    if tls_term:
        proxy_task = asyncio.create_task(
            run_tls_terminating_proxy(listen_host, listen_port, sql_host, sql_port, stop_event)
        )
    else:
        proxy_task = asyncio.create_task(
            run_proxy(listen_host, listen_port, sql_host, sql_port, stop_event)
        )
    tasks = [proxy_task]

    if enable_api:
        tasks.append(asyncio.create_task(run_api(stop_event)))
    if enable_scheduler:
        tasks.append(asyncio.create_task(run_scheduler(stop_event)))

    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    stop_event.set()
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
