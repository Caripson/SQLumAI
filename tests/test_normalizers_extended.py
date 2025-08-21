from agents.normalizers import (
    normalize_decimal,
    normalize_uuid,
    normalize_datetime,
    suggest_normalizations,
)


def test_normalize_decimal_locales():
    assert normalize_decimal("1 234,50")[0] == "1234.50"
    assert normalize_decimal("1234.5")[0] == "1234.5"


def test_normalize_uuid():
    val, kind = normalize_uuid("{550E8400-E29B-41D4-A716-446655440000}")
    assert kind == "uuid"
    assert val == "550e8400-e29b-41d4-a716-446655440000"


def test_normalize_datetime_and_suggest():
    val, kind = normalize_datetime("2024-8-5 7:03")
    assert kind == "datetime" and val == "2024-08-05T07:03:00"
    sug = suggest_normalizations("1 234,50")
    assert sug and sug["kind"] == "decimal"

