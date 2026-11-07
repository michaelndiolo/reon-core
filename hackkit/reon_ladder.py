"""Granularity ladder (Tim Ren: module-level second life is possible, but cells inside a module age differently by position).
Cells in physical modules of `module` cells share a location, so part of the fade spread is between modules and part is within. Switching g cells at a time (g = 1 cell level, g = module, g = n no switching = plain string).
Gain = usable of the switched design / usable of a plain string - 1, median over trials. Lognormal fade spread, independent draws; our own simulation, not REON data."""
import numpy as np
from hackkit.reon_guard import need


def ladder(n=240, module=24, between_share=0.5, mean_loss=0.10, cv=0.45, groups=(1, 6, 12, 24, 48, 240), trials=600, seed=2):
    need(n % module == 0 and all(n % g == 0 for g in groups) and 0.0 <= between_share <= 1.0 and 0 < mean_loss < 0.9 and cv >= 0, "ladder: groups and module must divide n; 0 <= between share <= 1; 0 < loss < 0.9")
    rng = np.random.default_rng(seed)
    sig = np.sqrt(np.log(1 + cv ** 2)); sb = sig * np.sqrt(between_share); sw = sig * np.sqrt(1 - between_share)
    mod = np.repeat(rng.normal(0, sb, (trials, n // module)), module, axis=1)
    cell = rng.normal(0, sw, (trials, n))
    c = 1 - mean_loss * np.exp(mod + cell - (sb ** 2 + sw ** 2) / 2)
    plain = n * c.min(1)
    return {g: float(np.median((g * c.reshape(trials, n // g, g).min(2)).sum(1) / plain - 1)) for g in groups}
