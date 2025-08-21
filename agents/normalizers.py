import re
from typing import Optional, Tuple


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
    "orgnr": "Use normalized organisation number format"
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


def suggest_normalizations(value: str):
    for fn in (normalize_date, normalize_phone_se, normalize_postal, normalize_email, normalize_country_iso, normalize_orgnr_se):
        normalized, kind = fn(value)
        if normalized:
            return {"kind": kind, "normalized": normalized, "hint": HINTS.get(kind)}
    return None
