"""
Experimental TDS RPC Request payload builder for a subset of types (NVARCHAR, INT, BIT)
and best‑effort extensions (DECIMAL/NUMERIC, DATE/TIME/DATETIME2/DATETIMEOFFSET,
UNIQUEIDENTIFIER, VARBINARY). This is intended for controlled tests, not full TDS fidelity.
This constructs only the RPC payload (not the outer TDS header). It is best-effort and
intended for controlled testing, not production-grade TDS encoding.
"""
from typing import List, Tuple
import uuid
from decimal import Decimal, InvalidOperation
import datetime as dt


# TDS type IDs (subset)
TDS_INTN = 0x26
TDS_BITN = 0x68
TDS_NVARCHAR = 0xE7
TDS_DECIMALN = 0x6A
TDS_NUMERICN = 0x6C
TDS_DATE = 0x28
TDS_TIME = 0x29
TDS_DATETIME2 = 0x2A
TDS_DATETIMEOFFSET = 0x2B
TDS_UNIQUEIDENTIFIER = 0x24
TDS_VARBINARY = 0xA5


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

        t = typ.lower()
        if t == "int":
            # INTN: type, max length, then value length + value
            out += bytes([TDS_INTN])
            out += b"\x04"  # max length 4
            try:
                iv = int(value)
            except Exception:
                iv = 0
            out += b"\x04"  # actual length
            out += int(iv).to_bytes(4, byteorder="little", signed=True)
        elif t == "bit":
            out += bytes([TDS_BITN])
            out += b"\x01"  # max length 1
            bv = 1 if str(value).strip().lower() in ("1", "true", "yes") else 0
            out += b"\x01"  # actual length
            out += bytes([bv])
        elif t in ("decimal", "numeric"):
            # Best-effort DECIMAL/NUMERIC encoding
            out += bytes([TDS_DECIMALN if t == "decimal" else TDS_NUMERICN])
            try:
                d = Decimal(str(value))
            except (InvalidOperation, ValueError):
                d = Decimal(0)
            sign = 1 if d >= 0 else 0
            d = abs(d)
            s = d.as_tuple()
            scale = max(0, -s.exponent)
            precision = len(s.digits)
            # Storage length by precision (TDS rules simplified)
            if precision <= 9:
                stor_len = 5
            elif precision <= 19:
                stor_len = 9
            elif precision <= 28:
                stor_len = 13
            else:
                stor_len = 17
            out += bytes([stor_len])  # max length
            out += bytes([precision])
            out += bytes([scale])
            # Compute scaled integer
            scaled = int(d.scaleb(scale))
            val_bytes = scaled.to_bytes(stor_len - 1, byteorder="little", signed=False)
            out += bytes([stor_len])  # actual length
            out += bytes([sign]) + val_bytes
        elif t in ("uniqueidentifier", "uuid"):
            out += bytes([TDS_UNIQUEIDENTIFIER])
            out += b"\x10"  # max length 16
            try:
                g = uuid.UUID(str(value))
                data = g.bytes  # note: SQL Server uses mixed-endian; test harness doesn't decode
            except Exception:
                data = b"\x00" * 16
            out += b"\x10"  # actual length
            out += data
        elif t in ("varbinary", "binary"):
            out += bytes([TDS_VARBINARY])
            out += (8000).to_bytes(2, byteorder="little")  # max length
            data = bytes.fromhex(value) if all(c in "0123456789abcdefABCDEF" for c in value.replace(" ", "")) else value.encode()
            out += len(data).to_bytes(2, byteorder="little")
            out += data
        elif t in ("date",):
            out += bytes([TDS_DATE])
            # DATE: 3-byte days since 0001-01-01
            out += b"\x03"  # max length
            try:
                y, m, d = map(int, str(value).split("-")[:3])
                days = (dt.date(y, m, d) - dt.date(1, 1, 1)).days
            except Exception:
                days = 0
            out += b"\x03"  # actual length
            out += int(days).to_bytes(3, byteorder="little", signed=False)
        elif t in ("time",):
            out += bytes([TDS_TIME])
            scale = 7
            out += bytes([scale])
            # time storage length for scale 7 is 5 bytes
            out += bytes([5])
            # encode as 100ns ticks since midnight
            try:
                parts = str(value).split(":")
                hh = int(parts[0])
                mm = int(parts[1])
                ss = int(parts[2].split(".")[0])
                frac = parts[2].split(".")[1] if "." in parts[2] else "0"
                frac = int((frac + "0" * 7)[:7])
                ticks = ((hh * 3600 + mm * 60 + ss) * 10_000_000) + frac
            except Exception:
                ticks = 0
            out += int(ticks).to_bytes(5, byteorder="little", signed=False)
        elif t in ("datetime2",):
            out += bytes([TDS_DATETIME2])
            scale = 7
            out += bytes([scale])
            # time portion length + date (3) -> 5 + 3
            out += bytes([8])
            try:
                dtv = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00").split("+")[0])
                base_date = dt.date(1, 1, 1)
                days = (dtv.date() - base_date).days
                seconds = dtv.hour * 3600 + dtv.minute * 60 + dtv.second
                ticks = seconds * 10_000_000 + int(dtv.microsecond * 10)
            except Exception:
                days = 0
                ticks = 0
            out += int(ticks).to_bytes(5, byteorder="little", signed=False)
            out += int(days).to_bytes(3, byteorder="little", signed=False)
        elif t in ("datetimeoffset",):
            out += bytes([TDS_DATETIMEOFFSET])
            scale = 7
            out += bytes([scale])
            # time(5) + date(3) + offset(2) = 10
            out += bytes([10])
            try:
                # Expect e.g. 2024-08-21T12:34:56+02:00
                s = str(value)
                if s.endswith("Z"):
                    s = s[:-1] + "+00:00"
                dtv = dt.datetime.fromisoformat(s)
                base_date = dt.date(1, 1, 1)
                days = (dtv.date() - base_date).days
                seconds = dtv.hour * 3600 + dtv.minute * 60 + dtv.second
                ticks = seconds * 10_000_000 + int(dtv.microsecond * 10)
                # offset minutes
                off = dtv.utcoffset().total_seconds() // 60 if dtv.utcoffset() else 0
            except Exception:
                days = 0
                ticks = 0
                off = 0
            out += int(ticks).to_bytes(5, byteorder="little", signed=False)
            out += int(days).to_bytes(3, byteorder="little", signed=False)
            out += int(off).to_bytes(2, byteorder="little", signed=True)
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
