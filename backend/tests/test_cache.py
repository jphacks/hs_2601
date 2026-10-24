import httpx

from app.external.google.geocoding import GeocodingClient
from app.services.creator.cache import FileCache, cache_key
from app.services.creator.geocode import geocode_queries


def test_同じ入力なら同じキー_違えば違うキー() -> None:
    assert cache_key("geocode", "大阪駅") == cache_key("geocode", "大阪駅")
    assert cache_key("geocode", "大阪駅") != cache_key("geocode", "京都駅")
    assert cache_key("routes", [(1.0, 2.0)]) != cache_key("routes", [(2.0, 1.0)])


def test_jsonとbytesを保存して読める(tmp_path) -> None:
    c = FileCache(tmp_path, "t")
    assert c.get_json("k") is None
    c.set_json("k", {"a": "値"})
    assert c.get_json("k") == {"a": "値"}
    c.set_bytes("img", b"\xff\xd8")
    assert c.get_bytes("img") == b"\xff\xd8"


def test_2回目はAPIを叩かない(tmp_path) -> None:
    calls = 0

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"status": "OK", "results": [
            {"formatted_address": "x", "geometry": {"location": {"lat": 34.7, "lng": 135.5}}, "place_id": "p"}]})

    client = GeocodingClient("k", http=httpx.Client(transport=httpx.MockTransport(handler)))
    cache = FileCache(tmp_path, "google")
    a = geocode_queries(client, ["大阪駅"], cache)
    b = geocode_queries(client, ["大阪駅"], cache)
    assert calls == 1
    assert a.places == b.places
    geocode_queries(client, ["大阪駅"])  # キャッシュ無しなら叩く
    assert calls == 2
