"""NeuroSky ThinkGear protocol parser — pure standard library.

Lets Amun *optionally* take a signal from a NeuroSky MindWave headset (real EEG),
bringing the original "drive with your brain" idea back as a bonus mode. The
MindWave Mobile pairs over Bluetooth as a serial port and streams ThinkGear
packets; this module decodes them without any hardware so it can be unit-tested.

Packet format (ThinkGear serial stream):

    0xAA 0xAA  <plength>  <payload[plength]>  <checksum>

Payload is a sequence of (code, value) data rows. We care about the small-payload
codes used for control:

    0x02  POOR_SIGNAL   (0 = great contact, 200 = off head)
    0x04  ATTENTION     (0..100)   ← used as the "brain throttle"
    0x05  MEDITATION    (0..100)

``checksum = (~(sum(payload) & 0xFF)) & 0xFF``.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

SYNC = 0xAA
CODE_POOR_SIGNAL = 0x02
CODE_ATTENTION = 0x04
CODE_MEDITATION = 0x05
CODE_RAW = 0x80  # multi-byte; skipped for control but parsed correctly


def checksum(payload: bytes) -> int:
    return (~(sum(payload) & 0xFF)) & 0xFF


def build_packet(rows: List[Tuple[int, int]]) -> bytes:
    """Build a ThinkGear packet from (code, value) rows. Used by tests/sim."""
    payload = bytearray()
    for code, value in rows:
        payload.append(code)
        payload.append(value & 0xFF)
    return bytes([SYNC, SYNC, len(payload)]) + bytes(payload) + bytes([checksum(payload)])


def _parse_payload(payload: bytes) -> Dict[str, int]:
    """Decode one validated payload into a dict of named readings."""
    out: Dict[str, int] = {}
    i = 0
    n = len(payload)
    while i < n:
        code = payload[i]
        i += 1
        if code >= 0x80:  # multi-byte value: next byte is length
            if i >= n:
                break
            length = payload[i]
            i += 1 + length  # skip raw/eeg-power blobs
            continue
        if i >= n:
            break
        value = payload[i]
        i += 1
        if code == CODE_POOR_SIGNAL:
            out["poor_signal"] = value
        elif code == CODE_ATTENTION:
            out["attention"] = value
        elif code == CODE_MEDITATION:
            out["meditation"] = value
    return out


class ThinkGearParser:
    """Stateful byte-stream parser. Feed bytes, get decoded reading dicts."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> List[Dict[str, int]]:
        """Append ``data`` and return every complete, valid packet decoded."""
        self._buf += data
        results: List[Dict[str, int]] = []
        while True:
            # find sync 0xAA 0xAA
            start = self._buf.find(b"\xaa\xaa")
            if start < 0:
                # keep only a trailing partial sync byte
                self._buf = self._buf[-1:] if self._buf[-1:] == b"\xaa" else bytearray()
                break
            if start:
                del self._buf[:start]
            if len(self._buf) < 4:
                break
            plength = self._buf[2]
            if plength > 169:  # invalid per spec; drop the sync and resync
                del self._buf[:2]
                continue
            total = 3 + plength + 1
            if len(self._buf) < total:
                break  # wait for more bytes
            payload = bytes(self._buf[3:3 + plength])
            recv_ck = self._buf[3 + plength]
            del self._buf[:total]
            if checksum(payload) == recv_ck:
                reading = _parse_payload(payload)
                if reading:
                    results.append(reading)
        return results
