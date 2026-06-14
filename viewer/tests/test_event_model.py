from packet_probe_viewer.event_model import PacketEvent, format_time_ns

def test_packet_event():
    raw = {
        "seq": 10,
        "parent_seq": 1,
        "time_ns": 1781426521288393851,
        "session": "test-session",
        "transport": "tcp",
        "direction": "device_to_app",
        "type": "raw_bytes",
        "size": 6,
        "payload_hex": "0210010003A7",
        "summary": "RX 6 bytes"
    }
    event = PacketEvent(raw)
    assert event.seq == 10
    assert event.parent_seq == 1
    assert event.time_ns == 1781426521288393851
    assert event.session == "test-session"
    assert event.transport == "tcp"
    assert event.direction == "device_to_app"
    assert event.type == "raw_bytes"
    assert event.size == 6
    assert event.payload_hex == "0210010003A7"
    assert event.summary == "RX 6 bytes"

def test_format_time_ns():
    assert format_time_ns(0) == "00:00:00.000000"
    res = format_time_ns(1781426521288393851)
    assert len(res) == 15
