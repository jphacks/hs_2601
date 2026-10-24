"""ステップ 5: route.json の各点に Street View 画像を付ける。

- heading（交差点に近づく向き）で撮る。
- パノラマの選び方: 交差点の手前 offset_m から数 m ずつ後ろに下がりながら Metadata API で候補を探し、
  Google 公式撮影のものを優先する（ユーザー投稿は夜景・屋内・船上などが混ざるため）。
  公式が見つからなければ最初に見つかった候補を使う。
- 画像が無い地点は image を null のままにする。
- 作成者の写真（image_source == creator_photo）はそのまま触らない。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from app.external.google.street_view import PanoMeta, StreetViewClient
from app.schemas.exploration import Exploration, ExplorationPoint, ImageCandidate, StreetViewMeta
from app.services.creator.cache import FileCache, cache_key
from app.services.creator.geo import destination_point, heading_diff_deg

IMAGE_DIR = "images"

HeadingMode = Literal["approach", "bisector", "departure"]


def camera_heading(p: ExplorationPoint, mode: HeadingMode) -> float:
    """カメラを向ける方位。
    approach:  進入方向（まっすぐ先が写る。曲がる先は枠外になりやすい）
    bisector:  進入方向と退出方向の中間（直進方向と曲がる先の両方が枠に入る）
    departure: 退出方向（入る道が正面に写る）
    """
    h_in = p.heading if p.heading is not None else 0.0
    if mode == "approach" or p.heading_out is None:
        return h_in
    if mode == "departure":
        return p.heading_out
    return (h_in + heading_diff_deg(h_in, p.heading_out) / 2.0) % 360.0


@dataclass(frozen=True)
class StreetViewOptions:
    offset_m: float = 0.0  # 最初に試す位置（交差点の何 m 手前か）
    search_step_m: float = 8.0  # 公式が無いとき、さらに何 m ずつ下がって探すか
    search_tries: int = 4  # 探索回数（offset_m を含む）
    prefer_official: bool = True
    heading_mode: HeadingMode = "bisector"
    fov: int = 90
    pitch: int = 0
    size: str = "640x640"
    radius_m: int = 30


@dataclass(frozen=True)
class StreetViewStats:
    fetched: list[int] = field(default_factory=list)
    missing: list[int] = field(default_factory=list)
    skipped: list[int] = field(default_factory=list)


def _position(p: ExplorationPoint, heading: float, back_m: float) -> tuple[float, float]:
    """候補位置。通常は進入方向の手前に下がる。出発点は後ろが経路外なので前方に進む。"""
    if back_m <= 0:
        return (p.lat, p.lng)
    direction = heading if p.maneuver.upper() == "DEPART" else (heading + 180.0) % 360.0
    return destination_point((p.lat, p.lng), direction, back_m)


def choose_pano(client: StreetViewClient, p: ExplorationPoint, heading: float, opt: StreetViewOptions) -> tuple[PanoMeta, float] | None:
    """候補位置を順に試し、(メタ情報, 使った offset) を返す。無ければ None。"""
    first: tuple[PanoMeta, float] | None = None
    seen: set[str] = set()
    for i in range(opt.search_tries):
        back = opt.offset_m + i * opt.search_step_m
        lat, lng = _position(p, heading, back)
        meta = client.metadata(lat, lng, radius_m=opt.radius_m)
        if meta is None or meta.pano_id in seen:
            continue
        seen.add(meta.pano_id)
        if not opt.prefer_official or meta.is_official:
            return meta, back
        if first is None:
            first = (meta, back)
    return first


def fetch_point_image(
    client: StreetViewClient, p: ExplorationPoint, out_dir: Path, opt: StreetViewOptions, cache: FileCache | None = None
) -> ExplorationPoint:
    """1 点分。画像があれば保存して新しい ExplorationPoint を返す（元は変更しない）。"""
    approach = p.heading if p.heading is not None else 0.0  # パノラマ探索は進入方向の手前で行う
    heading = camera_heading(p, opt.heading_mode)  # 撮る向きはモードで決める
    chosen = choose_pano(client, p, approach, opt)
    if chosen is None:
        return p.model_copy(update={"image": None, "image_source": None, "street_view": None})
    meta, back = chosen
    key = cache_key("streetview", meta.pano_id, round(heading, 1), opt.fov, opt.pitch, opt.size)
    data = cache.get_bytes(key) if cache else None
    if data is None:
        data = client.image(meta.pano_id, heading=heading, fov=opt.fov, pitch=opt.pitch, size=opt.size)
        if cache:
            cache.set_bytes(key, data)
    rel = f"{IMAGE_DIR}/{p.index:03d}.jpg"
    (out_dir / rel).parent.mkdir(parents=True, exist_ok=True)
    (out_dir / rel).write_bytes(data)
    return p.model_copy(
        update={
            "image": rel,
            "image_source": "street_view",
            "street_view": StreetViewMeta(
                pano_id=meta.pano_id, date=meta.date, heading=heading, fov=opt.fov, pitch=opt.pitch,
                copyright=meta.copyright, offset_m=back,
            ),
        }
    )


def fetch_images(
    client: StreetViewClient, e: Exploration, out_dir: Path, opt: StreetViewOptions | None = None, cache: FileCache | None = None
) -> tuple[Exploration, StreetViewStats]:
    opt = opt or StreetViewOptions()
    fetched: list[int] = []
    missing: list[int] = []
    skipped: list[int] = []
    points: list[ExplorationPoint] = []
    for p in e.points:
        if p.image_source == "creator_photo":
            skipped.append(p.index)
            points.append(p)
            continue
        q = fetch_point_image(client, p, out_dir, opt, cache)
        (fetched if q.image else missing).append(p.index)
        points.append(q)
    return e.model_copy(update={"points": points}), StreetViewStats(fetched, missing, skipped)


# ---------------------------------------------------------------------------
# 候補を複数枚取る（ステップ 7 で VLM が選ぶ）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Variant:
    heading_mode: HeadingMode
    offset_m: float = 0.0
    fov: int = 90


TARGET_CANDIDATES = 8

# 曲がり角用。重複を除いて TARGET_CANDIDATES 枚になるまで上から順に試す
TURN_VARIANTS: tuple[Variant, ...] = (
    Variant("bisector", 0.0),        # 直進方向と曲がる先の両方
    Variant("approach", 0.0),        # 進入方向。正面の目印が大きい
    Variant("departure", 0.0),       # 入る道が正面
    Variant("bisector", 10.0),       # 10 m 手前から。交差点が前方に見える
    Variant("approach", 10.0),
    Variant("bisector", 0.0, 110),   # 広角。曲がる先が枠に入りやすい
    Variant("bisector", 20.0),
    Variant("approach", 0.0, 110),
    Variant("bisector", 5.0),
    Variant("departure", 10.0),
    Variant("approach", 20.0),
    Variant("bisector", 10.0, 110),
    Variant("bisector", 30.0),
    Variant("approach", 30.0),
)

# 出発点・目的地用。向きの違いが無いので、位置（出発点は前方、目的地は手前）と画角を変える
ENDPOINT_VARIANTS: tuple[Variant, ...] = (
    Variant("approach", 0.0),
    Variant("approach", 10.0),
    Variant("approach", 20.0),
    Variant("approach", 0.0, 110),
    Variant("approach", 30.0),
    Variant("approach", 10.0, 110),
    Variant("approach", 40.0),
    Variant("approach", 50.0),
    Variant("approach", 5.0),
    Variant("approach", 15.0),
    Variant("approach", 20.0, 110),
    Variant("approach", 60.0),
    Variant("approach", 70.0),
    Variant("approach", 80.0),
)

DEFAULT_VARIANTS = TURN_VARIANTS  # 互換のため


def variants_for(p: ExplorationPoint) -> tuple[Variant, ...]:
    if p.maneuver.upper() == "DEPART" or p.turn == "arrive" or p.heading_out is None:
        return ENDPOINT_VARIANTS
    return TURN_VARIANTS


def fetch_point_candidates(
    client: StreetViewClient, p: ExplorationPoint, out_dir: Path, base: StreetViewOptions,
    variants: tuple[Variant, ...] | None = None, cache: FileCache | None = None,
    target: int = TARGET_CANDIDATES,
) -> ExplorationPoint:
    """1 地点について variants を上から順に試し、重複を除いて target 枚まで candidates に入れる。
    同じパノラマ・同じ向き・同じ画角は重複。image には先頭の候補を仮採用する。"""
    approach = p.heading if p.heading is not None else 0.0
    cands: list[ImageCandidate] = []
    seen: set[tuple[str, float, int]] = set()
    for v in variants or variants_for(p):
        if len(cands) >= target:
            break
        opt = StreetViewOptions(**{**base.__dict__, "offset_m": v.offset_m, "heading_mode": v.heading_mode, "fov": v.fov})
        heading = camera_heading(p, v.heading_mode)
        chosen = choose_pano(client, p, approach, opt)
        if chosen is None:
            continue
        meta, back = chosen
        sig = (meta.pano_id, round(heading), v.fov)
        if sig in seen:
            continue
        seen.add(sig)
        key = cache_key("streetview", meta.pano_id, round(heading, 1), opt.fov, opt.pitch, opt.size)
        data = cache.get_bytes(key) if cache else None
        if data is None:
            data = client.image(meta.pano_id, heading=heading, fov=opt.fov, pitch=opt.pitch, size=opt.size)
            if cache:
                cache.set_bytes(key, data)
        rel = f"{IMAGE_DIR}/{p.index:03d}_c{len(cands)}.jpg"
        (out_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        (out_dir / rel).write_bytes(data)
        cands.append(ImageCandidate(
            image=rel, heading_mode=v.heading_mode,
            street_view=StreetViewMeta(pano_id=meta.pano_id, date=meta.date, heading=heading, fov=opt.fov,
                                       pitch=opt.pitch, copyright=meta.copyright, offset_m=back),
        ))
    if not cands:
        return p.model_copy(update={"image": None, "image_source": None, "street_view": None, "candidates": []})
    first = cands[0]
    return p.model_copy(update={
        "image": first.image, "image_source": "street_view", "street_view": first.street_view,
        "candidates": cands, "chosen_candidate": None,
    })


def fetch_candidates(
    client: StreetViewClient, e: Exploration, out_dir: Path, base: StreetViewOptions | None = None,
    variants: tuple[Variant, ...] | None = None, cache: FileCache | None = None,
) -> tuple[Exploration, StreetViewStats]:
    base = base or StreetViewOptions()
    fetched: list[int] = []
    missing: list[int] = []
    skipped: list[int] = []
    points: list[ExplorationPoint] = []
    for p in e.points:
        if p.image_source == "creator_photo":
            skipped.append(p.index)
            points.append(p)
            continue
        q = fetch_point_candidates(client, p, out_dir, base, variants, cache)
        (fetched if q.candidates else missing).append(p.index)
        points.append(q)
    return e.model_copy(update={"points": points}), StreetViewStats(fetched, missing, skipped)
