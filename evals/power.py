"""AC or battery for any moment, from the Windows power log (Kernel-Power events 105 and 42/107).

Event 105 records each power-source change with `AcOnline`. Between two changes the state holds.
Times while the machine slept are not compute time, so they never matter. A moment before the
first event, or on a machine without the log, is "unknown", never assumed.

The events are read once with PowerShell and saved, so audits are reproducible:
docs/progress/logs/power-events.json.
"""

import bisect
import json
import subprocess
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVENTS_FILE = ROOT / "docs" / "progress" / "logs" / "power-events.json"
_QUERY = r"""
$events = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-Power'; Id=105} -ErrorAction SilentlyContinue | Sort-Object TimeCreated
$events | ForEach-Object { $x = [xml]$_.ToXml(); $ac = ($x.Event.EventData.Data | Where-Object Name -eq 'AcOnline').'#text'; [pscustomobject]@{utc=$_.TimeCreated.ToUniversalTime().ToString('o'); ac_online=$ac} } | ConvertTo-Json
"""  # noqa: E501


def read_events() -> list[dict[str, Any]]:
    """Query the log now and save it. Returns [] where there is no Windows power log."""
    try:
        out = subprocess.run(  # noqa: S603 - fixed command, no user input
            ["powershell", "-NoProfile", "-Command", _QUERY],  # noqa: S607
            capture_output=True, text=True, check=True, timeout=60,
        ).stdout  # fmt: skip
    except (OSError, subprocess.SubprocessError):
        return []
    events = json.loads(out) if out.strip() else []
    events = events if isinstance(events, list) else [events]
    parsed = [{"utc": e["utc"], "ac": str(e["ac_online"]).lower() == "true"} for e in events]
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    EVENTS_FILE.write_text(json.dumps(parsed, indent=1) + "\n", encoding="utf-8", newline="\n")
    return parsed


class PowerLog:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        pairs = sorted((_ts(e["utc"]), bool(e["ac"])) for e in events)
        self.times = [t for t, _ in pairs]
        self.states = [ac for _, ac in pairs]

    @classmethod
    def load(cls, refresh: bool = False) -> "PowerLog":
        if refresh or not EVENTS_FILE.exists():
            return cls(read_events())
        return cls(json.loads(EVENTS_FILE.read_text(encoding="utf-8")))

    def state_at(self, timestamp: float) -> str:
        index = bisect.bisect_right(self.times, timestamp) - 1
        if index < 0:
            return "unknown"
        return "ac" if self.states[index] else "battery"

    def summarize(self, timestamps: Iterable[float]) -> dict[str, Any]:
        """Counts per state, and one label: ac, battery-affected, or unknown."""
        counts = Counter(self.state_at(t) for t in timestamps)
        if counts["battery"]:
            label = "battery-affected"
        elif counts["unknown"] or not counts:
            label = "unknown"
        else:
            label = "ac"
        return {
            "label": label,
            "timings_ac": counts["ac"],
            "timings_battery": counts["battery"],
            "timings_unknown": counts["unknown"],
            "source": "Windows Kernel-Power event 105",
        }


def _ts(text: str) -> float:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC).timestamp()


def timings_power(paths: Iterable[Path], refresh: bool = True) -> dict[str, Any]:
    """Power state when each timing was recorded, from the modification times of the cache
    files that hold them (OCR entries and LLM replies are written once, when measured)."""
    stamps = [path.stat().st_mtime for path in paths if path.exists()]
    return PowerLog.load(refresh=refresh).summarize(stamps) | {
        "method": "cache file modification time per recorded timing"
    }


def ac_online_now() -> bool | None:
    """Whether AC power is connected right now (Windows GetSystemPowerStatus); None if unknown."""
    import ctypes
    import sys

    if sys.platform != "win32":
        return None

    class SystemPowerStatus(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_ubyte),
            ("BatteryFlag", ctypes.c_ubyte),
            ("BatteryLifePercent", ctypes.c_ubyte),
            ("SystemStatusFlag", ctypes.c_ubyte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    status = SystemPowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):  # type: ignore[attr-defined,unused-ignore]  # windll: Windows only
        return None
    return {0: False, 1: True}.get(status.ACLineStatus)
