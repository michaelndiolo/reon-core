import numpy as np

from hackkit import reon_grid as GR
from hackkit import reon_twin as TW


def _h():
    return GR.make_string(np.linspace(0.8, 1.2, 60))


def test_toggle_fails_then_repairs_and_ignores_bad_index():
    assert TW.toggle([], 5) == [5]
    assert TW.toggle([5], 5) == []
    assert TW.toggle([9, 5], 2) == [2, 5, 9]
    assert TW.toggle([1], 999) == [1]
    assert TW.toggle([1], -1) == [1]


def test_payload_no_failure_plain_line_is_weakest_cell_and_control_line_is_higher():
    h = _h()
    an = GR.analyse(h, [], 0.9, 60.0, 0.04, 5.0)
    p = TW.payload(h, an, 5.0)
    assert abs(p["line_plain"] - h.min()) < 1e-9
    assert p["line_ours"] > p["line_plain"]
    assert p["failed"] == [] and not p["refused"] and len(p["health"]) == 250
    assert p["plain_kwh"] > 0 and p["ours_kwh"] > 0  # with matched cells the 4% switch loss can leave control slightly behind a plain string


def test_payload_with_open_cell_plain_is_dark_control_keeps_going():
    h = _h()
    an = GR.analyse(h, [137], 0.9, 60.0, 0.04, 5.0)
    p = TW.payload(h, an, 5.0)
    assert p["plain_kwh"] == 0.0 and p["line_plain"] == 0.0
    assert p["ours_kwh"] > 0 and p["failed"] == [137]
    assert all(i != 137 for i in p["early"])


def test_payload_refused_when_too_many_fail():
    h = _h()
    failed = list(range(26))  # K = 25 at window 0.9
    an = GR.analyse(h, failed, 0.9, 60.0, 0.04, 5.0)
    p = TW.payload(h, an, 5.0)
    assert p["refused"] and p["ours_kwh"] == 0.0 and p["line_ours"] == 0.0
