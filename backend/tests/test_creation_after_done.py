"""作成ジョブの後処理（map.png など）: 完了を知らせた後に呼び、失敗しても作成は成功のまま。"""
from pathlib import Path
from types import SimpleNamespace

from app.services.creator.creation import CreationJob, run_creation_job
from app.services.creator.jobs import JobStore
from app.services.creator.snapshot import snapshot, write_map_png


PLAN = SimpleNamespace(name="テスト", creator_id="c1")


class _Result:
    exploration = None


class _Pipeline:
    def run(self, plan, work_dir, rep=None):  # noqa: ANN001
        return _Result()


def _run(tmp_path: Path, monkeypatch, after_done) -> tuple[JobStore, str]:  # noqa: ANN001
    import app.services.creator.creation as creation_mod
    monkeypatch.setattr(creation_mod, "publish_plan", lambda *a, **k: None)
    store = JobStore()
    job = store.start("r1")
    run_creation_job(CreationJob(job.job_id, "r1", PLAN, tmp_path), store, _Pipeline(), None, None, after_done=after_done)
    return store, job.job_id


def test_完了を知らせてから後処理を呼ぶ(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    seen: list[str] = []
    holder: dict = {}

    def after(d: Path) -> None:
        seen.append(holder["store"].get(holder["id"]).state)

    import app.services.creator.creation as creation_mod
    monkeypatch.setattr(creation_mod, "publish_plan", lambda *a, **k: None)
    store = JobStore()
    job = store.start("r1")
    holder.update(store=store, id=job.job_id)
    run_creation_job(CreationJob(job.job_id, "r1", PLAN, tmp_path), store, _Pipeline(), None, None, after_done=after)
    assert seen == ["done"]


def test_後処理が失敗しても作成は成功のまま(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    def boom(d: Path) -> None:
        raise RuntimeError("firefox crashed")

    store, job_id = _run(tmp_path, monkeypatch, boom)
    assert store.get(job_id).state == "done"


def test_Firefoxが無ければmap_pngは作らない(tmp_path: Path) -> None:
    (tmp_path / "map.html").write_text("<html></html>", encoding="utf-8")
    assert snapshot(tmp_path, "map") is None and write_map_png(tmp_path) is None
    assert not (tmp_path / "map.png").exists()
