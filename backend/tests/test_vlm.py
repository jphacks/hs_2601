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
    {"index": 0, "on_walkway": True, "here_score": 2, "arrow_score": 2, "landmark": "目印なし", "reason": "壁だけ", "arrow_path": []},
    {"index": 1, "on_walkway": True, "here_score": 5, "arrow_score": 5, "landmark": "赤い看板のコンビニ", "reason": "看板が大きい",
     "arrow_path": [{"x": 0.5, "y": 0.95}, {"x": 0.5, "y": 0.6}, {"x": 1.2, "y": 0.5}]},
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
    assert p.candidates[0].score is not None and p.candidates[0].score.here == 2 and p.candidates[0].score.arrow == 2
    best = p.candidates[1].score
    assert best is not None and [(a.x, a.y) for a in best.arrow_path] == [(0.5, 0.95), (0.5, 0.6), (1.0, 0.5)]  # 範囲外は丸める
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
    assert "3 枚" in prompt and "左折" in prompt and "best_index" in prompt and "here_score" in prompt and "等間隔" in prompt
    assert "グループ: なし" in prompt  # 候補が無いときはグループなし


def test_撮影地点グループがプロンプトに入る() -> None:
    from app.services.creator.landmark import pano_groups
    e = Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    cands = [ImageCandidate(image=f"images/0_c{i}.jpg", heading_mode="bisector", street_view=StreetViewMeta(pano_id=pid, heading=0))
             for i, pid in enumerate(["A", "A", "B", "A"])]
    p = e.points[0].model_copy(update={"candidates": cands})
    assert pano_groups(p) == "画像 0,1,3 / 画像 2"


def test_経路が無くても解釈できる() -> None:
    body = {"evaluations": [{"index": 0, "here_score": 4, "arrow_score": 4, "landmark": "x", "reason": "y"}], "best_index": 0}
    ev = parse_evaluation(json.dumps(body), 1).evaluations[0]
    assert ev.here == 4 and ev.arrow_path == []


def test_立てない候補は点数が高くても選ばない() -> None:
    body = {"evaluations": [
        {"index": 0, "on_walkway": False, "here_score": 5, "arrow_score": 5, "landmark": "船上", "reason": "川", "arrow_path": []},
        {"index": 1, "on_walkway": True, "here_score": 3, "arrow_score": 3, "landmark": "歩道", "reason": "ok", "arrow_path": []},
    ], "best_index": 0}  # モデルが船上を選んでも
    ev = parse_evaluation(json.dumps(body), 2)
    assert ev.best_index == 1
    assert ev.evaluations[0].on_walkway is False


def test_全部立てないならモデルの選択を尊重し_範囲外なら点数で選ぶ() -> None:
    evals = [
        {"index": 0, "on_walkway": False, "here_score": 2, "arrow_score": 2, "landmark": "", "reason": "", "arrow_path": []},
        {"index": 1, "on_walkway": "false", "here_score": 4, "arrow_score": 4, "landmark": "", "reason": "", "arrow_path": []},
    ]
    assert parse_evaluation(json.dumps({"evaluations": evals, "best_index": 0}), 2).best_index == 0
    assert parse_evaluation(json.dumps({"evaluations": evals, "best_index": 9}), 2).best_index == 1


def test_同じパノラマの候補が1枚でも立てないなら全部除外(tmp_path: Path) -> None:
    e = Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    (tmp_path / "images").mkdir()
    cands = []
    for i, pano in enumerate(["P_STAIRS", "P_STAIRS", "P_PLAZA"]):
        rel = f"images/000_c{i}.jpg"
        (tmp_path / rel).write_bytes(JPEG + bytes([i]))
        cands.append(ImageCandidate(image=rel, heading_mode="bisector", street_view=StreetViewMeta(pano_id=pano, heading=10.0)))
    p0 = e.points[0].model_copy(update={"candidates": cands, "image": cands[0].image, "turn": "left"})
    body = {"evaluations": [
        {"index": 0, "on_walkway": False, "here_score": 5, "arrow_score": 5, "landmark": "柵の内側", "reason": "", "arrow_path": []},
        {"index": 1, "on_walkway": True, "here_score": 5, "arrow_score": 5, "landmark": "広場", "reason": "", "arrow_path": []},
        {"index": 2, "on_walkway": True, "here_score": 3, "arrow_score": 3, "landmark": "歩道", "reason": "", "arrow_path": []},
    ], "best_index": 1}

    class Vlm:
        model = "fake"
        def evaluate(self, prompt, images):
            return parse_evaluation(json.dumps(body), len(images))

    e2, _ = evaluate_landmarks(Vlm(), e.model_copy(update={"points": [p0]}), tmp_path)
    p = e2.points[0]
    assert p.chosen_candidate == 2  # 同じ階段パノラマの c1 は点数が高くても除外
    assert p.candidates[1].score is not None and p.candidates[1].score.on_walkway is False


def test_進めない候補は除外される() -> None:
    body = {"evaluations": [
        {"index": 0, "on_walkway": True, "path_blocked": True, "here_score": 5, "arrow_score": 5, "landmark": "柵", "reason": "", "arrow_path": []},
        {"index": 1, "on_walkway": True, "path_blocked": False, "here_score": 3, "arrow_score": 3, "landmark": "歩道", "reason": "", "arrow_path": []},
    ], "best_index": 0}
    ev = parse_evaluation(json.dumps(body), 2)
    assert ev.best_index == 1 and ev.evaluations[0].path_blocked is True
