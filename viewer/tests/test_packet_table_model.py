from PySide6.QtCore import Qt
from packet_probe_viewer.packet_table_model import PacketFilterProxyModel, PacketTableModel
from packet_probe_viewer.event_model import PacketEvent

def test_table_model_basic():
    model = PacketTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 8

    # Append an event
    event = PacketEvent({
        "seq": 1,
        "parent_seqs": [42],
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
    assert model.headerData(1, Qt.Orientation.Horizontal) == "Parent Seq(s)"

    # Check data retrieval
    idx = model.index(0, 0)
    assert model.data(idx) == "42.1"
    idx_parent = model.index(0, 1)
    assert model.data(idx_parent) == "42"
    idx_summary = model.index(0, 7)
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


def _make_proxy():
    model = PacketTableModel()
    model.set_events([
        PacketEvent({"seq": 1, "direction": "app_to_device", "type": "raw_bytes", "summary": "ping", "payload_hex": "AABB"}),
        PacketEvent({"seq": 2, "direction": "device_to_app", "type": "raw_bytes", "summary": "pong", "payload_hex": "CCDD"}),
        PacketEvent({"seq": 3, "direction": "device_to_app", "type": "error", "summary": "boom", "payload_hex": ""}),
    ])
    proxy = PacketFilterProxyModel()
    proxy.setSourceModel(model)
    return model, proxy


def test_filter_proxy_no_filter_shows_all():
    _, proxy = _make_proxy()
    assert proxy.rowCount() == 3


def test_filter_proxy_direction_filter():
    _, proxy = _make_proxy()
    proxy.set_direction_filter("app_to_device")
    assert proxy.rowCount() == 1
    assert proxy.data(proxy.index(0, 7)) == "ping"


def test_filter_proxy_type_filter():
    _, proxy = _make_proxy()
    proxy.set_type_filter("error")
    assert proxy.rowCount() == 1
    assert proxy.data(proxy.index(0, 7)) == "boom"


def test_filter_proxy_text_filter_matches_summary_and_hex():
    _, proxy = _make_proxy()
    proxy.set_text_filter("pong")
    assert proxy.rowCount() == 1

    proxy.set_text_filter("aabb")
    assert proxy.rowCount() == 1
    assert proxy.data(proxy.index(0, 7)) == "ping"


def test_filter_proxy_combines_filters():
    _, proxy = _make_proxy()
    proxy.set_direction_filter("device_to_app")
    proxy.set_type_filter("raw_bytes")
    assert proxy.rowCount() == 1
    assert proxy.data(proxy.index(0, 7)) == "pong"


def test_filter_proxy_clears_back_to_all():
    _, proxy = _make_proxy()
    proxy.set_text_filter("pong")
    assert proxy.rowCount() == 1
    proxy.set_text_filter("")
    assert proxy.rowCount() == 3
