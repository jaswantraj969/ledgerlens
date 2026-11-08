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
