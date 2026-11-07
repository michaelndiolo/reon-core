"""The REON page runs top to bottom on each sample, on pasted text, and on bad input without crashing; key numbers match the modules."""
import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest

from pathlib import Path

from hackkit import reon_loss

APP = str(Path(__file__).resolve().parent.parent / "app_reon.py")


def _run(**state):
    at = AppTest.from_file(APP, default_timeout=60)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    return at


def test_default_runs_and_matches_modules():
    at = _run()
    assert not at.exception
    leaf = [20.27, 17.42, 19.57, 18.93, 25.04, 23.65, 22.87, 17.59]
    ideal = reon_loss.net_gain(leaf, 1.0)
    labels = [m.label for m in at.metric]
    assert "Gain, ideal control" in labels and "Gain after your limits" in labels
    tile = [m for m in at.metric if m.label == "Gain, ideal control"][0]
    assert tile.value == f"{100 * ideal:,.1f}%"
    assert len(at.tabs) == 6


@pytest.mark.parametrize("choice", ["36 BMW i3 cells (arXiv 2507.14020)", "BMW i3 module 3", "BMW i3 module 1 (has an outlier)"])
def test_samples_run(choice):
    at = _run(choice=choice)
    assert not at.exception


def test_paste_and_bad_input():
    at = _run(choice="Paste or upload my own", paste="100 90 80 70")
    assert not at.exception
    assert [m for m in at.metric if m.label == "Gain, ideal control"][0].value == "21.4%"
    bad = _run(choice="Paste or upload my own", paste="abc")
    assert not bad.exception and any("Could not read" in e.value for e in bad.sidebar.error)
    one = _run(choice="Paste or upload my own", paste="100")
    assert not one.exception and any("at least two" in e.value for e in one.sidebar.error)


def test_limits_can_remove_the_gain():
    at = _run(choice="BMW i3 module 3", loss=5.0)
    assert not at.exception
    assert any("no more than the conventional" in e.value for e in at.error)


def test_sorting_and_flip_blocks_render():
    at = _run(choice="36 BMW i3 cells (arXiv 2507.14020)")
    assert not at.exception
    text = " ".join(m.value for t in at.tabs for m in t.markdown) + " ".join(c.value for t in at.tabs for c in t.caption)
    assert "Against the usual alternative" in text and "What would flip the verdict" in text


def test_beats_current_methods_tab_renders_and_responds():
    at = _run(choice="36 BMW i3 cells (arXiv 2507.14020)")
    assert not at.exception
    text = " ".join(m.value for t in at.tabs for m in t.markdown) + " ".join(c.value for t in at.tabs for c in t.caption) + " ".join(i.value for i in at.info) + " ".join(h.value for h in at.subheader)
    assert "where to put the switches" in text and "drift apart" in text
    flat = _run(choice="36 BMW i3 cells (arXiv 2507.14020)", fade_cv=0.0)
    assert not flat.exception and any("does not last longer" in i.value for i in flat.info)


def test_best_design_section_and_conditions():
    at = _run(choice="36 BMW i3 cells (arXiv 2507.14020)", m_str=12, eol=0.7)
    assert not at.exception
    heads = " ".join(h.value for h in at.subheader)
    assert "The answer" in heads
    text = " ".join(i.value for i in at.info) + " ".join(s.value for s in at.success) + " ".join(w.value for w in at.warning)
    assert "stays in service" in text and "Robust choice" in text
    one = _run(choice="36 BMW i3 cells (arXiv 2507.14020)", m_str=36, eol=0.5)
    assert not one.exception
    paste = _run(choice="Paste or upload my own", paste="100 90 80 70")
    assert not paste.exception


def test_balancer_comparison_in_the_app():
    at = _run(choice="36 BMW i3 cells (arXiv 2507.14020)", m_str=12, eol=0.7, bal_r=20, bal_cost=0.0)
    assert not at.exception
    text = " ".join(i.value for i in at.info) + " ".join(w.value for w in at.warning)
    assert "late-engaging switches" in text and "Best:" in text
    off = _run(choice="36 BMW i3 cells (arXiv 2507.14020)", use_bal=False)
    assert not off.exception


