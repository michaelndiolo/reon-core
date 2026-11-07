"""check_cells: a weak cell is not a bad sensor. Each test builds ONE known defect and checks the right finding (and no other) appears."""
import numpy as np
import pytest

from hackkit import contract as K


def volts(T=48, n=4, seed=0):
    rng = np.random.default_rng(seed)
    common = 3.7 + 0.1 * np.sin(np.arange(T) / 5.0)
    return common[:, None] + rng.normal(0, 0.002, size=(T, n))


def by_code(f):
    out = {}
    for x in f:
        out.setdefault(x.code, []).append(x.series)
    return out


def test_clean_pack_is_quiet():
    V = volts()
    assert K.check_cells([100, 98, 102, 99], V, V.sum(axis=1)) == []


def test_weak_cell_by_hand():
    # median of 100/90/80/70 is 85; 15% below is 72.25: only the 70 Ah cell is weak (the 80 Ah cell is 5.9% below)
    f = K.check_cells([100, 90, 80, 70])
    assert by_code(f) == {"weak_cell": ["cell 3"]}
    assert f[0].severity == "info" and "18% below the median (85.0 Ah)" in f[0].message
    assert by_code(K.check_cells([100, 90, 80, 70], weak_frac=0.05)) == {"weak_cell": ["cell 2", "cell 3"]}


def test_stuck_sensor_on_a_weak_looking_cell_is_not_called_weak():
    V = volts()
    V[10:35, 3] = V[10, 3]                                   # cell 3's voltage freezes for 25 steps
    f = K.check_cells([100, 90, 80, 70], V)
    c = by_code(f)
    assert c["sensor_stuck"] == ["cell 3"]
    assert c["weak_or_sensor"] == ["cell 3"] and "weak_cell" not in c
    assert all(x.severity == "warn" for x in f)


def test_stuck_everything_is_not_a_cell_fault():
    V = volts()
    V[10:35, :] = V[10, :]                                   # all cells frozen at once (logger stopped), not one bad sensor
    assert "sensor_stuck" not in by_code(K.check_cells([100, 98, 102, 99], V))


def test_out_of_range_and_missing_readings():
    V = volts()
    V[5, 1] = 0.0
    V[7, 2] = np.nan
    c = by_code(K.check_cells([100, 98, 102, 99], V))
    assert c["sensor_range"] == ["cell 1"] and c["sensor_missing"] == ["cell 2"]


def test_sum_of_cells_vs_pack_finds_the_offset_sensor():
    V = volts()
    pack = V.sum(axis=1)
    V2 = V.copy()
    V2[:, 1] -= 0.8                                          # cell 1's sensor reads 0.8 V low all the time (5% of the pack voltage)
    c = by_code(K.check_cells([100, 98, 102, 99], V2, pack))
    assert c["pack_voltage_mismatch"] == ["pack voltage"]
    assert c["sensor_suspect_by_sum"] == ["cell 1"]


def test_inputs_are_checked():
    with pytest.raises(ValueError):
        K.check_cells([100])
    with pytest.raises(ValueError):
        K.check_cells([100, 90], volts(n=3))
    with pytest.raises(ValueError):
        K.check_cells([100, 90], volts(n=2), np.zeros(5))
    f = K.check_cells([100, 0, 90])
    assert by_code(f)["bad_capacity"] == ["cell 1"] and K.has_stop(f)
