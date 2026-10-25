"""地面の点を Street View 画像の座標に投影する（ピンホールカメラ、地面は平面と仮定）。

画像の座標は左上 (0,0)、右下 (1,1)。Street View Static API の画像は fov が水平画角で、
正方形なら垂直画角も同じ。カメラの高さは撮影車のおおよその値。純関数のみ。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.services.creator.geo import LatLngT, bearing_deg, haversine_m

CAMERA_HEIGHT_M = 2.5
MIN_FORWARD_M = 1.0  # これより手前（足元）は投影しない


@dataclass(frozen=True)
class Camera:
    lat: float
    lng: float
    heading: float  # 向き（北 0、時計回り）
    fov: float = 90.0  # 水平画角（度）
    pitch: float = 0.0  # 上向き正（度）
    height_m: float = CAMERA_HEIGHT_M
    aspect: float = 1.0  # 幅 / 高さ


def project_ground(cam: Camera, pt: LatLngT) -> tuple[float, float] | None:
    """地面上の点 pt を画像座標にする。カメラの後ろや画角の外なら None。"""
    d = haversine_m((cam.lat, cam.lng), pt)
    if d <= 0:
        return None
    rel = math.radians((bearing_deg((cam.lat, cam.lng), pt) - cam.heading + 180.0) % 360.0 - 180.0)
    forward = d * math.cos(rel)  # 光軸方向の距離
    if forward < MIN_FORWARD_M:
        return None
    side = d * math.sin(rel)  # 右が正
    half_h = math.tan(math.radians(cam.fov) / 2)
    half_v = half_h / cam.aspect
    x = 0.5 + 0.5 * (side / forward) / half_h
    depression = math.atan2(cam.height_m, forward) + math.radians(cam.pitch)  # 光軸からの見下ろし角
    y = 0.5 + 0.5 * math.tan(depression) / half_v
    return (x, y)


def in_frame(xy: tuple[float, float] | None) -> bool:
    return xy is not None and 0.0 <= xy[0] <= 1.0 and 0.0 <= xy[1] <= 1.0
