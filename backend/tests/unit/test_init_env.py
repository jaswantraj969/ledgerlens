import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("init_env", ROOT / "scripts" / "init_env.py")
assert _spec and _spec.loader
init_env = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(init_env)


def test_every_change_me_value_is_replaced_and_the_password_matches() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    text = init_env.render(example, "p" * 48, "j" * 64, 8081)
    values = dict(
        line.split("=", 1) for line in text.splitlines() if "=" in line and not line.startswith("#")
    )
    assert "change-me" not in "".join(values.values())
    assert values["POSTGRES_PASSWORD"] == "p" * 48
    assert ":" + "p" * 48 + "@" in values["LEDGERLENS_DATABASE_URL"]
    assert values["LEDGERLENS_JWT_SECRET"] == "j" * 64
    assert values["LEDGERLENS_WEB_PORT"] == "8081"


def test_the_default_web_port_is_kept_without_the_option() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "LEDGERLENS_WEB_PORT=8080" in init_env.render(example, "a" * 48, "b" * 64, None)
