import pandas as pd
import pytest
from hackkit import reon_map as M


def eia():
    return pd.read_csv("examples/data/eia_reliability_by_state.csv", comment="#").set_index("state")


def test_every_state_has_one_unique_tile_and_every_eia_row_maps():
    assert len(M.TILES) == 51 and len(set(M.TILES.values())) == 51
    assert set(M.ABBR.values()) == set(M.TILES)
    states = set(eia().index) - {"U.S. Total"}
    assert states == set(M.ABBR), states ^ set(M.ABBR)


def test_layers_return_one_row_per_state_with_sane_values():
    df = eia()
    for layer in M.LAYERS:
        f = M.tile_frame(df, layer)
        assert len(f) == 51 and f.value.gt(0).all() and f.text.str.len().gt(0).all()
    cov = M.tile_frame(df, "Coverage", backup_hours=8.4)
    assert abs(cov.set_index("abbr").loc["TX", "value"] - 8.4 / (df.loc["Texas", "caidi_major_2025"] / 60)) < 1e-9


def test_pilot_layer_scales_with_load_and_value_and_rejects_bad_input():
    df = eia()
    a = M.tile_frame(df, "Where to pilot", load_kw=5, voll=10).set_index("abbr").value
    b = M.tile_frame(df, "Where to pilot", load_kw=10, voll=20).set_index("abbr").value
    assert ((b / a) - 4).abs().max() < 1e-9
    with pytest.raises(ValueError):
        M.tile_frame(df, "nope")
    with pytest.raises(ValueError):
        M.tile_frame(df, "Exposure", load_kw=0)


def test_clicked_state():
    assert M.clicked_state({"pick": [{"state": "Ohio"}]}) == "Ohio"
    assert M.clicked_state({"pick": []}) is None
    assert M.clicked_state(None) is None
