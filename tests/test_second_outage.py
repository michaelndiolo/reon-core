import numpy as np
from hackkit import reon_storm as S


def test_slow_recharge_caps_both_and_full_recharge_matches_first_outage():
    caps = np.array([1.0, 0.97, 0.9, 0.95] * 10)
    kw = dict(nameplate_kwh=60.0, load_kw=5.0)
    full_plain = S.second_outage_hours(caps, recharge_kw=10, recharge_h=24, managed=False, **kw)
    full_ours = S.second_outage_hours(caps, recharge_kw=10, recharge_h=24, managed=True, window=0.9, **kw)
    assert abs(full_plain - S.hours(caps, 60.0, 5.0, False)) < 1e-9
    assert abs(full_ours - S.hours(caps, 60.0, 5.0, True, window=0.9)) < 1e-9
    slow_plain = S.second_outage_hours(caps, recharge_kw=10, recharge_h=1, managed=False, **kw)
    slow_ours = S.second_outage_hours(caps, recharge_kw=10, recharge_h=1, managed=True, window=0.9, **kw)
    assert slow_plain == 2.0 and slow_ours < slow_plain + 1e-9   # one hour of charger = 10 kWh = 2 h at 5 kW; the switch loss costs the managed string a little


def test_failed_cell_kills_plain_but_not_managed():
    caps = np.array([1.0, 0.97, 0.9, 0.95] * 10)
    assert S.second_outage_hours(caps, 60.0, 5.0, 10, 24, False, failed=1) == 0.0
    assert S.second_outage_hours(caps, 60.0, 5.0, 10, 24, True, window=0.9, failed=1) > 5.0
