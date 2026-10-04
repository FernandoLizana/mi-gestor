"""Carga .env compatible con hosting ASCII (cPanel / Passenger)."""

import os


def _parse_env_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    key, _, value = line.partition("=")
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return key, value


def safe_load_dotenv(dotenv_path: str, *, override: bool = False) -> None:
    """Carga variables ASCII-safe; evita UnicodeEncodeError en os.environ."""
    if not dotenv_path or not os.path.isfile(dotenv_path):
        return

    with open(dotenv_path, encoding="utf-8-sig") as handle:
        for raw in handle:
            parsed = _parse_env_line(raw)
            if not parsed:
                continue
            key, value = parsed
            try:
                value.encode("ascii")
            except UnicodeEncodeError:
                continue
            if override or key not in os.environ:
                os.environ[key] = value
