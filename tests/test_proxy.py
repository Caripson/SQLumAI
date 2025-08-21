import asyncio
import socket
import threading
import pytest

from src.proxy.tds_proxy import run_proxy


def _start_echo_server(host, port, stop_event: threading.Event):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except PermissionError:
        pytest.skip("Socket operations not permitted in sandbox")
    sock.bind((host, port))
    sock.listen(5)
    sock.settimeout(0.2)

    def loop():
        conns = []
        try:
            while not stop_event.is_set():
                try:
                    conn, _ = sock.accept()
                    conn.settimeout(0.2)
                    conns.append(conn)
                except socket.timeout:
                    pass
                for c in list(conns):
                    try:
                        data = c.recv(65536)
                        if data:
                            c.sendall(data)  # echo
                        else:
                            c.close()
                            conns.remove(c)
                    except socket.timeout:
                        pass
                    except OSError:
                        if c in conns:
                            conns.remove(c)
        finally:
            for c in conns:
                try:
                    c.close()
                except Exception:
                    pass
            sock.close()

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t


def test_proxy_passthrough():
    host = "127.0.0.1"
    upstream_port = 15333
    proxy_port = 16433

    # Start upstream echo server
    stop_flag = threading.Event()
    thread = _start_echo_server(host, upstream_port, stop_flag)

    async def run_and_check():
        stop = asyncio.Event()
        proxy_task = asyncio.create_task(run_proxy(host, proxy_port, host, upstream_port, stop))
        await asyncio.sleep(0.2)

        reader, writer = await asyncio.open_connection(host, proxy_port)
        msg = b"HELLO TDS"
        writer.write(msg)
        await writer.drain()
        data = await reader.read(len(msg))
        writer.close()
        await writer.wait_closed()

        stop.set()
        await proxy_task
        return data

    data = asyncio.run(run_and_check())
    stop_flag.set()
    thread.join(timeout=1)
    assert data == b"HELLO TDS"
