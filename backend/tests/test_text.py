from app.services.creator.text import normalize_instruction


def test_方角を直進に() -> None:
    assert normalize_instruction("東に進む", "straight") == "直進する"
    assert normalize_instruction("北西に進んで奈良街道に向かう", "straight") == "直進して奈良街道に向かう"
    assert normalize_instruction("南東方向に進み 北梅田通 に向かう", "straight") == "直進し 北梅田通 に向かう"


def test_方角を左右に() -> None:
    assert normalize_instruction("東に進んでえびす橋に向かう", "left") == "左に進んでえびす橋に向かう"
    assert normalize_instruction("北へ進む", "right") == "右に進む"


def test_方角が無ければそのまま() -> None:
    assert normalize_instruction("左折して谷町筋に入る", "left") == "左折して谷町筋に入る"
    assert normalize_instruction("", "straight") == ""
    assert normalize_instruction("東京駅に向かう", "straight") == "東京駅に向かう"  # 地名の「東」は触らない
