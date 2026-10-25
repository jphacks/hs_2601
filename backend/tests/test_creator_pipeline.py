"""作成パイプライン（services/creator/pipeline.py）を外部 API をモックして通す。工程の通知順も確かめる。"""
import json
from pathlib import Path

import httpx
import pytest

import app.external.vlm.gemini as gemini_mod
from app.external.google.geocoding import GeocodingClient
from app.external.google.routes import RoutesClient
from app.external.google.street_view import StreetViewClient
from app.external.vlm.base import VlmError
from app.external.vlm.gemini import GeminiClient
from app.schemas.creator_input import PlanInput
from app.services.creator.pipeline import PhotoPipeline, PipelineClients, Reporter
from tests.test_photos_flow import google_handler, vlm_handler, write_input


def clients(make_vlm=None) -> PipelineClients:
    g = httpx.Client(transport=httpx.MockTransport(google_handler))
    return PipelineClients(geocoding=GeocodingClient("k", http=g), routes=RoutesClient("k", http=g),
                           street_view=StreetViewClient("k", http=g), make_vlm=make_vlm)


def test_写真入力から全工程を回し_工程を順に知らせる(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_mod.time, "sleep", lambda s: None)
    write_input(tmp_path)
    plan = PlanInput.model_validate_json((tmp_path / "photos.json").read_text(encoding="utf-8"))
    v = httpx.Client(transport=httpx.MockTransport(vlm_handler))
    steps: list[str] = []
    lines: list[str] = []

    r = PhotoPipeline(make_clients=lambda: clients(lambda: GeminiClient("gk", http=v))).run(
        plan, tmp_path, Reporter(on_step=steps.append, log=lines.append))

    assert steps == ["geocode", "route", "streetview", "landmark", "arrow"]
    assert lines[0].startswith("[2/7] geocode: S (") and "写真 2 枚" in lines[0]
    assert any(line.startswith("[7/7] arrow:") for line in lines)
    assert [p.creator_photo.id for p in r.exploration.points if p.creator_photo] == ["p0", "p1"]
    saved = json.loads((tmp_path / "route.json").read_text(encoding="utf-8"))
    assert len(saved["points"]) == len(r.exploration.points) and (tmp_path / "contact.html").is_file()


def test_VLMが作れなくてもフォールバック文で続ける(tmp_path: Path) -> None:
    write_input(tmp_path)
    plan = PlanInput.model_validate_json((tmp_path / "photos.json").read_text(encoding="utf-8"))

    def no_vlm():
        raise VlmError("キーなし")

    lines: list[str] = []
    r = PhotoPipeline(make_clients=lambda: clients(no_vlm)).run(plan, tmp_path, Reporter(log=lines.append))
    assert any("VLM なし（キーなし）" in line for line in lines)
    assert all(p.landmark for p in r.exploration.points)