def test_hybrid_and_closed_loss_controls():
    at = _run(choice="8 Nissan Leaf cells (arXiv 2402.18859)", m_str=4, eol=0.7, closed_loss=1.0, hyb_shared=True)
    assert not at.exception
    assert any("Controller decision today" in c.value for t in at.tabs for c in t.caption)


def test_failures_and_repair_inputs():
    at = _run(choice="36 BMW i3 cells (arXiv 2507.14020)", m_str=12, eol=0.7, fail_pct=1.0, repair_days=0)
    assert not at.exception
    fast = _run(choice="36 BMW i3 cells (arXiv 2507.14020)", m_str=12, eol=0.7, fail_pct=1.0, repair_days=30)
    assert not fast.exception


def test_learn_section_updates_with_observations():
    base = _run(choice="36 BMW i3 cells (arXiv 2507.14020)", m_str=12)
    assert not base.exception
    seen = _run(choice="36 BMW i3 cells (arXiv 2507.14020)", m_str=12, learn_f=40, learn_cy=2000.0, learn_fades="3, 4, 5, 4.5, 3.5, 4.2")
    assert not seen.exception
    vals = {m.label: m.value for m in seen.metric}
    assert vals["Believed failure rate / cell-year"] == "1.93%"
    bad = _run(choice="36 BMW i3 cells (arXiv 2507.14020)", m_str=12, learn_fades="a, b")
    assert not bad.exception and any("Could not read" in w.value for w in bad.warning)


def test_brief_sixteen_cell_example():
    """The REON brief: 15 cells at 85 Ah and one at 70 Ah. String = 70 Ah, average cell 84.06%, ratio string/average 83.3%, ideal gain = mean/min - 1."""
    caps = [85.0] * 15 + [70.0]
    mean, mn = sum(caps) / 16, min(caps)
    assert abs(mean - 84.0625) < 1e-9 and mn == 70.0
    assert abs(mn / mean - 0.8327) < 1e-3
    assert abs(reon_loss.net_gain(caps, 1.0) - (mean / mn - 1)) < 1e-9
    at = _run(choice="REON brief: 16 cells (15 at 85 Ah, one at 70 Ah)")
    assert not at.exception
    tile = [m for m in at.metric if m.label == "Gain, ideal control"][0]
    assert tile.value == f"{100 * (mean / mn - 1):,.1f}%"


def test_application_presets_set_inputs_and_run():
    at = _run(choice="36 BMW i3 cells (arXiv 2507.14020)", m_str=12)
    at.selectbox(key="preset").select("Grid-scale storage").run()
    assert not at.exception
    assert at.session_state["value"] == 12.0 and at.session_state["life"] == 15.0 and at.session_state["eol"] == 0.7
    assert at.session_state["value_tag"] == "ASSUMED" and at.session_state["life_tag"] == "CITED"
    at.selectbox(key="preset").select("Data-center backup").run()
    assert not at.exception
    assert at.session_state["eol"] == 0.8 and at.session_state["fail_pct"] == 0.0 and at.session_state["life"] == 12.0
    at.selectbox(key="preset").select("Retired EV packs reused as stationary storage").run()
    assert not at.exception and at.session_state["fade_m"] == 1.0


def test_recommended_build_block_renders_and_picks_selective_for_the_brief_pack():
    at = _run(choice="REON brief: 16 cells (15 at 85 Ah, one at 70 Ah)", dod_g=0.8)
    assert not at.exception
    texts = [s.value for s in at.success] + [w.value for w in at.warning]
    rb = [t for t in texts if "Recommended build" in t]
    assert len(rb) >= 2          # once next to the tiles, once in tab 5
    assert any("selective" in t or "late switches" in t or "hybrid" in t for t in rb)
