from packet_probe_viewer.widgets.hex_view import format_hex_dump

def test_format_hex_dump_compact():
    assert format_hex_dump("0210010003A7") == "0000  02 10 01 00 03 A7"

def test_format_hex_dump_empty():
    assert format_hex_dump("") == ""

def test_format_hex_dump_spaced():
    assert format_hex_dump("02 10 01 00 03 A7") == "0000  02 10 01 00 03 A7"

def test_format_hex_dump_invalid_char():
    assert "Invalid hex payload" in format_hex_dump("G")
    assert "Invalid hex payload" in format_hex_dump("0210010003A7G")

def test_format_hex_dump_invalid_odd_length():
    assert "Invalid hex payload length" in format_hex_dump("ABC")

def test_format_hex_dump_16_bytes_split():
    hex_str_long = "00" * 20
    formatted_long = format_hex_dump(hex_str_long)
    lines = formatted_long.split("\n")
    assert len(lines) == 2
    assert lines[0] == "0000  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
    assert lines[1] == "0010  00 00 00 00"
