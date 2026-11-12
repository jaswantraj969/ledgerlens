"""Atomic file writes: a reader, or a resumed run, sees the old file or the complete new one.

The text goes to a uniquely named temporary file in the target's directory, is flushed and
fsynced, then renamed over the target with os.replace, which is atomic on one volume (Windows and
POSIX). If anything fails before the rename, the temporary file is removed and the target is
untouched.
"""

import contextlib
import os
import tempfile
from pathlib import Path


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
        raise
