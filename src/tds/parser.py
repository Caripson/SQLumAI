from typing import Optional, Tuple, List


TDS_TYPES = {
    0x01: "SQL Batch",
    0x02: "Pre-TDS Login",
    0x03: "RPC",
    0x04: "Tabular Result",
    0x12: "Login7",
    0x07: "Attention",
    0x0E: "Transaction Manager",
}


def parse_header(buf: bytes) -> Optional[Tuple[int, int, int, int, int, int]]:
    if len(buf) < 8:
        return None
    typ = buf[0]
    status = buf[1]
    length = (buf[2] << 8) | buf[3]
    spid = (buf[4] << 8) | buf[5]
    packet = buf[6]
    window = buf[7]
    return typ, status, length, spid, packet, window


def type_name(typ: int) -> str:
    return TDS_TYPES.get(typ, f"Unknown(0x{typ:02x})")


EOM = 0x01  # End Of Message


def iter_packets(buf: bytes) -> List[Tuple[int, int, int, int, int, bytes]]:
    """
    Yields (typ, status, length, spid, packet, payload) for each full packet in buf.
    If a declared length exceeds the available buffer, stops.
    """
    packets: List[Tuple[int, int, int, int, int, bytes]] = []
    off = 0
    while off + 8 <= len(buf):
        hdr = parse_header(buf[off:off+8])
        if not hdr:
            break
        typ, status, length, spid, packet, window = hdr
        if length < 8 or off + length > len(buf):
            break
        payload = buf[off+8: off+length]
        packets.append((typ, status, length, spid, packet, payload))
        off += length
    return packets


def extract_sqlbatch_text(chunks: List[bytes]) -> Optional[str]:
    """
    Given a list of concatenated SQL Batch payload chunks (may be split across packets),
    try to decode as UTF-16LE first (typical for TDS), falling back to latin-1.
    """
    if not chunks:
        return None
    data = b"".join(chunks)
    for enc in ("utf-16le", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return None
