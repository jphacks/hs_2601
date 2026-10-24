"""schemas/exploration.py が docs/route-exploration.md の形式を読み書きできることを確認する。"""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.exploration import Exploration

FIXTURE = Path(__file__).parent / "fixtures" / "route_sample.json"


def load_sample() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_読み込み() -> None:
    e = Exploration.model_validate(load_sample())
    assert e.version == 1
    assert len(e.points) == 2
    assert e.points[0].turn == "straight"
    assert e.points[1].heading is None


def test_書き出して読み直すと同じ(tmp_path: Path) -> None:
    e = Exploration.model_validate(load_sample())
    out = tmp_path / "route.json"
    out.write_text(e.model_dump_json(indent=2), encoding="utf-8")
    again = Exploration.model_validate_json(out.read_text(encoding="utf-8"))
    assert again == e


def test_turn_は4種のみ() -> None:
    bad = load_sample()
    bad["points"][0]["turn"] = "backward"
    with pytest.raises(ValidationError):
        Exploration.model_validate(bad)


def test_heading_は0以上360未満() -> None:
    bad = load_sample()
    bad["points"][0]["heading"] = 360.0
    with pytest.raises(ValidationError):
        Exploration.model_validate(bad)
