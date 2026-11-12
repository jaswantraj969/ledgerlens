"""Tests for the fixes in docs/security-review.md."""

import io
import re
import socket
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from ledgerlens.core.errors import Problem
from ledgerlens.ingest.validate import MAX_IMAGE_PIXELS, validate_upload
from ledgerlens.workers import webhooks
from ledgerlens.workers.webhooks import (
    REPLAY_WINDOW_SECONDS,
    UnsafeWebhookUrl,
    check_url,
    sign,
    verify,
)

ROOT = Path(__file__).resolve().parents[3]
SECRET = "whsec_test"
BODY = b'{"event":"job.completed"}'
NOW = 1_800_000_000


def test_a_fresh_correctly_signed_delivery_verifies() -> None:
    assert verify(SECRET, str(NOW), sign(SECRET, NOW, BODY), BODY, now=NOW + 5)


@pytest.mark.parametrize(
    ("secret", "timestamp", "body", "now"),
    [
        ("another_secret", NOW, BODY, NOW),  # wrong key
        (SECRET, NOW, BODY + b" ", NOW),  # tampered body
        (SECRET, NOW, BODY, NOW + REPLAY_WINDOW_SECONDS + 1),  # replayed later
        (SECRET, NOW, BODY, NOW - REPLAY_WINDOW_SECONDS - 1),  # timestamp in the future
    ],
)
def test_bad_or_stale_deliveries_do_not_verify(
    secret: str, timestamp: int, body: bytes, now: int
) -> None:
    signature = sign(SECRET, NOW, BODY)
    assert not verify(secret, str(timestamp), signature, body, now=now)


def test_the_window_edge_is_inclusive_and_bad_timestamps_fail() -> None:
    signature = sign(SECRET, NOW, BODY)
    assert verify(SECRET, str(NOW), signature, BODY, now=NOW + REPLAY_WINDOW_SECONDS)
    assert not verify(SECRET, "not-a-number", signature, BODY, now=NOW)


def _resolve_to(monkeypatch: pytest.MonkeyPatch, address: str) -> None:
    family = socket.AF_INET6 if ":" in address else socket.AF_INET

    def fake(*_: Any, **__: Any) -> list[tuple[Any, ...]]:
        return [(family, socket.SOCK_STREAM, 6, "", (address, 443))]

    monkeypatch.setattr(webhooks.socket, "getaddrinfo", fake)


@pytest.mark.parametrize(
    "address",
    [
        "10.1.2.3", "172.16.0.1", "192.168.0.1", "127.0.0.1", "0.0.0.0",  # noqa: S104 (an address under test, not a bind)
        "169.254.169.254",  # cloud metadata (link-local)
        "100.64.0.1",  # shared address space (carrier-grade NAT)
        "224.0.0.1",  # multicast
        "::1", "fd00::1", "fe80::1",
        "::ffff:127.0.0.1", "::ffff:10.0.0.1",  # IPv4 inside IPv6
    ],
)  # fmt: skip
def test_hosts_resolving_to_non_public_addresses_are_refused(
    monkeypatch: pytest.MonkeyPatch, address: str
) -> None:
    _resolve_to(monkeypatch, address)
    with pytest.raises(UnsafeWebhookUrl):
        check_url("https://hooks.example.test/x", allow_insecure=False)


@pytest.mark.parametrize("address", ["93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"])
def test_hosts_resolving_to_public_addresses_are_allowed(
    monkeypatch: pytest.MonkeyPatch, address: str
) -> None:
    _resolve_to(monkeypatch, address)
    check_url("https://hooks.example.test/x", allow_insecure=False)


def _png(width: int, height: int) -> bytes:
    output = io.BytesIO()
    Image.new("1", (width, height)).save(output, format="PNG")
    return output.getvalue()


def test_images_over_the_pixel_limit_are_refused_before_decoding() -> None:
    side = int(MAX_IMAGE_PIXELS**0.5) + 1
    with pytest.raises(Problem) as raised:
        validate_upload("big.png", _png(side, side), 50_000_000, 50)
    assert raised.value.code == "image_too_large"
    assert raised.value.status == 413
    assert validate_upload("small.png", _png(100, 100), 50_000_000, 50).pages == 1


@pytest.mark.parametrize("dockerfile", ["backend/Dockerfile", "frontend/Dockerfile"])
def test_containers_run_as_a_non_root_user(dockerfile: str) -> None:
    text = (ROOT / dockerfile).read_text(encoding="utf-8")
    final_stage = text[text.rindex("\nFROM ") :]
    users = re.findall(r"^USER\s+(\S+)", final_stage, flags=re.M)
    assert users, f"{dockerfile}: the final stage sets no USER, so it runs as root"
    assert users[-1] not in {"root", "0", "0:0"}


def test_the_web_proxy_does_not_expose_metrics() -> None:
    caddyfile = (ROOT / "frontend" / "Caddyfile").read_text(encoding="utf-8")
    api_block = caddyfile[caddyfile.index("handle_path /api/*") :]
    api_block = api_block[: api_block.index("}")]
    assert "@internal path /metrics /metrics/*" in api_block
    assert api_block.index("respond @internal 404") < api_block.index("reverse_proxy")
