from PySide6.QtCore import Qt
from packet_probe_viewer.packet_table_model import PacketTableModel
from packet_probe_viewer.event_model import PacketEvent

def test_table_model_basic():
    model = PacketTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 7

    # Append an event
    event = PacketEvent({
        "seq": 1,
        "time_ns": 1000000000,
        "direction": "device_to_app",
        "type": "raw_bytes",
        "transport": "udp",
        "size": 5,
        "summary": "hello"
    })
    model.append_event(event)
    assert model.rowCount() == 1
    assert model.event_at(0) == event

    # Check header
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Seq"

    # Check data retrieval
    idx = model.index(0, 0)
    assert model.data(idx) == 1
    idx_summary = model.index(0, 6)
    assert model.data(idx_summary) == "hello"

def test_table_model_set_events():
    model = PacketTableModel()
    events = [
        PacketEvent({"seq": i, "summary": f"event {i}"})
        for i in range(10)
    ]
    model.set_events(events)
    assert model.rowCount() == 10
    assert model.event_at(0).seq == 0
    assert model.event_at(9).seq == 9

    # Clear
    model.clear()
    assert model.rowCount() == 0

def test_table_model_max_events():
    model = PacketTableModel()
    # Temporarily set MAX_EVENTS to 3 for testing
    model.MAX_EVENTS = 3

    events = [
        PacketEvent({"seq": i})
        for i in range(5)
    ]
    model.set_events(events)
    assert model.rowCount() == 3
    # Should keep the last 3 events
    assert model.event_at(0).seq == 2
    assert model.event_at(2).seq == 4

    # Test append_event rolling behavior
    model.append_event(PacketEvent({"seq": 5}))
    assert model.rowCount() == 3
    assert model.event_at(0).seq == 3
    assert model.event_at(2).seq == 5
