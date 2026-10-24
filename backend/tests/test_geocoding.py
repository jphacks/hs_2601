"""Geocoding クライアントを、HTTP をモックして確認する（API キー不要）。"""
import json
from pathlib import Path

import httpx
import pytest

from app.external.google.geocoding import GeocodingClient, GeocodingError, parse_geocode_response
from app.services.creator.geocode import geocode_from_raw, geocode_queries

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "geocode_sample.json").read_text(encoding="utf-8"))


def make_client(handler) -> GeocodingClient:
    transport = httpx.MockTransport(handler)
    return GeocodingClient("dummy-key", http=httpx.Client(transport=transport))


def test_住所が座標になる() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.params["address"] == "大阪駅"
        assert req.url.params["key"] == "dummy-key"
        assert req.url.params["language"] == "ja"
        return httpx.Response(200, json=FIXTURE["大阪駅"])

    r = make_client(handler).geocode("大阪駅")
    assert (round(r.lat, 4), round(r.lng, 4)) == (34.7025, 135.496)
    assert "梅田" in r.formatted_address


def test_ZERO_RESULTS_はエラー() -> None:
    with pytest.raises(GeocodingError, match="ZERO_RESULTS"):
        parse_geocode_response("存在しない場所", {"status": "ZERO_RESULTS", "results": []})


def test_REQUEST_DENIED_はキーの問題として伝わる() -> None:
    body = {"status": "REQUEST_DENIED", "error_message": "The provided API key is invalid."}
    with pytest.raises(GeocodingError, match="REQUEST_DENIED.*invalid"):
        parse_geocode_response("大阪駅", body)


def test_複数地名をまとめて座標にする() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=FIXTURE[req.url.params["address"]])

    out = geocode_queries(make_client(handler), ["大阪駅", "グランフロント大阪"])
    assert [p.query for p in out.places] == ["大阪駅", "グランフロント大阪"]
    assert set(out.raw) == {"大阪駅", "グランフロント大阪"}


def test_fixture_から復元できる() -> None:
    out = geocode_from_raw(FIXTURE)
    assert len(out.places) == 2
    assert out.places[1].query == "グランフロント大阪"
