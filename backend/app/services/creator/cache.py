"""外部 API レスポンスのファイルキャッシュ。

同じ入力（出発地・目的地・経由地、パノラマ ID と向き）なら API を叩かずに再利用する。
キーは入力を JSON にして SHA-256 にしたもの。ハッカソン中に同じ経路を何度も試すときの
無料枠と時間の節約が目的で、失効はしない（消したいときはディレクトリごと削除する）。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def cache_key(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


class FileCache:
    def __init__(self, root: Path, namespace: str) -> None:
        self._dir = root / namespace

    def _path(self, key: str, ext: str) -> Path:
        return self._dir / f"{key}.{ext}"

    def get_json(self, key: str) -> Any | None:
        p = self._path(key, "json")
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def set_json(self, key: str, value: Any) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path(key, "json").write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def get_bytes(self, key: str, ext: str = "jpg") -> bytes | None:
        p = self._path(key, ext)
        return p.read_bytes() if p.exists() else None

    def set_bytes(self, key: str, data: bytes, ext: str = "jpg") -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path(key, ext).write_bytes(data)
