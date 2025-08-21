from agents.normalizers import (
    normalize_date,
    normalize_phone_se,
    normalize_postal,
    normalize_email,
    normalize_country_iso,
    normalize_orgnr_se,
    suggest_normalizations,
)


def test_normalize_date():
    v, kind = normalize_date('1/2/24')
    assert v == '2024-02-01' and kind == 'date'
    v, kind = normalize_date('2024-12-31')
    assert v == '2024-12-31'


def test_normalize_phone_se():
    v, kind = normalize_phone_se('070 123 45 67')
    assert v.startswith('+46') and kind == 'phone'


def test_normalize_postal_and_email():
    assert normalize_postal('12345')[0] == '12345'
    assert normalize_email('TEST@EXAMPLE.COM')[0] == 'test@example.com'


def test_country_and_orgnr():
    assert normalize_country_iso('se')[0] == 'SE'
    assert normalize_country_iso('Sweden')[0] == 'SE'
    assert normalize_orgnr_se('16 1234567890')[0] == '1234567890'


def test_suggest():
    s = suggest_normalizations('31/12/24')
    assert s and s['kind'] == 'date'
