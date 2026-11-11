"""Load mail credentials from the project .env file."""
import os
import shlex
from pathlib import Path


BASE = Path(__file__).parent


def load_mail_credentials():
    values = {}
    env_file = BASE / ".env"
    if env_file.exists():
        for line_number, raw_line in enumerate(
            env_file.read_text(encoding="utf-8").splitlines(), 1
        ):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise SystemExit(f"Invalid .env entry on line {line_number}.")
            key, raw_value = line.split("=", 1)
            key = key.strip()
            if not key:
                raise SystemExit(f"Invalid .env entry on line {line_number}.")
            try:
                parsed = shlex.split(raw_value.strip())
            except ValueError as exc:
                raise SystemExit(f"Invalid .env entry on line {line_number}: {exc}")
            if len(parsed) > 1:
                raise SystemExit(f"Invalid .env entry on line {line_number}.")
            values[key] = parsed[0] if parsed else ""

    user = os.environ.get("MAIL_USER", values.get("MAIL_USER", ""))
    password = os.environ.get(
        "MAIL_APP_PASSWORD", values.get("MAIL_APP_PASSWORD", "")
    )
    return user, password
