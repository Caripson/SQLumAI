import os
from pathlib import Path
from typing import Optional


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Simple secrets provider abstraction.
    Provider is chosen by SECRET_PROVIDER env: env|file. Default: env.
    - env: read from environment variable NAME
    - file: read from file path in env var NAME_FILE (or NAME) if it looks like a path
    """
    provider = os.getenv("SECRET_PROVIDER", "env").lower()
    if provider == "file":
        path = os.getenv(f"{name}_FILE") or os.getenv(name)
        if path and (path.startswith('/') or path.startswith('./') or path.startswith('../')) and Path(path).exists():
            return Path(path).read_text(encoding="utf-8").strip()
        # fallback to env if no file found
    val = os.getenv(name, default)
    return val

