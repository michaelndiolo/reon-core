from streamlit.testing.v1 import AppTest


def test_app_final_runs_without_error():
    at = AppTest.from_file("../app_final.py", default_timeout=180).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert len(at.tabs) == 13  # 2 top-level (customer view, engineering) + 11 engineering tabs
