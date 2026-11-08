import pytest
from streamlit.testing.v1 import AppTest

@pytest.fixture(autouse=True)
def _restore_widgets():
    """app_final replaces st.slider / st.select_slider with chip versions at import time. AppTest runs it in this process, so put the originals back afterwards (otherwise later tests of other apps see the chips)."""
    import streamlit as st
    from streamlit.delta_generator import DeltaGenerator as DG
    saved = (st.slider, st.select_slider, DG.slider, DG.select_slider)
    yield
    st.slider, st.select_slider, DG.slider, DG.select_slider = saved


PAGES = ["1 · Ask us", "2 · See it in 3D", "3 · Your state and site", "4 · The evidence"]


def _run(page, ev=None):
    at = AppTest.from_file("../app_final.py", default_timeout=240)
    at.session_state["nav"] = PAGES[page]
    if ev is not None:
        at.session_state["ev"] = ev
    return at.run()


@pytest.mark.parametrize("page", [0, 1, 2])
def test_pages_run_without_error(page):
    at = _run(page)
    assert not at.exception, [str(e) for e in at.exception]


@pytest.mark.parametrize("ev", list(range(1, 14)))
def test_evidence_topics_run_without_error(ev):
    at = _run(3, ev)
    assert not at.exception, [str(e) for e in at.exception]


def test_try_your_own_numbers_survey_runs_to_the_answer():
    at = AppTest.from_file("../app_final.py", default_timeout=300)
    at.session_state["nav"] = PAGES[3]
    at.session_state["ev"] = 1
    at.session_state["wz_step"] = 7
    at.session_state["wz_ans"] = {"fade25": 0.012, "n1": 200}
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    assert any("rn-verdict" in h.value for h in at.get("html"))
