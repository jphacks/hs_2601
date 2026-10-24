from app.services.creator.mapview import MapSpec, Marker, render_map_html


def test_ピンと経路とJSONが埋め込まれる() -> None:
    spec = MapSpec(
        title="t",
        markers=[Marker(lat=34.7, lng=135.5, label="1", popup_html="<b>大阪駅</b>")],
        path=[(34.7, 135.5), (34.71, 135.51)],
        data={"k": "値"},
    )
    out = render_map_html(spec)
    assert "leaflet" in out
    assert '"label": "1"' in out
    assert "[34.7, 135.5]" in out
    assert "&quot;k&quot;: &quot;値&quot;" in out  # JSON は HTML エスケープされる
