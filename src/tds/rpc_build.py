"""
Experimental TDS RPC Request payload builder for a subset of types (NVARCHAR, INT, BIT).
This constructs only the RPC payload (not the outer TDS header). It is best-effort and
intended for controlled testing, not production-grade TDS encoding.
"""
from typing import List, Tuple


# TDS type IDs (subset)
TDS_INTN = 0x26
TDS_BITN = 0x68
TDS_NVARCHAR = 0xE7


def _us_varchar(s: str) -> bytes:
    b = s.encode("ascii", errors="ignore")
    if len(b) > 255:
        b = b[:255]
    return bytes([len(b)]) + b


def _b_varchar(s: str) -> bytes:
    # Same as US_VARCHAR in this context
    return _us_varchar(s)


def _collation_bytes() -> bytes:
    # Best-effort default collation bytes; may not match server defaults but often acceptable for tests
    # Structure: 4 bytes LCID and flags + 1 byte sort id (this is simplified)
    return b"\x09\x04\x00\x00\x00"  # LCID 0x0409 (en-US), sort id 0


def build_rpc_payload(proc_name: str, params: List[Tuple[str, str, str]]) -> bytes:
    out = bytearray()
    # Procedure name as US_VARCHAR
    out += _us_varchar(proc_name)
    # Option flags (2 bytes)
    out += b"\x00\x00"

    for name, value, typ in params:
        # Parameter name as B_VARCHAR including '@'
        pname = name if name.startswith("@") else ("@" + name)
        out += _b_varchar(pname)
        # Status flags: 0x00 = input
        out += b"\x00"
        # UserType (4 bytes) and Flags (2 bytes)
        out += b"\x00\x00\x00\x00"  # usertype
        out += b"\x00\x00"  # flags

        if typ.lower() == "int":
            # INTN: type, max length, then value length + value
            out += bytes([TDS_INTN])
            out += b"\x04"  # max length 4
            try:
                iv = int(value)
            except Exception:
                iv = 0
            out += b"\x04"  # actual length
            out += int(iv).to_bytes(4, byteorder="little", signed=True)
        elif typ.lower() == "bit":
            out += bytes([TDS_BITN])
            out += b"\x01"  # max length 1
            bv = 1 if str(value).strip().lower() in ("1", "true", "yes") else 0
            out += b"\x01"  # actual length
            out += bytes([bv])
        else:
            # NVARCHAR
            out += bytes([TDS_NVARCHAR])
            # Max length in bytes (UTF-16LE): choose 4000 chars = 8000 bytes
            out += (8000).to_bytes(2, byteorder="little")
            out += _collation_bytes()
            data = str(value).encode("utf-16le", errors="ignore")
            out += len(data).to_bytes(2, byteorder="little")
            out += data

    return bytes(out)
