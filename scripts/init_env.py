"""Create .env from .env.example with fresh random secrets. Refuses to overwrite an existing .env.

    python scripts/init_env.py [--web-port 8081]

Replaces the "change-me" PostgreSQL password (in POSTGRES_PASSWORD and inside
LEDGERLENS_DATABASE_URL, with the same value) and LEDGERLENS_JWT_SECRET with random values.
Secrets are written to .env only and never printed. Standard library only.
"""

import argparse
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render(example: str, password: str, jwt_secret: str, web_port: int | None) -> str:
    lines = []
    for line in example.splitlines():
        if line.startswith("POSTGRES_PASSWORD="):
            line = f"POSTGRES_PASSWORD={password}"
        elif line.startswith("LEDGERLENS_DATABASE_URL="):
            line = line.replace(":change-me@", f":{password}@")
        elif line.startswith("LEDGERLENS_JWT_SECRET="):
            line = f"LEDGERLENS_JWT_SECRET={jwt_secret}"
        elif line.startswith("LEDGERLENS_WEB_PORT=") and web_port is not None:
            line = f"LEDGERLENS_WEB_PORT={web_port}"
        lines.append(line)
    text = "\n".join(lines) + "\n"
    if "change-me" in "\n".join(line for line in lines if not line.startswith("#")):
        raise ValueError("a change-me value was left in .env")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--web-port", type=int, help="host port for the web UI (default 8080)")
    arguments = parser.parse_args()
    target = ROOT / ".env"
    if target.exists():
        print(".env already exists; not overwritten")
        return 1
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    text = render(example, secrets.token_hex(24), secrets.token_urlsafe(48), arguments.web_port)
    target.write_text(text, encoding="utf-8", newline="\n")
    print("wrote .env with new random secrets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
