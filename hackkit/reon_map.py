"""State tile map for the front page: one square per state (an NPR-style tile grid, so small states are as clickable as Texas) over the EIA-861 reliability table.
Three layers, all utility-wide state averages, not a store's own outage record:
  * Exposure      : minutes without power per customer in 2025, major events included (SAIDI).
  * Coverage      : hours of backup with cell-level control divided by the typical outage length in that state (CAIDI major 2025 / 60). Above 1 the battery rides through the typical outage.
  * Where to pilot: hours without power per year x critical load (kW) x value of lost load ($ per kWh). The one sourced anchor for the value of lost load is the Texas figure (about 35.7 $/kWh); it is a slider, not a fact about every store.
Pure data code (no plotting) so it can be tested; the chart is hackkit.reon_visuals.tile_map_chart."""
from __future__ import annotations

import pandas as pd

ABBR = {"Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
        "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME",
        "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
        "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
        "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
        "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"}
NAME = {v: k for k, v in ABBR.items()}

# (row, column) of each tile
TILES = {"AK": (0, 0), "ME": (0, 11),
         "VT": (1, 10), "NH": (1, 11),
         "WA": (2, 1), "ID": (2, 2), "MT": (2, 3), "ND": (2, 4), "MN": (2, 5), "IL": (2, 6), "WI": (2, 7), "MI": (2, 8), "NY": (2, 9), "RI": (2, 10), "MA": (2, 11),
         "OR": (3, 1), "NV": (3, 2), "WY": (3, 3), "SD": (3, 4), "IA": (3, 5), "IN": (3, 6), "OH": (3, 7), "PA": (3, 8), "NJ": (3, 9), "CT": (3, 10),
         "CA": (4, 1), "UT": (4, 2), "CO": (4, 3), "NE": (4, 4), "MO": (4, 5), "KY": (4, 6), "WV": (4, 7), "VA": (4, 8), "MD": (4, 9), "DE": (4, 10),
         "AZ": (5, 2), "NM": (5, 3), "KS": (5, 4), "AR": (5, 5), "TN": (5, 6), "NC": (5, 7), "SC": (5, 8), "DC": (5, 9),
         "OK": (6, 4), "LA": (6, 5), "MS": (6, 6), "AL": (6, 7), "GA": (6, 8),
         "HI": (7, 0), "TX": (7, 4), "FL": (7, 9)}

LAYERS = ("Exposure", "Coverage", "Where to pilot")
VOLL_TEXAS = 35.7   # $ per kWh, Texas PUC / Brattle 2024 (Utility Dive); an anchor, not a national value


def tile_frame(df: pd.DataFrame, layer: str, backup_hours: float = 8.4, load_kw: float = 5.0, voll: float = VOLL_TEXAS) -> pd.DataFrame:
    """One row per state in the tile grid. `df` is the EIA table indexed by full state name. Columns: state (full name), abbr, row, col, value, text (tooltip line), unit."""
    if layer not in LAYERS:
        raise ValueError(f"map: layer must be one of {LAYERS}")
    if backup_hours <= 0 or load_kw <= 0 or voll < 0:
        raise ValueError("map: backup hours and load must be positive, value of lost load not negative")
    rows = []
    for name, ab in ABBR.items():
        if name not in df.index:
            continue
        saidi = float(df.loc[name, "saidi_major_2025"])
        caidi_h = float(df.loc[name, "caidi_major_2025"]) / 60.0
        if layer == "Exposure":
            v, unit, text = saidi, "minutes without power per customer, 2025", f"{saidi:.0f} min"
        elif layer == "Coverage":
            v, unit, text = backup_hours / caidi_h, "backup hours / typical outage hours", f"{backup_hours / caidi_h:.1f}x a typical {caidi_h:.1f} h outage"
        else:
            v = saidi / 60.0 * load_kw * voll
            unit, text = "$ of load at risk per store per year", f"${v:,.0f} per year ({saidi / 60:.1f} h at {load_kw:g} kW)"
        r, c = TILES[ab]
        rows.append(dict(state=name, abbr=ab, row=r, col=c, value=float(v), text=text, unit=unit))
    return pd.DataFrame(rows)


def clicked_state(selection) -> str | None:
    """Full state name from a Streamlit chart selection (the 'pick' parameter with the field 'state'), or None."""
    try:
        pts = selection.get("pick", [])
    except AttributeError:
        return None
    for d in pts:
        s = d.get("state")
        if s in ABBR:
            return s
    return None
