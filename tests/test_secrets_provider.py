from src.runtime.secrets import get_secret


def test_env_provider(monkeypatch):
    monkeypatch.setenv("SECRET_PROVIDER", "env")
    monkeypatch.setenv("MY_SECRET", "abc")
    assert get_secret("MY_SECRET") == "abc"


def test_file_provider(tmp_path, monkeypatch):
    p = tmp_path / "s.txt"
    p.write_text("xyz", encoding="utf-8")
    monkeypatch.setenv("SECRET_PROVIDER", "file")
    monkeypatch.setenv("MY_SECRET_FILE", str(p))
    assert get_secret("MY_SECRET") == "xyz"


def test_file_provider_strict_missing_path_raises(monkeypatch):
    monkeypatch.setenv("SECRET_PROVIDER", "file")
    monkeypatch.setenv("SECRET_PROVIDER_MODE", "strict")
    # No MY_SECRET_FILE and MY_SECRET is not a path
    monkeypatch.delenv("MY_SECRET", raising=False)
    monkeypatch.delenv("MY_SECRET_FILE", raising=False)
    try:
        get_secret("MY_SECRET")
        assert False, "expected error in strict mode when no file path is provided"
    except RuntimeError as e:
        assert "no file path provided" in str(e)


def test_file_provider_strict_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_PROVIDER", "file")
    monkeypatch.setenv("SECRET_PROVIDER_MODE", "strict")
    p = tmp_path / "does_not_exist.txt"
    monkeypatch.setenv("MY_SECRET_FILE", str(p))
    try:
        get_secret("MY_SECRET")
        assert False, "expected error in strict mode when file is missing"
    except FileNotFoundError as e:
        assert "not found" in str(e)
