from packet_probe_viewer.widgets.hex_view import format_hex_dump

def test_format_hex_dump():
    hex_str = "0210010003A7"
    formatted = format_hex_dump(hex_str)
    assert formatted == "0000  02 10 01 00 03 A7"

    hex_str_long = "00" * 20
    formatted_long = format_hex_dump(hex_str_long)
    lines = formatted_long.split("\n")
    assert len(lines) == 2
    assert lines[0] == "0000  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
    assert lines[1] == "0010  00 00 00 00"
