import pytest
from streamlit.testing.v1 import AppTest

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
