"""写真列を作る一連の処理（geocode → route → turns → streetview → landmark → arrow）。

CLI（scripts/explore_route.py）と作る人 API のジョブの両方から使う。
- 外部クライアントは ``PipelineClients`` にまとめて渡す（テストでは差し替える）。
- 進み具合は ``Reporter`` で知らせる。``on_step`` は工程の切り替わり、``log`` は CLI と同じ 1 行の経過表示。
- Exploration は model_copy で作り直し、元は変更しない。
保存（publish）はここでは行わない。呼び出し側が publish_plan を呼ぶ。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from app.core.config import Settings
from app.external.google.geocoding import GeocodingClient
from app.external.google.routes import RoutesClient
from app.external.google.street_view import StreetViewClient
from app.external.vlm.base import VlmClient, VlmError
from app.external.vlm.factory import make_vlm_client
from app.schemas.creator_input import PlanInput, goal_from_last_photo
from app.schemas.exploration import Exploration, Place
from app.services.creator.arrow import draw_arrows
from app.services.creator.cache import FileCache
from app.services.creator.route_map import render_route_map
from app.services.creator.contact import render_contact_html
from app.services.creator.geocode import geocode_queries, resolve_places
from app.services.creator.landmark import evaluate_landmarks
from app.services.creator.legs import merge_legs, plan_legs, split_legs
from app.services.creator.photos import PHOTOS_JSON, normalize_photo
from app.services.creator.route import compute_route
from app.services.creator.streetview import StreetViewOptions, fetch_candidates
from app.services.creator.turns import extract_turns

Step = Literal["geocode", "route", "streetview", "landmark", "arrow", "save"]


def _noop(_: Any) -> None:
    return None


@dataclass(frozen=True)
class Reporter:
    on_step: Callable[[Step], None] = _noop
    log: Callable[[str], None] = _noop


@dataclass(frozen=True)
class PipelineClients:
    geocoding: GeocodingClient
    routes: RoutesClient
    street_view: StreetViewClient
    make_vlm: Callable[[], VlmClient] | None = None  # None なら VLM を使わない（フォールバック文のみ）
    google_cache: FileCache | None = None
    vlm_cache: FileCache | None = None


@dataclass(frozen=True)
class PipelineResult:
    exploration: Exploration
    origin: Place
    destination: Place


def make_clients(settings: Settings, *, use_cache: bool = True, use_vlm: bool = True) -> PipelineClients:
    """設定（.env）から本物のクライアントを作る。Google のキーが無ければ RuntimeError。"""
    key = settings.require_google_maps_api_key()
    return PipelineClients(
        geocoding=GeocodingClient(key), routes=RoutesClient(key), street_view=StreetViewClient(key),
        make_vlm=(lambda: make_vlm_client(settings)) if use_vlm else None,
        google_cache=FileCache(settings.cache_dir, "google") if use_cache else None,
        vlm_cache=FileCache(settings.cache_dir, "vlm") if use_cache else None,
    )


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _fmt_place(p: Place) -> str:
    return f"{p.query} ({p.lat:.5f},{p.lng:.5f})"


# --- 地名だけから（経由地あり） ---

def explore_queries(c: PipelineClients, queries: list[str], out_dir: Path, rep: Reporter = Reporter()) -> PipelineResult:
    """[出発地, *経由地, 目的地] から geocode → route → turns。"""
    rep.on_step("geocode")
    geo = geocode_queries(c.geocoding, queries, c.google_cache)
    origin, dest, via = geo.places[0], geo.places[-1], geo.places[1:-1]
    _write_json(out_dir / "raw" / "geocode.json", geo.raw)
    rep.log(f"[2/7] geocode: {_fmt_place(origin)} → {_fmt_place(dest)}")

    rep.on_step("route")
    ro = compute_route(c.routes, origin, dest, via, c.google_cache)
    _write_json(out_dir / "raw" / "routes.json", ro.raw)
    rep.log(f"[3/7] route: {ro.route.distance_m} m, 約 {ro.route.duration_s // 60} 分, {len(ro.route.steps)} ステップ")

    turns = extract_turns(ro.route, origin, dest)
    rep.log(f"[4/7] turns: 採用 {len(turns.exploration.points)} / 候補 {len(turns.decisions)}")
    return PipelineResult(turns.exploration, origin, dest)


# --- 作成者の写真を通る経路 ---

def copy_photos(plan: PlanInput, src_dir: Path, out_dir: Path) -> None:
    """写真を正規化して ``out_dir/photos/`` に置き、``photos.json`` も書く。同じ場所なら何もしない。"""
    if src_dir.resolve() == out_dir.resolve():
        return
    (out_dir / "photos").mkdir(parents=True, exist_ok=True)
    for ph in plan.photos:
        (out_dir / ph.image).write_bytes(normalize_photo((src_dir / ph.image).read_bytes()))
    (out_dir / PHOTOS_JSON).write_text(plan.model_dump_json(indent=2), encoding="utf-8")


def _plan_photo_legs(c: PipelineClients, plan: PlanInput, origin: Place, legs_dest: Place | None, dest: Place,
                     out_dir: Path, rep: Reporter) -> Exploration:
    """legs_dest が None なら最後の写真で終わる。dest は表示用のゴール（写真地点の Place）。"""
    rep.on_step("route")
    legs = split_legs(origin, legs_dest, plan.photos)
    outputs, leg_warnings = plan_legs(c.routes, legs, c.google_cache)
    (out_dir / "legs").mkdir(exist_ok=True)
    for leg, out in zip(legs, outputs):
        if out:
            _write_json(out_dir / "legs" / f"{leg.index:02d}.json", out.raw)
    ok = [o for o in outputs if o]
    rep.log(f"[3/7] route: 区間 {len(ok)}/{len(legs)}, 計 {sum(o.route.distance_m for o in ok)} m")

    merged = merge_legs(legs, outputs, origin, dest)
    e = merged.exploration
    n_photo = sum(1 for p in e.points if p.image_source == "creator_photo")
    rep.log(f"[4/7] turns: 採用 {len(e.points)}（うち作成者写真 {n_photo}）")
    for w in [*leg_warnings, *merged.warnings]:
        rep.log(f"      ! {w.message}")
    return e


def explore_photos(c: PipelineClients, plan: PlanInput, out_dir: Path, rep: Reporter = Reporter(),
                   *, src_dir: Path | None = None) -> PipelineResult:
    """photos.json（PlanInput）から geocode（座標が無いときだけ）→ 区間ごとの route → 結合。"""
    rep.on_step("geocode")
    goal = plan.destination or goal_from_last_photo(plan.photos[-1])  # 省略時は最後の写真がゴール
    origin, dest = resolve_places([plan.origin, goal], c.geocoding, c.google_cache)
    note = "（目的地なし: 最後の写真がゴール）" if plan.ends_at_last_photo else ""
    rep.log(f"[2/7] geocode: {_fmt_place(origin)} → {_fmt_place(dest)}  写真 {len(plan.photos)} 枚{note}")
    if src_dir is not None:
        copy_photos(plan, src_dir, out_dir)
    legs_dest = None if plan.ends_at_last_photo else dest
    return PipelineResult(_plan_photo_legs(c, plan, origin, legs_dest, dest, out_dir, rep), origin, dest)


# --- 共通の後半（画像・目印・矢印） ---

def _vlm_client(c: PipelineClients, rep: Reporter) -> VlmClient | None:
    if c.make_vlm is None:
        return None
    try:
        return c.make_vlm()
    except VlmError as err:
        rep.log(f"[6/7] VLM なし（{err}）→ フォールバック文のみ")
        return None


def enrich(c: PipelineClients, e: Exploration, out_dir: Path, opt: StreetViewOptions,
           rep: Reporter = Reporter()) -> Exploration:
    """Street View の候補 → VLM の採点と目印文 → 矢印。"""
    rep.on_step("streetview")
    e, stats = fetch_candidates(c.street_view, e, out_dir, opt, cache=c.google_cache)
    n_cand = sum(len(p.candidates) for p in e.points)
    rep.log(f"[5/7] street view: 地点 {len(stats.fetched)} / なし {len(stats.missing)}, 候補 {n_cand} 枚")

    rep.on_step("landmark")
    vlm = _vlm_client(c, rep)
    e, lstats = evaluate_landmarks(vlm, e, out_dir, c.vlm_cache)
    if vlm:
        rep.log(f"[6/7] landmark ({vlm.model}): 評価 {len(lstats.evaluated)} / フォールバック {len(lstats.fallback)}")
        for i, msg in lstats.errors.items():
            rep.log(f"      ! 地点 {i}: {msg}")

    rep.on_step("arrow")
    e, a = draw_arrows(e, out_dir)
    rep.log(f"[7/7] arrow: 描画 {len(a.drawn)}（地図+画像 {len(a.with_fused_path)} / 地図の投影 {len(a.with_geo_path)} / VLM のみ {len(a.with_vlm_path)}）"
            f"/ 画像なし {len(a.skipped)} / 作成者写真 {len(a.creator)}")
    return e


def route_title(r: PipelineResult) -> str:
    e = r.exploration
    return f"{r.origin.query} → {r.destination.query}（{e.total_distance_m} m, {len(e.points)} 地点）"


def write_route_files(r: PipelineResult, out_dir: Path) -> None:
    """中間ファイル route.json・contact.html（候補画像の一覧）・map.html（経路線と地点の地図）を書く。"""
    (out_dir / "route.json").write_text(r.exploration.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "contact.html").write_text(render_contact_html(r.exploration, route_title(r)), encoding="utf-8")
    (out_dir / "map.html").write_text(render_route_map(r.exploration, route_title(r)), encoding="utf-8")


@dataclass(frozen=True)
class PhotoPipeline:
    """作る人 API 用: 入力ディレクトリ（photos.json と photos/ が置いてある）でそのまま全工程を回す。"""

    make_clients: Callable[[], PipelineClients]
    options: StreetViewOptions = field(default_factory=StreetViewOptions)

    def run(self, plan: PlanInput, work_dir: Path, rep: Reporter = Reporter()) -> PipelineResult:
        c = self.make_clients()
        (work_dir / "raw").mkdir(parents=True, exist_ok=True)
        r = explore_photos(c, plan, work_dir, rep)
        r = PipelineResult(enrich(c, r.exploration, work_dir, self.options, rep), r.origin, r.destination)
        write_route_files(r, work_dir)
        return r
