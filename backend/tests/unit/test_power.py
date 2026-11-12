from datetime import UTC, datetime

from evals.power import PowerLog


def at(text: str) -> float:
    return datetime.fromisoformat(text).replace(tzinfo=UTC).timestamp()


LOG = PowerLog(
    [
        {"utc": "2026-11-07T18:50:50Z", "ac": True},
        {"utc": "2026-11-07T20:52:04Z", "ac": False},
        {"utc": "2026-11-08T05:42:29Z", "ac": True},
    ]
)


def test_state_holds_between_changes() -> None:
    assert LOG.state_at(at("2026-11-07T19:30:00")) == "ac"
    assert LOG.state_at(at("2026-11-07T21:11:00")) == "battery"
    assert LOG.state_at(at("2026-11-08T06:00:00")) == "ac"


def test_before_the_first_event_is_unknown_not_assumed() -> None:
    assert LOG.state_at(at("2026-11-01T00:00:00")) == "unknown"


def test_any_battery_timing_labels_the_whole_result() -> None:
    summary = LOG.summarize([at("2026-11-07T19:00:00"), at("2026-11-07T21:00:00")])
    assert summary["label"] == "battery-affected"
    assert (summary["timings_ac"], summary["timings_battery"]) == (1, 1)


def test_only_ac_is_ac_and_nothing_is_unknown() -> None:
    assert LOG.summarize([at("2026-11-07T19:00:00")])["label"] == "ac"
    assert LOG.summarize([])["label"] == "unknown"
    mixed = [at("2026-11-01T00:00:00"), at("2026-11-07T19:00:00")]
    assert LOG.summarize(mixed)["label"] == "unknown"


def _fake_powershell(monkeypatch, tmp_path):  # type: ignore[no-untyped-def]
    import subprocess

    from evals import power

    reply = '[{"utc": "2026-11-12T06:00:00Z", "ac_online": "True"}]'
    monkeypatch.setattr(
        power.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, reply, ""),
    )  # fmt: skip
    monkeypatch.setattr(power, "LIVE_FILE", tmp_path / "data" / "power-events.json")
    monkeypatch.setattr(power, "EVENTS_FILE", tmp_path / "logs" / "power-events.json")
    return power


def test_an_ordinary_refresh_never_writes_the_committed_snapshot(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    power = _fake_powershell(monkeypatch, tmp_path)
    power.PowerLog.load(refresh=True)
    assert power.LIVE_FILE.exists()
    assert not power.EVENTS_FILE.exists()


def test_only_an_explicit_audit_updates_the_snapshot(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    power = _fake_powershell(monkeypatch, tmp_path)
    power.PowerLog.load(refresh=True, snapshot=True)
    assert power.LIVE_FILE.exists() and power.EVENTS_FILE.exists()


def test_a_plain_load_prefers_the_local_copy_then_the_snapshot(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    power = _fake_powershell(monkeypatch, tmp_path)
    power.EVENTS_FILE.parent.mkdir(parents=True)
    power.EVENTS_FILE.write_text('[{"utc": "2026-11-01T00:00:00Z", "ac": false}]', encoding="utf-8")
    assert power.PowerLog.load().state_at(at("2026-11-02T00:00:00")) == "battery"
    power.LIVE_FILE.parent.mkdir(parents=True)
    power.LIVE_FILE.write_text('[{"utc": "2026-11-01T00:00:00Z", "ac": true}]', encoding="utf-8")
    assert power.PowerLog.load().state_at(at("2026-11-02T00:00:00")) == "ac"
