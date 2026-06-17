from packet_probe_viewer.event_model import PacketEvent, format_time_ns

def test_packet_event_fields():
    event = PacketEvent({
        "seq": 1,
        "time_ns": 1781234567890,
        "session": "udp-1",
        "transport": "udp",
        "direction": "device_to_app",
        "type": "raw_bytes",
        "size": 6,
        "payload_hex": "0210010003A7",
        "summary": "DEVICE -> APP 6 bytes",
    })

    assert event.seq == 1
    assert event.transport == "udp"
    assert event.direction == "device_to_app"
    assert event.payload_hex == "0210010003A7"
    assert event.summary == "DEVICE -> APP 6 bytes"
    assert event.time_ns == 1781234567890
    assert event.session == "udp-1"
    assert event.type == "raw_bytes"
    assert event.size == 6

def test_packet_event_missing_fields():
    event = PacketEvent({})
    assert event.seq == 0
    assert event.parent_seq == 0
    assert event.parent_seqs == []
    assert event.time_ns == 0
    assert event.session == ""
    assert event.transport == ""
    assert event.direction == ""
    assert event.type == ""
    assert event.size == 0
    assert event.payload_hex == ""
    assert event.summary == ""

def test_parent_seqs_fallback():
    # Case 1: Both parent_seq and parent_seqs are missing
    assert PacketEvent({}).parent_seqs == []

    # Case 2: parent_seq is present, parent_seqs is missing (fallback)
    assert PacketEvent({"parent_seq": 42}).parent_seqs == [42]

    # Case 3: Both are present
    assert PacketEvent({"parent_seq": 42, "parent_seqs": [41, 42]}).parent_seqs == [41, 42]

    # Case 4: parent_seqs is empty array, but parent_seq is present (fallback)
    assert PacketEvent({"parent_seq": 42, "parent_seqs": []}).parent_seqs == [42]

def test_format_time_ns_zero():
    assert format_time_ns(0) == "00:00:00.000000"
