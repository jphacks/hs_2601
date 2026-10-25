"""手順 10: 作成者写真を通る一括実行を、外部 API をすべてモックして通す（photos.json → 保存形式まで）。

Routes は区間ごとに直線を返す。Street View は常に画像あり。VLM は常に最初の候補を選ぶ。
写真地点は写真のまま（Street View・VLM・矢印なし）、他の地点は従来どおり矢印入りになることを確認する。
"""
import json
from pathlib import Path

import httpx
import polyline as polyline_codec
from PIL import Image

from app.external.google.routes import RoutesClient
from app.external.google.street_view import StreetViewClient
from app.external.vlm.gemini import GeminiClient
from app.schemas.creator_input import PlanInput
from app.services.creator.arrow import draw_arrows
from app.services.creator.landmark import evaluate_landmarks
from app.services.creator.legs import merge_legs, plan_legs, split_legs
from app.services.creator.photos import load_plan_input
from app.services.creator.publish import publish_plan
from app.services.creator.streetview import StreetViewOptions, fetch_candidates
from app.schemas.exploration import Place
from tests.test_publish import MemoryRepo, MemoryStorage

A, B, C, D = (34.7000, 135.5000), (34.7000, 135.5020), (34.7020, 135.5020), (34.7020, 135.5040)


def jpeg_bytes(color: str) -> bytes:
    from io import BytesIO
    buf = BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, format="JPEG")
    return buf.getvalue()


def google_handler(req: httpx.Request) -> httpx.Response:
    path = req.url.path
    if "computeRoutes" in path:
        body = json.loads(req.content)
        o, d = body["origin"]["location"]["latLng"], body["destination"]["location"]["latLng"]
        pts = [(o["latitude"], o["longitude"]), (d["latitude"], d["longitude"])]
        return httpx.Response(200, json={"routes": [{"distanceMeters": 100, "duration": "60s",
                                                      "polyline": {"encodedPolyline": polyline_codec.encode(pts, precision=5)},
                                                      "legs": [{"steps": [{"startLocation": {"latLng": o}, "endLocation": {"latLng": d}, "distanceMeters": 100,
                                                                           "navigationInstruction": {"maneuver": "DEPART", "instructions": "進む"},
                                                                           "polyline": {"encodedPolyline": polyline_codec.encode(pts, precision=5)}}]}]}]})
    if path.endswith("/metadata"):
        lat, lng = map(float, req.url.params["location"].split(","))
        return httpx.Response(200, json={"status": "OK", "pano_id": f"P{lat:.4f}{lng:.4f}", "date": "2024-01", "copyright": "© 2026 Google",
                                         "location": {"lat": lat, "lng": lng}})
    return httpx.Response(200, content=jpeg_bytes("gray"), headers={"content-type": "image/jpeg"})


def vlm_handler(req: httpx.Request) -> httpx.Response:
    n = len(json.loads(req.content)["contents"][0]["parts"]) - 1
    evals = [{"index": i, "on_walkway": True, "path_blocked": False, "here_score": 4, "arrow_score": 4, "landmark": f"目印{i}", "reason": "",
              "arrow_path": [{"x": 0.5, "y": 0.95}, {"x": 0.5, "y": 0.6}, {"x": 0.2, "y": 0.5}]} for i in range(n)]
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps({"evaluations": evals, "best_index": 0})}]}}]})


def write_input(d: Path) -> None:
    (d / "photos").mkdir(parents=True)
    (d / "photos" / "p0.jpg").write_bytes(jpeg_bytes("red"))
    (d / "photos" / "p1.jpg").write_bytes(jpeg_bytes("blue"))
    plan = PlanInput(name="写真テスト", origin={"query": "S", "lat": A[0], "lng": A[1]}, destination={"query": "G", "lat": D[0], "lng": D[1]},
                     photos=[{"id": "p0", "seq": 0, "image": "photos/p0.jpg", "lat": B[0], "lng": B[1]},
                             {"id": "p1", "seq": 1, "image": "photos/p1.jpg", "lat": C[0], "lng": C[1], "caption": "青い扉"}])
    (d / "photos.json").write_text(plan.model_dump_json(), encoding="utf-8")


def test_写真を通る一括実行(tmp_path: Path) -> None:
    write_input(tmp_path)
    g = httpx.Client(transport=httpx.MockTransport(google_handler))
    import app.external.vlm.gemini as gm
    gm.time.sleep = lambda s: None
    v = httpx.Client(transport=httpx.MockTransport(vlm_handler))

    plan = load_plan_input(tmp_path)
    origin = Place(query=plan.origin.query, lat=plan.origin.lat, lng=plan.origin.lng)
    dest = Place(query=plan.destination.query, lat=plan.destination.lat, lng=plan.destination.lng)
    legs = split_legs(origin, dest, plan.photos)
    outputs, warnings = plan_legs(RoutesClient("k", http=g), legs)
    assert len(outputs) == 3 and warnings == []
    e = merge_legs(legs, outputs, origin, dest).exploration

    e, sv = fetch_candidates(StreetViewClient("k", http=g), e, tmp_path, StreetViewOptions())
    e, lm = evaluate_landmarks(GeminiClient("gk", http=v), e, tmp_path)
    e, ar = draw_arrows(e, tmp_path)

    photos = [p for p in e.points if p.image_source == "creator_photo"]
    others = [p for p in e.points if p.image_source != "creator_photo"]
    assert [p.creator_photo.id for p in photos] == ["p0", "p1"] and [p.turn for p in photos] == ["left", "right"]
    assert sv.skipped == [p.index for p in photos] and lm.creator == [p.index for p in photos] and ar.creator == [p.index for p in photos]
    assert all(p.image.startswith("photos/") and p.arrow_image is None and not p.candidates for p in photos)
    assert photos[1].landmark == "青い扉"
    assert all(p.arrow_image and p.candidates and p.landmark for p in others)

    rec = publish_plan(e, tmp_path, plan.name, MemoryRepo(), MemoryStorage()).record
    urls = [s.image_url for s in rec.plan.steps]
    assert all(urls) and len(urls) == len(e.points)
    # 写真地点は写真（photos/）、他は矢印入り（images/…_arrow.jpg）が上がっている
    assert urls[photos[0].index].endswith(f"/{photos[0].index:03d}.jpg")
