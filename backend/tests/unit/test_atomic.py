import os
from pathlib import Path

import pytest
from evals import atomic
from evals.atomic import write_text_atomic

ROOT = Path(__file__).resolve().parents[3]


def test_writes_the_exact_text_with_lf_newlines(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "out.json"
    write_text_atomic(target, '{"a": 1}\n')
    assert target.read_bytes() == b'{"a": 1}\n'
    assert list(target.parent.iterdir()) == [target]


@pytest.mark.parametrize("failing", ["fsync", "replace"])
def test_a_crash_before_the_rename_leaves_the_old_file_and_no_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failing: str
) -> None:
    target = tmp_path / "out.json"
    target.write_text("old", encoding="utf-8")

    def crash(*_: object) -> None:
        raise OSError("simulated crash")

    monkeypatch.setattr(atomic.os, failing, crash)
    with pytest.raises(OSError, match="simulated"):
        write_text_atomic(target, "new and much longer content")
    assert target.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.iterdir()) == [target]


def test_a_crash_on_first_write_leaves_no_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(atomic.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("x")))
    with pytest.raises(OSError):
        write_text_atomic(tmp_path / "out.json", "{}")
    assert list(tmp_path.iterdir()) == []
    assert os.path.exists(tmp_path)


@pytest.mark.parametrize(
    "runner", ["run_cord.py", "run_s5.py", "run_s5_ablations.py", "run_final_test.py"]
)
def test_protocol_runners_write_files_only_atomically(runner: str) -> None:
    source = (ROOT / "evals" / "runners" / runner).read_text(encoding="utf-8")
    assert ".write_text(" not in source
    assert "write_text_atomic(" in source
