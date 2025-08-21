import os
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

