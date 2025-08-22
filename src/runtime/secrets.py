import os
from pathlib import Path
from typing import Optional


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Simple secrets provider abstraction.
    Provider is chosen by SECRET_PROVIDER env: env|file. Default: env.
    - env: read from environment variable NAME
    - file: read from file path in env var NAME_FILE (or NAME) if it looks like a path

    Behavior mode is controlled by SECRET_PROVIDER_MODE: permissive|strict (default: permissive).
    - permissive: fallback to env value if file path is missing or unreadable
    - strict: raise an error if provider=file but a valid secret file cannot be read
    """
    provider = os.getenv("SECRET_PROVIDER", "env").lower()
    mode = os.getenv("SECRET_PROVIDER_MODE", "permissive").lower()
    if provider == "file":
        path_env = os.getenv(f"{name}_FILE")
        inline = os.getenv(name)
        # Prefer NAME_FILE; otherwise treat NAME as a path only if it looks like one
        path = path_env or (inline if (inline or "").startswith(("/", "./", "../")) else None)
        if path:
            p = Path(path)
            if p.exists():
                try:
                    return p.read_text(encoding="utf-8").strip()
                except Exception as e:
                    if mode == "strict":
                        raise RuntimeError(f"Failed reading secret file for {name}: {path}: {e}")
                    # permissive: fall through to env/default
            else:
                if mode == "strict":
                    raise FileNotFoundError(f"Secret file not found for {name}: {path}")
        else:
            if mode == "strict":
                raise RuntimeError(
                    f"SECRET_PROVIDER=file but no file path provided for {name} (set {name}_FILE)"
                )
        # permissive fallback to env if file missing/unreadable
    return os.getenv(name, default)
