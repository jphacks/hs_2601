"""作成ジョブの状態（メモリ上）。サーバーを再起動すると消える（docs/interface.md 5 章）。

ジョブはバックグラウンドのスレッドで進むので、読み書きはロックで守る。
状態は frozen なモデルで持ち、更新は model_copy で作り直して差し替える。
"""
from __future__ import annotations

import threading
import uuid
from typing import Any

from app.schemas.creator_api import JobStatus


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, JobStatus] = {}

    def start(self, route_id: str) -> JobStatus | None:
        """新しいジョブを running で登録する。同じ道案内を作成中なら None（作業ディレクトリを二重に使わないため）。"""
        with self._lock:
            if any(j.route_id == route_id and j.state == "running" for j in self._jobs.values()):
                return None
            job = JobStatus(job_id=uuid.uuid4().hex, state="running", route_id=route_id)
            self._jobs[job.job_id] = job
            return job

    def get(self, job_id: str) -> JobStatus | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **changes: Any) -> JobStatus:
        with self._lock:
            job = self._jobs[job_id].model_copy(update=changes)
            self._jobs[job_id] = job
            return job
