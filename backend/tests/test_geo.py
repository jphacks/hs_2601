from app.services.creator.geo import bearing_deg, bearing_into, bearing_out_of, haversine_m, heading_diff_deg

OSAKA = (34.7024854, 135.4959506)


def test_方位_北東南西() -> None:
    assert round(bearing_deg(OSAKA, (OSAKA[0] + 0.001, OSAKA[1]))) == 0     # 北
    assert round(bearing_deg(OSAKA, (OSAKA[0], OSAKA[1] + 0.001))) == 90    # 東
    assert round(bearing_deg(OSAKA, (OSAKA[0] - 0.001, OSAKA[1]))) == 180   # 南
    assert round(bearing_deg(OSAKA, (OSAKA[0], OSAKA[1] - 0.001))) == 270   # 西


def test_方位差は右回り正で範囲内() -> None:
    assert heading_diff_deg(10, 100) == 90
    assert heading_diff_deg(350, 10) == 20
    assert heading_diff_deg(10, 350) == -20
    assert heading_diff_deg(0, 180) == 180


def test_距離() -> None:
    assert 100 < haversine_m(OSAKA, (OSAKA[0] + 0.001, OSAKA[1])) < 112


def test_入る方位と出る方位() -> None:
    # 北へ 50m → 東へ 50m の L 字
    path = [(34.7000, 135.5000), (34.70045, 135.5000), (34.70045, 135.50055)]
    assert round(bearing_into(path, 1)) == 0
    assert round(bearing_out_of(path, 1)) == 90
    assert bearing_into(path, 0) is None
    assert bearing_out_of(path, 2) is None
