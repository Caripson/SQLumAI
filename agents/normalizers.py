import re
from typing import Optional, Tuple
from decimal import Decimal, InvalidOperation
import datetime as dt
import uuid as uuidlib


def normalize_date(value: str) -> Tuple[Optional[str], Optional[str]]:
    v = value.strip()
    # Accept D/M/Y or M/D/Y with separators / or - and 2/4-digit year.
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", v)
    if m:
        d, mth, y = m.groups()
        y = y if len(y) == 4 else ("20" + y)
        d = d.zfill(2)
        mth = mth.zfill(2)
        return (f"{y}-{mth}-{d}", "date")
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", v)
    if m:
        return (v, "date")
    return (None, None)


def normalize_phone_se(value: str) -> Tuple[Optional[str], Optional[str]]:
    v = re.sub(r"\s+", "", value)
    v = v.replace("(0)", "")
    if v.startswith("00"):  # 0046...
        v = "+" + v[2:]
    if v.startswith("0"):
        v = "+46" + v[1:]
    if v.startswith("+46"):
        return (v, "phone")
    return (None, None)


def normalize_postal(value: str) -> Tuple[Optional[str], Optional[str]]:
    v = re.sub(r"\s+", "", value)
    if re.match(r"^[0-9]{5}$", v):
        return (v, "postal")
    return (None, None)


def normalize_email(value: str) -> Tuple[Optional[str], Optional[str]]:
    v = value.strip()
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
        return (v.lower(), "email")
    return (None, None)


HINTS = {
    "date": "Use ISO dates (YYYY-MM-DD)",
    "phone": "Include country code (e.g., +46)",
    "postal": "Use 5 digits without spaces",
    "email": "Provide a valid email (local@domain)",
    "country_iso": "Use ISO 3166-1 alpha-2 (e.g., SE)",
    "orgnr": "Use normalized organisation number format",
    "decimal": "Use dot as decimal separator (e.g., 1234.56)",
    "uuid": "Use canonical UUID (8-4-4-4-12, lowercase)",
    "datetime": "Use ISO 8601 (YYYY-MM-DDTHH:MM:SS)",
}


def normalize_country_iso(value: str):
    v = value.strip()
    if len(v) == 2 and v.isalpha():
        return (v.upper(), "country_iso")
    m = {
        "sweden": "SE", "sverige": "SE",
        "united states": "US", "usa": "US", "us": "US",
        "united kingdom": "GB", "uk": "GB", "england": "GB",
        "germany": "DE", "deutschland": "DE",
        "norway": "NO", "norge": "NO",
        "denmark": "DK", "danmark": "DK",
        "finland": "FI", "suomi": "FI",
    }
    key = v.lower()
    if key in m:
        return (m[key], "country_iso")
    return (None, None)


def normalize_orgnr_se(value: str):
    digits = re.sub(r"\D+", "", value)
    if len(digits) == 10:
        return (digits, "orgnr")
    if len(digits) == 12 and digits.startswith("16"):
        # Trim century prefix often present
        return (digits[2:], "orgnr")
    return (None, None)


def normalize_decimal(value: str) -> Tuple[Optional[str], Optional[str]]:
    v = value.strip().replace(" ", "").replace("_", "")
    # Accept comma as decimal separator
    if "," in v and "." not in v:
        v = v.replace(",", ".")
    try:
        d = Decimal(v)
        # Render without scientific notation
        s = format(d, 'f')
        return (s, "decimal")
    except (InvalidOperation, ValueError):
        return (None, None)


def normalize_uuid(value: str) -> Tuple[Optional[str], Optional[str]]:
    v = value.strip().lower().strip("{}() ")
    try:
        u = uuidlib.UUID(v)
        return (str(u), "uuid")
    except Exception:
        return (None, None)


def normalize_datetime(value: str) -> Tuple[Optional[str], Optional[str]]:
    v = value.strip().replace("/", "-")
    # Common patterns
    candidates = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
    ]
    # Zero-pad month/day if single-digit in simple pattern like 2024-8-5 7:03
    try:
        parts = v.split(" ")
        date_part = parts[0]
        if len(date_part.split("-")) == 3:
            y, m, dday = date_part.split("-")
            if len(m) == 1 or len(dday) == 1:
                v = f"{y}-{m.zfill(2)}-{dday.zfill(2)}" + (" " + parts[1] if len(parts) > 1 else "")
    except Exception:
        pass
    for fmt in candidates:
        try:
            dtv = dt.datetime.strptime(v, fmt)
            return (dtv.strftime("%Y-%m-%dT%H:%M:%S"), "datetime")
        except Exception:
            continue
    return (None, None)


def suggest_normalizations(value: str):
    for fn in (
        normalize_date,
        normalize_datetime,
        normalize_phone_se,
        normalize_postal,
        normalize_email,
        normalize_decimal,
        normalize_uuid,
        normalize_country_iso,
        normalize_orgnr_se,
    ):
        normalized, kind = fn(value)
        if normalized:
            return {"kind": kind, "normalized": normalized, "hint": HINTS.get(kind)}
    return None
