"""VLM クライアントと目印選定を、HTTP をモックして確認する（API キー不要）。"""
import json
from pathlib import Path

import httpx
import pytest

from app.external.vlm.base import VlmError, parse_evaluation
from app.external.vlm.gemini import GeminiClient
from app.external.vlm.claude import ClaudeClient
from app.schemas.exploration import Exploration, ImageCandidate, StreetViewMeta
from app.services.creator.landmark import build_prompt, evaluate_landmarks, fallback_text

FIXTURE = Path(__file__).parent / "fixtures" / "route_sample.json"
JPEG = b"\xff\xd8\xff\xe0fake"

GOOD = {"evaluations": [
    {"index": 0, "landmark_score": 2, "turn_score": 3, "view_score": 2, "landmark": "目印なし", "reason": "壁だけ"},
    {"index": 1, "landmark_score": 5, "turn_score": 4, "view_score": 5, "landmark": "赤い看板のコンビニ", "reason": "看板が大きい"},
], "best_index": 1}


def test_parse_evaluation_はコードフェンスも許す() -> None:
    ev = parse_evaluation("```json\n" + json.dumps(GOOD, ensure_ascii=False) + "\n```", 2)
    assert ev.best_index == 1
    assert ev.evaluations[1].landmark_text == "赤い看板のコンビニ"


def test_parse_evaluation_はbest_indexが不正なら点数で決める() -> None:
    body = {**GOOD, "best_index": 9}
    assert parse_evaluation(json.dumps(body), 2).best_index == 1


def test_parse_evaluation_はJSONでなければエラー() -> None:
    with pytest.raises(VlmError):
        parse_evaluation("わかりません", 2)


def test_gemini_はJSONモードで呼び_429で再試行する() -> None:
    calls = 0

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert req.url.params["key"] == "gk"
        body = json.loads(req.content)
        assert body["generationConfig"]["response_mime_type"] == "application/json"
        assert len(body["contents"][0]["parts"]) == 3  # text + 2 images
        if calls == 1:
            return httpx.Response(429, json={"error": "rate"})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(GOOD)}]}}]})

    import app.external.vlm.gemini as g
    g.time.sleep = lambda s: None  # 待ちを省略
    c = GeminiClient("gk", http=httpx.Client(transport=httpx.MockTransport(handler)))
    ev = c.evaluate("p", [JPEG, JPEG])
    assert ev.best_index == 1 and calls == 2


def test_claude_はmessages形式で呼ぶ() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.headers["x-api-key"] == "ck"
        body = json.loads(req.content)
        assert body["messages"][0]["content"][1]["type"] == "image"
        return httpx.Response(200, json={"content": [{"type": "text", "text": json.dumps(GOOD)}]})

    c = ClaudeClient("ck", http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert c.evaluate("p", [JPEG, JPEG]).best_index == 1


class FakeVlm:
    model = "fake"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def evaluate(self, prompt, images):
        self.calls += 1
        if self.fail:
            raise VlmError("boom")
        return parse_evaluation(json.dumps(GOOD), len(images))


def make_point_with_candidates(tmp_path: Path) -> Exploration:
    e = Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    (tmp_path / "images").mkdir()
    cands = []
    for i in range(2):
        rel = f"images/000_c{i}.jpg"
        (tmp_path / rel).write_bytes(JPEG + bytes([i]))
        cands.append(ImageCandidate(image=rel, heading_mode="bisector",
                                    street_view=StreetViewMeta(pano_id=f"P{i}", heading=10.0)))
    p0 = e.points[0].model_copy(update={"candidates": cands, "image": cands[0].image, "turn": "right", "instruction": "右折する"})
    return e.model_copy(update={"points": [p0, e.points[1]]})


def test_最良の候補が採用され目印文が入る(tmp_path: Path) -> None:
    e = make_point_with_candidates(tmp_path)
    vlm = FakeVlm()
    e2, stats = evaluate_landmarks(vlm, e, tmp_path)
    p = e2.points[0]
    assert p.chosen_candidate == 1
    assert p.image == "images/000_c1.jpg"
    assert p.landmark == "赤い看板のコンビニ"
    assert p.candidates[0].score is not None and p.candidates[0].score.turn == 3 and p.candidates[0].score.view == 2
    assert stats.evaluated == [0] and stats.fallback == [1]  # 候補の無い目的地はフォールバック
    assert e2.points[1].landmark == "目的地です"
    assert e.points[0].chosen_candidate is None  # 元は変更されない


def test_VLM失敗時はフォールバック文(tmp_path: Path) -> None:
    e = make_point_with_candidates(tmp_path)
    e2, stats = evaluate_landmarks(FakeVlm(fail=True), e, tmp_path)
    assert e2.points[0].landmark == "右折する（次まで 120 m）"
    assert 0 in stats.errors and e2.points[0].chosen_candidate is None


def test_キャッシュがあれば2回目は呼ばない(tmp_path: Path) -> None:
    from app.services.creator.cache import FileCache
    e = make_point_with_candidates(tmp_path)
    vlm = FakeVlm()
    cache = FileCache(tmp_path / "cache", "vlm")
    evaluate_landmarks(vlm, e, tmp_path, cache)
    evaluate_landmarks(vlm, e, tmp_path, cache)
    assert vlm.calls == 1


def test_fallback_text_とプロンプト() -> None:
    e = Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    p = e.points[0].model_copy(update={"turn": "left", "instruction": "", "distance_to_next_m": 50})
    assert fallback_text(p) == "左折（次まで 50 m）"
    prompt = build_prompt(p, 3)
    assert "3 枚" in prompt and "左折" in prompt and "best_index" in prompt and "view_score" in prompt


def test_view_score_が無ければ3扱い() -> None:
    body = {"evaluations": [{"index": 0, "landmark_score": 4, "turn_score": 4, "landmark": "x", "reason": "y"}], "best_index": 0}
    assert parse_evaluation(json.dumps(body), 1).evaluations[0].view == 3
