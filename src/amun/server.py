"""Server — stdlib HTTP + a hand-rolled RFC 6455 WebSocket. No dependencies.

The browser opens the page, captures the microphone with the Web Audio API, and
streams a loudness value per frame over the WebSocket. The server runs the real
pipeline (preprocessing -> classify -> engine) and streams game state back at
~60 Hz. Nothing but the Python standard library is used here — the WebSocket is
implemented from scratch, which keeps the project genuinely zero-dependency and
fully offline.

Also exposes :func:`run_headless` for running the engine with a non-browser
breath source (sim / replay / mic) — handy for CI and the demo renderer.
"""

from __future__ import annotations

import base64
import hashlib
import json
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from .calibrate import DEFAULT_PROFILE_PATH, calibrate_from_samples, load_or_default
from .classify import BreathClassifier
from .engine import GameEngine
from .preprocessing import BreathEnvelope

PKG = Path(__file__).resolve().parent
TEMPLATES = PKG / "templates"
# Repo-level assets are served in dev if present; absent in an installed wheel
# (the UI is self-contained, so this route simply 404s gracefully).
ASSETS = PKG.parents[1] / "assets"

WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"  # RFC 6455 GUID
TICK_HZ = 60.0


# ── WebSocket frame helpers (testable, no I/O) ────────────────────────────────
def compute_accept(key: str) -> str:
    """Sec-WebSocket-Accept for a given client Sec-WebSocket-Key (RFC 6455)."""
    digest = hashlib.sha1((key + WS_MAGIC).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def encode_frame(payload: bytes, opcode: int = 0x1) -> bytes:
    """Encode a single un-fragmented, unmasked server frame (text by default)."""
    header = bytearray([0x80 | opcode])  # FIN + opcode
    n = len(payload)
    if n < 126:
        header.append(n)
    elif n < 65536:
        header.append(126)
        header += struct.pack(">H", n)
    else:
        header.append(127)
        header += struct.pack(">Q", n)
    return bytes(header) + payload


def decode_frame(data: bytes):
    """Decode one client frame from ``data``.

    Returns ``(opcode, payload, total_bytes_consumed)`` or ``None`` if a complete
    frame is not yet available. Handles client masking (mandatory per spec).
    """
    if len(data) < 2:
        return None
    b0, b1 = data[0], data[1]
    opcode = b0 & 0x0F
    masked = bool(b1 & 0x80)
    length = b1 & 0x7F
    idx = 2
    if length == 126:
        if len(data) < idx + 2:
            return None
        length = struct.unpack(">H", data[idx:idx + 2])[0]
        idx += 2
    elif length == 127:
        if len(data) < idx + 8:
            return None
        length = struct.unpack(">Q", data[idx:idx + 8])[0]
        idx += 8
    mask = b""
    if masked:
        if len(data) < idx + 4:
            return None
        mask = data[idx:idx + 4]
        idx += 4
    if len(data) < idx + length:
        return None
    payload = bytearray(data[idx:idx + length])
    if masked:
        for i in range(length):
            payload[i] ^= mask[i % 4]
    return opcode, bytes(payload), idx + length


# ── shared per-connection state ───────────────────────────────────────────────
class _Session:
    """Pipeline state for one connected player."""

    def __init__(self, profile, seed: int = 0):
        self.lock = threading.Lock()
        self.raw_breath = 0.0
        self.engine = GameEngine(seed=seed)
        self.env = BreathEnvelope()
        self.clf = BreathClassifier(profile)
        self.running = True
        self.outbox = []  # out-of-band messages flushed by the main loop

    def set_breath(self, raw: float) -> None:
        with self.lock:
            self.raw_breath = max(0.0, float(raw))

    def reset(self) -> None:
        with self.lock:
            self.engine.reset()
            self.env.reset()

    def recalibrate(self, samples) -> dict:
        profile = calibrate_from_samples(samples, save_to=DEFAULT_PROFILE_PATH)
        with self.lock:
            self.clf = BreathClassifier(profile)
            self.outbox.append({"type": "calibrated", "profile": profile.__dict__})
        return profile.__dict__

    def drain_outbox(self) -> list:
        with self.lock:
            out, self.outbox = self.outbox, []
        return out

    def tick(self, dt: float) -> dict:
        with self.lock:
            smoothed = self.env.update(self.raw_breath)
            self.engine.set_breath(self.clf.lift(smoothed))
            self.engine.update(dt)
            state = self.engine.state()
        state["type"] = "state"
        state["lift"] = round(smoothed, 4)
        return state


# ── HTTP + WebSocket handler ──────────────────────────────────────────────────
class _Handler(BaseHTTPRequestHandler):
    server_version = "Amun/1.0"
    profile = None  # set by run_server

    def log_message(self, *args):  # silence default logging
        pass

    # static
    def do_GET(self):
        if self.headers.get("Upgrade", "").lower() == "websocket":
            return self._serve_ws()
        if self.path in ("/", "/index.html"):
            return self._send_file(TEMPLATES / "index.html", "text/html")
        if self.path == "/health":
            body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/assets/"):
            name = self.path[len("/assets/"):].split("?")[0]
            target = (ASSETS / name).resolve()
            if str(target).startswith(str(ASSETS.resolve())) and target.is_file():
                return self._send_file(target, _guess_type(target))
        self.send_error(404, "Not found")

    def _send_file(self, path: Path, ctype: str):
        if not path.is_file():
            return self.send_error(404, "Not found")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # websocket upgrade + game loop
    def _serve_ws(self):
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            return self.send_error(400, "Missing Sec-WebSocket-Key")
        accept = compute_accept(key)
        self.wfile.write(
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Accept: " + accept.encode("ascii") + b"\r\n\r\n"
        )
        self.wfile.flush()

        sock = self.connection
        session = _Session(self.profile, seed=int(time.time()) & 0xFFFF)

        reader = threading.Thread(target=self._reader, args=(sock, session), daemon=True)
        reader.start()

        last = time.monotonic()
        dt_target = 1.0 / TICK_HZ
        try:
            while session.running:
                now = time.monotonic()
                dt = now - last
                last = now
                for extra in session.drain_outbox():
                    sock.sendall(encode_frame(json.dumps(extra).encode("utf-8")))
                state = session.tick(dt)
                sock.sendall(encode_frame(json.dumps(state).encode("utf-8")))
                sleep = dt_target - (time.monotonic() - now)
                if sleep > 0:
                    time.sleep(sleep)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            session.running = False

    def _reader(self, sock, session: _Session):
        buf = bytearray()
        try:
            while session.running:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while True:
                    result = decode_frame(bytes(buf))
                    if result is None:
                        break
                    opcode, payload, consumed = result
                    del buf[:consumed]
                    if opcode == 0x8:  # close
                        session.running = False
                        break
                    if opcode in (0x1, 0x2):
                        self._handle_message(payload, session)
        except (ConnectionResetError, OSError):
            pass
        finally:
            session.running = False

    def _handle_message(self, payload: bytes, session: _Session):
        try:
            msg = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return
        kind = msg.get("type")
        if kind == "breath":
            session.set_breath(msg.get("rms", 0.0))
        elif kind == "reset":
            session.reset()
        elif kind == "calibrate":
            session.recalibrate(msg.get("samples") or [])


def run_server(host: str = "127.0.0.1", port: int = 8011,
               profile=None, open_browser: bool = False) -> ThreadingHTTPServer:
    """Start the HTTP/WebSocket server. Returns the server (call shutdown())."""
    _Handler.profile = profile or load_or_default()
    httpd = ThreadingHTTPServer((host, port), _Handler)
    if open_browser:
        import webbrowser

        threading.Timer(
            0.6, lambda: webbrowser.open(f"http://{host}:{httpd.server_address[1]}/")
        ).start()
    return httpd


# ── headless runner (no browser) ──────────────────────────────────────────────
def run_headless(source, profile=None, duration: Optional[float] = None,
                 quiet: bool = False, already_started: bool = False) -> dict:
    """Run the engine driven by a :class:`~amun.ingestion.BreathSource`.

    Returns the final game state. Used by CI and the demo renderer; never blocks
    on input. Pass ``already_started=True`` if the caller already started the
    source (e.g. to detect hardware availability before falling back to the mic).
    """
    profile = profile or load_or_default()
    engine = GameEngine(seed=1)
    env = BreathEnvelope()
    clf = BreathClassifier(profile)
    if not already_started:
        source.start()
    start = time.monotonic()
    last = start
    dt_target = 1.0 / TICK_HZ
    try:
        while True:
            now = time.monotonic()
            dt = now - last
            last = now
            smoothed = env.update(source.read())
            engine.set_breath(clf.lift(smoothed))
            engine.update(dt)
            if not quiet and int(now * 4) % 4 == 0:
                print(
                    f"\r  alt={engine.falcon_y:5.1f}  breath={engine.breath:.2f}  "
                    f"score={engine.score:5d}  {'ALIVE' if engine.alive else 'DOWN '}",
                    end="", flush=True,
                )
            if duration is not None and now - start >= duration:
                break
            if not engine.alive:
                engine.reset()
                env.reset()
                if duration is None:
                    break
            sleep = dt_target - (time.monotonic() - now)
            if sleep > 0:
                time.sleep(sleep)
    finally:
        source.close()
        if not quiet:
            print()
    return engine.state()


def _guess_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp",
        ".css": "text/css", ".js": "application/javascript",
        ".html": "text/html", ".json": "application/json",
    }.get(ext, "application/octet-stream")
