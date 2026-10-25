"""作成ジョブの本体: 作業ディレクトリでパイプラインを回し、下書きとして保存する。

バックグラウンドのスレッドで呼ばれる。例外は外に出さず、ジョブを failed にして利用者向けの文を入れる
（詳細はサーバーのログに残す）。
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.external.google.geocoding import GeocodingError
from app.external.google.routes import RoutesError
from app.external.google.street_view import StreetViewError
from app.external.supabase.rest import SupabaseError
from app.repositories.base import PhotoStorage, RoutePlanRepository
from app.schemas.creator_api import JobStep
from app.schemas.creator_input import PlanInput
from app.services.creator.jobs import JobStore
from app.services.creator.pipeline import PipelineResult, Reporter
from app.services.creator.publish import publish_plan

log = logging.getLogger(__name__)

STEP_LABEL: dict[str, str] = {
    "geocode": "地名の検索", "route": "経路の計算", "streetview": "街の画像の取得",
    "landmark": "目印の作成", "arrow": "矢印の描画", "save": "保存",
}


class PipelineRunner(Protocol):
    def run(self, plan: PlanInput, work_dir: Path, rep: Reporter = ...) -> PipelineResult: ...


@dataclass(frozen=True)
class CreationJob:
    job_id: str
    route_id: str
    plan: PlanInput
    work_dir: Path


def failure_message(err: Exception, step: JobStep | None) -> str:
    """利用者向けの日本語。内部の詳細（キーや URL）は出さない。"""
    where = f"{STEP_LABEL[step]}中に" if step else ""
    if isinstance(err, GeocodingError):
        return "出発地か目的地が見つかりませんでした。地名を変えて作り直してください。"
    if isinstance(err, ValueError) and step == "route":
        return "経路が見つかりませんでした。出発地・目的地・写真の位置を確かめてください。"
    if isinstance(err, (RoutesError, StreetViewError)):
        return f"{where}地図サービスへの問い合わせに失敗しました。しばらくしてから作り直してください。"
    if isinstance(err, SupabaseError):
        return "保存に失敗しました。しばらくしてから作り直してください。"
    return f"{where}失敗しました。しばらくしてから作り直してください。"


def run_creation_job(job: CreationJob, store: JobStore, pipeline: PipelineRunner,
                     repo: RoutePlanRepository, storage: PhotoStorage,
                     after_done: Callable[[Path], object] | None = None) -> None:
    """after_done は完了を知らせた後に作業ディレクトリで呼ぶ（map.png など、待たせたくない後処理）。"""
    def on_step(step: JobStep) -> None:
        store.update(job.job_id, step=step)

    def log_line(msg: str) -> None:
        log.info("job %s: %s", job.job_id, msg)

    try:
        result = pipeline.run(job.plan, job.work_dir, Reporter(on_step=on_step, log=log_line))
        on_step("save")
        publish_plan(result.exploration, job.work_dir, job.plan.name, repo, storage, plan_id=job.route_id,
                     status="draft", creator_id=job.plan.creator_id)
    except Exception as err:  # noqa: BLE001 ジョブのスレッドでは全て受けて failed にする
        current = store.get(job.job_id)
        step = current.step if current else None
        log.exception("job %s (route %s) failed at %s", job.job_id, job.route_id, step)
        store.update(job.job_id, state="failed", message=failure_message(err, step))
        return
    store.update(job.job_id, state="done")
    if after_done is not None:
        try:
            after_done(job.work_dir)
        except Exception:  # noqa: BLE001 後処理の失敗で道案内の作成を失敗にしない
            log.exception("job %s: 後処理に失敗しました", job.job_id)
