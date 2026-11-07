import csv
import numpy as np
from hackkit.reon_response import Cell, Context, Limits, decide, NORMAL, SWITCH_OUT, BYPASS, REDUCE_POWER, KILL


def cells(n=16, **kw):
    return [Cell(i, **kw) for i in range(n)]


def kinds(a):
    return [x.kind for x in a]


def test_all_normal():
    assert kinds(decide(cells(), Context())) == [NORMAL]


def test_cell_at_own_soc_limit_is_switched_out_not_bypassed():
    cs = cells(); cs[3].soc = 0.03
    a = decide(cs, Context())
    assert kinds(a) == [SWITCH_OUT] and a[0].cells == [3]


def test_hot_cell_rests():
    cs = cells(); cs[5].t = 50.0
    a = decide(cs, Context())
    assert SWITCH_OUT in kinds(a) and KILL not in kinds(a)


def test_persistently_weak_cell_is_bypassed_but_a_new_weak_cell_is_not():
    cs = cells(); cs[2].cap_rel = 0.8; cs[2].bad_cycles = 1
    assert kinds(decide(cs, Context())) == [NORMAL]
    cs[2].bad_cycles = 3
    a = decide(cs, Context())
    assert a[0].kind == BYPASS and a[0].cells == [2]


def test_one_fault_sign_bypass_two_kill():
    cs = cells(); cs[1].r_rel = 3.0
    assert decide(cs, Context())[0].kind == BYPASS
    cs[4].dT_dt = 2.0
    assert decide(cs, Context())[0].kind == KILL


def test_hard_limit_kills():
    cs = cells(); cs[0].t = 65.0
    assert decide(cs, Context())[0].kind == KILL


def test_cold_reduces_power():
    cs = cells(t=-5.0)
    a = decide(cs, Context())
    assert a[0].kind == REDUCE_POWER and a[0].power_limit < 1.0


def test_outage_stretches_runtime_instead_of_killing():
    a = decide(cells(), Context(islanded=True, runtime_needed_h=72, runtime_available_h=36))
    assert a[0].kind == REDUCE_POWER and abs(a[0].power_limit - 0.5) < 1e-9


def test_budget_used_up_calls_crew():
    cs = cells(); cs[0].cap_rel = 0.7; cs[0].bad_cycles = 9
    assert decide(cs, Context(bypass_left=0))[0].kind == KILL


def test_string_finished_kills():
    assert decide(cells(), Context(capacity_frac=0.65))[0].kind == KILL


def test_no_false_bypass_on_real_cells():
    """1,140 real cells (12 cars, 280,000 km, Nature Energy 2026 Fig 4): none is persistently 'weak' at the 15 % line, so the policy bypasses nothing on normal ageing spread."""
    rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
    car = {}
    for p, _, _, late in rows:
        car.setdefault(p, []).append(float(late))
    n = 0
    for v in car.values():
        v = np.array(v)
        cs = [Cell(i, cap_rel=float(v[i] / np.median(np.delete(v, i))), bad_cycles=99) for i in range(len(v))]
        n += len(cs)
        assert BYPASS not in kinds(decide(cs, Context(n_engaged=len(v), n_min=len(v) - 10, bypass_left=10))), "false bypass on a normal real cell"
    assert n == 1140
