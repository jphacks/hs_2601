"""ステップ 10: 保存した写真列の参加者 URL を QR コードにして qr.png に出す。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.imaging.qr import qr_png
from app.services.follower.fetch import participant_url

QR_FILENAME = "qr.png"


@dataclass(frozen=True)
class QrOutput:
    url: str
    path: Path


def write_qr(out_dir: Path, base_url: str, plan_id: str) -> QrOutput:
    url = participant_url(base_url, plan_id)
    path = out_dir / QR_FILENAME
    path.write_bytes(qr_png(url))
    return QrOutput(url, path)
