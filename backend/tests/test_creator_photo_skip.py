"""手順 4・5: 作成者の写真には矢印を描かず、VLM も呼ばない。"""
from pathlib import Path

from app.external.vlm.base import Evaluation
from app.schemas.exploration import Exploration
from app.services.creator.arrow import draw_arrows
from app.services.creator.contact import render_contact_html
from app.services.creator.landmark import evaluate_landmarks

FIXTURE = Path(__file__).parent / "fixtures" / "route_sample.json"


def with_creator_photo(tmp_path: Path) -> Exploration:
    e = Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    (tmp_path / "photos").mkdir()
    from PIL import Image
    Image.new("RGB", (64, 64), "white").save(tmp_path / "photos" / "p0.jpg")
    p0 = e.points[0].model_copy(update={"image": "photos/p0.jpg", "image_source": "creator_photo", "candidates": [], "landmark": "赤い看板"})
    return e.model_copy(update={"points": [p0, *e.points[1:]]})


def test_矢印は作成者の写真に描かない(tmp_path: Path) -> None:
    e2, stats = draw_arrows(with_creator_photo(tmp_path), tmp_path)
    assert stats.creator == [0] and 0 not in stats.drawn
    assert e2.points[0].arrow_image is None and e2.points[0].image == "photos/p0.jpg"
    assert not (tmp_path / "images" / "000_arrow.jpg").exists()


class CountingVlm:
    model = "dummy"

    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, prompt: str, images: list[bytes]) -> Evaluation:
        self.calls += 1
        raise AssertionError("作成者の写真で VLM が呼ばれた")


def test_VLMは作成者の写真を飛ばし_captionを目印にする(tmp_path: Path) -> None:
    vlm = CountingVlm()
    e2, stats = evaluate_landmarks(vlm, with_creator_photo(tmp_path), tmp_path)
    assert stats.creator == [0] and vlm.calls == 0
    assert e2.points[0].landmark == "赤い看板"


def test_captionが無ければフォールバック文(tmp_path: Path) -> None:
    e = with_creator_photo(tmp_path)
    e = e.model_copy(update={"points": [e.points[0].model_copy(update={"landmark": None}), *e.points[1:]]})
    e2, _ = evaluate_landmarks(None, e, tmp_path)
    assert e2.points[0].landmark and "次まで" in e2.points[0].landmark


def test_一覧には作成者の写真と表示する(tmp_path: Path) -> None:
    html = render_contact_html(with_creator_photo(tmp_path), "t")
    assert "作成者" in html and 'src="photos/p0.jpg"' in html
