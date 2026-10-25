"""QR の生成・読み取りと、参加者 URL の解釈。"""
import pytest

from app.imaging.qr import qr_png, read_qr
from app.services.follower.fetch import participant_url, plan_id_from_url


def test_QRはPNGになり_読み戻すと同じ文字列() -> None:
    png = qr_png("https://example.vercel.app/r/7298a7dd6554")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert read_qr(png) == "https://example.vercel.app/r/7298a7dd6554"


def test_空文字はエラー() -> None:
    with pytest.raises(ValueError):
        qr_png("")


def test_QRでない画像はNone() -> None:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (64, 64), "white").save(buf, format="PNG")
    assert read_qr(buf.getvalue()) is None


def test_参加者URLは末尾スラッシュの有無に関わらず同じ() -> None:
    assert participant_url("https://x.app/", "abc") == "https://x.app/r/abc"
    assert participant_url("https://x.app", "abc") == "https://x.app/r/abc"


@pytest.mark.parametrize("url,expected", [
    ("https://x.app/r/7298a7dd6554", "7298a7dd6554"),
    ("https://x.app/r/7298a7dd6554/", "7298a7dd6554"),
    ("http://localhost:5173/r/abc-1_2?x=1#y", "abc-1_2"),
])
def test_URLからIDを取り出す(url: str, expected: str) -> None:
    assert plan_id_from_url(url) == expected


@pytest.mark.parametrize("url", [
    "https://x.app/c/abc",            # 作る人の画面
    "https://x.app/r/",               # id なし
    "https://x.app/r/a/b",            # 深すぎる
    "https://x.app/r/a%2F..%2Fb",     # 許可外の文字
    "not a url",
])
def test_参加者URLでなければエラー(url: str) -> None:
    with pytest.raises(ValueError):
        plan_id_from_url(url)
