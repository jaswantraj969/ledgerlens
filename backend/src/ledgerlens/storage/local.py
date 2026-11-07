"""Document storage. Keys are generated here; uploaded names never reach a path."""

import uuid
from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    def put(self, organization_id: uuid.UUID, sha256: str, data: bytes) -> str: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def healthy(self) -> bool: ...


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("storage key escapes the root")
        return path

    def put(self, organization_id: uuid.UUID, sha256: str, data: bytes) -> str:
        key = f"org/{organization_id}/{sha256}"
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)
        return key

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def healthy(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            probe = self.root / ".probe"
            probe.write_bytes(b"ok")
            probe.unlink()
        except OSError:
            return False
        return True
