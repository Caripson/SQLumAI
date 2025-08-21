import asyncio
import logging
import os
import ssl
from typing import Optional

logger = logging.getLogger("tds_tls")


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        while not reader.at_eof():
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def _handle_client(local_reader, local_writer, upstream_host, upstream_port):
    try:
        remote_reader, remote_writer = await asyncio.open_connection(upstream_host, upstream_port)
    except Exception as e:
        logger.error(f"upstream connect failed: {e}")
        local_writer.close()
        await local_writer.wait_closed()
        return
    c2s = asyncio.create_task(_pipe(local_reader, remote_writer))
    s2c = asyncio.create_task(_pipe(remote_reader, local_writer))
    await asyncio.wait([c2s, s2c], return_when=asyncio.FIRST_COMPLETED)
    for t in (c2s, s2c):
        t.cancel()
        try:
            await t
        except Exception:
            pass


async def run_tls_terminating_proxy(listen_host: str, listen_port: int, upstream_host: str, upstream_port: int, stop_event: Optional[asyncio.Event] = None):
    cert_path = os.getenv("TLS_CERT_PATH", "certs/dev-cert.pem")
    key_path = os.getenv("TLS_KEY_PATH", "certs/dev-key.pem")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
    except Exception as e:
        logger.error(f"Failed to load TLS cert/key: {e}")
        raise

    server = await asyncio.start_server(
        lambda r, w: _handle_client(r, w, upstream_host, upstream_port), listen_host, listen_port, ssl=ctx
    )
    sockets = ", ".join(str(s.getsockname()) for s in server.sockets or [])
    logger.info(f"TLS proxy listening on {sockets} -> {upstream_host}:{upstream_port}")
    async with server:
        if stop_event is None:
            await server.serve_forever()
        else:
            await stop_event.wait()
    logger.info("TLS proxy shutdown")

