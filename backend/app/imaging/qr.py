"""QR コードの生成と読み取り。純粋な変換だけで、URL の意味は知らない。

生成: segno（純 Python）。読み取り: zxing-cpp（スマホのカメラの代わりにテストで使う）。
"""
from __future__ import annotations

from io import BytesIO

import segno

QR_SCALE = 8  # 1 モジュールのピクセル数。8 で 300px 前後、印刷にも足りる
QR_BORDER = 4  # 静止ゾーン（規格の最小値）


def qr_png(text: str, *, scale: int = QR_SCALE) -> bytes:
    """文字列（通常は URL）を QR コードの PNG にする。誤り訂正 M。"""
    if not text:
        raise ValueError("QR にする文字列が空です。")
    buf = BytesIO()
    segno.make(text, error="m").save(buf, kind="png", scale=scale, border=QR_BORDER)
    return buf.getvalue()


def read_qr(png: bytes) -> str | None:
    """PNG から QR の文字列を読む。見つからなければ None。"""
    import zxingcpp  # 読み取りはテスト・確認用なので、ここでだけ読み込む
    from PIL import Image

    result = zxingcpp.read_barcode(Image.open(BytesIO(png)).convert("RGB"))
    return result.text if result else None
