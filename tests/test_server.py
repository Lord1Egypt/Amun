"""End-to-end server: boots, serves the page, upgrades a real WebSocket."""

import base64
import json
import os
import socket
import threading
import time
import urllib.request

import pytest

from amun.server import run_server, run_headless, compute_accept, decode_frame
from amun.ingestion import SimSource


@pytest.fixture
def server():
    httpd = run_server(host="127.0.0.1", port=0, open_browser=False)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    yield port
    httpd.shutdown()


def test_health_ok(server):
    with urllib.request.urlopen(f"http://127.0.0.1:{server}/health", timeout=3) as r:
        assert r.status == 200
        assert json.loads(r.read())["status"] == "ok"


def test_index_served(server):
    with urllib.request.urlopen(f"http://127.0.0.1:{server}/", timeout=3) as r:
        body = r.read().decode()
    assert r.status == 200
    assert "AMUN" in body and "WebSocket" in body


def test_websocket_upgrade_101_and_state(server):
    key = base64.b64encode(os.urandom(16)).decode()
    s = socket.create_connection(("127.0.0.1", server), timeout=3)
    s.sendall(
        f"GET /ws HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n".encode()
    )
    # read the handshake response (keeping any bytes that follow the header)
    resp = b""
    while b"\r\n\r\n" not in resp:
        resp += s.recv(256)
    head, _, rest = resp.partition(b"\r\n\r\n")
    head = head.decode(errors="replace")
    assert "101" in head.split("\r\n")[0]
    assert f"Sec-WebSocket-Accept: {compute_accept(key)}" in head

    # the server streams state frames; buffer until a complete one decodes
    s.settimeout(3)
    buf = bytearray(rest)
    msg = None
    for _ in range(120):
        frame = decode_frame(bytes(buf))
        if frame is not None:
            _, payload, consumed = frame
            del buf[:consumed]
            candidate = json.loads(payload)
            if candidate.get("type") == "state":
                msg = candidate
                break
        else:
            buf += s.recv(65536)
    assert msg is not None and "falcon" in msg
    s.close()


def test_run_headless_sim_terminates():
    final = run_headless(SimSource(), duration=0.4, quiet=True)
    assert "score" in final and final["score"] >= 0
