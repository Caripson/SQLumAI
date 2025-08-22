from src.tds.parser import iter_packets, extract_sqlbatch_text, type_name


def test_parse_header_and_iter_packets():
    # Build two simple packets: type=1, len=12 (8 header + 4 payload)
    def pkt(typ, payload=b"ABCD"):
        length = 8 + len(payload)
        hdr = bytes([typ, 0x01, (length >> 8) & 0xFF, length & 0xFF, 0x00, 0x2A, 0x01, 0x00])
        return hdr + payload

    buf = pkt(1) + pkt(3)
    packets = iter_packets(buf)
    assert len(packets) == 2
    t1, _, l1, spid1, _, pay1 = packets[0]
    assert t1 == 1 and l1 == 12 and spid1 == 42 and pay1 == b"ABCD"
    # type name resolution
    assert type_name(1).lower().startswith("sql batch") and "Unknown" in type_name(0xFE)


def test_extract_sqlbatch_text_decoding():
    s = "SELECT 1"
    data = s.encode("utf-16le")
    assert extract_sqlbatch_text([data]) == s
    # Fallback to latin-1
    s2 = "abc"
    assert extract_sqlbatch_text([s2.encode("latin-1")]) == s2

