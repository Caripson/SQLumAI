from src.tds.rpc_build import build_rpc_payload


def grab_type_bytes(payload: bytes) -> bytes:
    # Heuristic: after procedure name and flags, parameters begin. We'll just return payload for inspection.
    return payload


def test_build_decimal_and_numeric():
    p = build_rpc_payload("dbo.proc", [("@amount", "123.45", "decimal"), ("num", "-7.5", "numeric")])
    # Type markers must be present
    assert b"\x6a" in p or b"\x6A" in p
    assert b"\x6c" in p or b"\x6C" in p


def test_build_datetime_and_uuid_and_varbinary():
    p = build_rpc_payload(
        "dbo.proc",
        [
            ("d2", "2024-08-21T12:34:56", "datetime2"),
            ("do", "2024-08-21T12:34:56+02:00", "datetimeoffset"),
            ("dt", "2024-08-21", "date"),
            ("t", "12:00:00", "time"),
            ("id", "550e8400-e29b-41d4-a716-446655440000", "uniqueidentifier"),
            ("bin", "DEADBEEF", "varbinary"),
        ],
    )
    # Type markers present: datetime2(0x2A), datetimeoffset(0x2B), date(0x28), time(0x29), uuid(0x24), varbinary(0xA5)
    for marker in (0x2A, 0x2B, 0x28, 0x29, 0x24, 0xA5):
        assert bytes([marker]) in p


