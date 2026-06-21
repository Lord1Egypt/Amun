"""Hand-rolled RFC 6455 WebSocket: handshake + frame codec."""

import json

from amun.server import compute_accept, encode_frame, decode_frame


def mask_client_frame(payload: bytes, opcode: int = 0x1,
                      mask=b"\x12\x34\x56\x78") -> bytes:
    """Build a masked *client* frame (what a browser sends)."""
    header = bytearray([0x80 | opcode])
    n = len(payload)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header += n.to_bytes(2, "big")
    else:
        header.append(0x80 | 127)
        header += n.to_bytes(8, "big")
    header += mask
    masked = bytes(payload[i] ^ mask[i % 4] for i in range(n))
    return bytes(header) + masked


def test_handshake_rfc6455_vector():
    # The canonical example from RFC 6455 §1.3.
    assert compute_accept("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="


def test_encode_small_frame_header():
    frame = encode_frame(b"hi")
    assert frame[0] == 0x81           # FIN + text
    assert frame[1] == 2              # unmasked length 2
    assert frame[2:] == b"hi"


def test_encode_extended_16bit_length():
    payload = b"x" * 200
    frame = encode_frame(payload)
    assert frame[1] == 126
    assert int.from_bytes(frame[2:4], "big") == 200


def test_decode_masked_client_frame():
    msg = json.dumps({"type": "breath", "rms": 0.12}).encode()
    frame = mask_client_frame(msg)
    opcode, payload, consumed = decode_frame(frame)
    assert opcode == 0x1
    assert json.loads(payload)["rms"] == 0.12
    assert consumed == len(frame)


def test_decode_incomplete_returns_none():
    frame = mask_client_frame(b"hello world")
    assert decode_frame(frame[:3]) is None   # not enough bytes yet


def test_roundtrip_server_then_decode_unmasked():
    payload = b'{"type":"state"}'
    frame = encode_frame(payload)
    opcode, got, consumed = decode_frame(frame)
    assert opcode == 0x1 and got == payload and consumed == len(frame)


def test_decode_handles_extended_length_masked():
    payload = b"z" * 500
    opcode, got, _ = decode_frame(mask_client_frame(payload))
    assert got == payload


def test_decode_close_opcode():
    frame = mask_client_frame(b"", opcode=0x8)
    opcode, _, _ = decode_frame(frame)
    assert opcode == 0x8
