"""NeuroSky ThinkGear parser — validated without any hardware."""

from amun.thinkgear import (
    ThinkGearParser, build_packet, checksum,
    CODE_ATTENTION, CODE_MEDITATION, CODE_POOR_SIGNAL,
)


def test_checksum_matches_spec():
    payload = bytes([CODE_ATTENTION, 57])
    assert checksum(payload) == (~(sum(payload) & 0xFF)) & 0xFF


def test_parse_single_attention_packet():
    pkt = build_packet([(CODE_ATTENTION, 72)])
    out = ThinkGearParser().feed(pkt)
    assert out == [{"attention": 72}]


def test_parse_multiple_codes_one_packet():
    pkt = build_packet([(CODE_POOR_SIGNAL, 0), (CODE_ATTENTION, 80),
                        (CODE_MEDITATION, 40)])
    out = ThinkGearParser().feed(pkt)
    assert out == [{"poor_signal": 0, "attention": 80, "meditation": 40}]


def test_split_across_feeds():
    pkt = build_packet([(CODE_ATTENTION, 50)])
    p = ThinkGearParser()
    assert p.feed(pkt[:2]) == []        # only sync so far
    assert p.feed(pkt[2:]) == [{"attention": 50}]


def test_bad_checksum_is_dropped():
    pkt = bytearray(build_packet([(CODE_ATTENTION, 50)]))
    pkt[-1] ^= 0xFF                      # corrupt checksum
    assert ThinkGearParser().feed(bytes(pkt)) == []


def test_resyncs_after_garbage():
    pkt = build_packet([(CODE_ATTENTION, 99)])
    stream = b"\x00\x11garbage" + pkt
    out = ThinkGearParser().feed(stream)
    assert out == [{"attention": 99}]


def test_two_packets_in_stream():
    s = build_packet([(CODE_ATTENTION, 10)]) + build_packet([(CODE_ATTENTION, 90)])
    out = ThinkGearParser().feed(s)
    assert out == [{"attention": 10}, {"attention": 90}]


def test_multibyte_code_is_skipped_cleanly():
    # 0x80 raw-wave row (length 2) followed by an attention row in same payload
    payload = bytes([0x80, 0x02, 0x12, 0x34, CODE_ATTENTION, 65])
    pkt = bytes([0xAA, 0xAA, len(payload)]) + payload + bytes([checksum(payload)])
    out = ThinkGearParser().feed(pkt)
    assert out == [{"attention": 65}]
