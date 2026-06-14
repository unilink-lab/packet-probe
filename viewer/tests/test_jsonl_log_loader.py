from packet_probe_viewer.jsonl_log_loader import load_packet_probe_jsonl

def test_load_metadata_and_event(tmp_path):
    path = tmp_path / "capture.jsonl"
    path.write_text(
        '{"type":"metadata","schema":"packet-probe.log.v1","event_schema":"packet-probe.event.v1"}\n'
        '{"seq":1,"type":"raw_bytes","payload_hex":"0210"}\n',
        encoding="utf-8",
    )

    result = load_packet_probe_jsonl(path)

    assert result.metadata is not None
    assert result.metadata["schema"] == "packet-probe.log.v1"
    assert len(result.events) == 1
    assert result.events[0]["seq"] == 1
    assert result.malformed_lines == []

def test_load_malformed_lines(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text(
        '{"type":"metadata"}\n'
        'not-json\n'
        '[1,2,3]\n'
        '{"seq":1,"type":"raw_bytes"}\n',
        encoding="utf-8",
    )

    result = load_packet_probe_jsonl(path)

    assert len(result.events) == 1
    assert len(result.malformed_lines) == 2
    assert result.malformed_lines[0][0] == 2
    assert result.malformed_lines[1][0] == 3

def test_load_empty_lines(tmp_path):
    path = tmp_path / "empty_lines.jsonl"
    path.write_text(
        '\n'
        '{"seq":1,"type":"raw_bytes"}\n'
        '\n'
        '{"seq":2,"type":"raw_bytes"}\n'
        '\n',
        encoding="utf-8",
    )

    result = load_packet_probe_jsonl(path)

    assert len(result.events) == 2
    assert result.events[0]["seq"] == 1
    assert result.events[1]["seq"] == 2
    assert result.malformed_lines == []

def test_load_event_only_no_metadata(tmp_path):
    path = tmp_path / "no_meta.jsonl"
    path.write_text(
        '{"seq":1,"type":"raw_bytes"}\n',
        encoding="utf-8",
    )

    result = load_packet_probe_jsonl(path)

    assert result.metadata is None
    assert len(result.events) == 1
    assert result.events[0]["seq"] == 1
    assert result.malformed_lines == []

def test_load_multiple_metadata_lines(tmp_path):
    path = tmp_path / "multi_meta.jsonl"
    path.write_text(
        '{"type":"metadata","version":"0.1.0"}\n'
        '{"seq":1,"type":"raw_bytes"}\n'
        '{"type":"metadata","version":"0.2.0"}\n',
        encoding="utf-8",
    )

    result = load_packet_probe_jsonl(path)

    # Initial metadata is retained, others ignored
    assert result.metadata is not None
    assert result.metadata["version"] == "0.1.0"
    assert len(result.events) == 1
    assert result.events[0]["seq"] == 1
    assert result.malformed_lines == []
