"""Streamlit side of the 3D twin: mounts the three.js scene as a v2 component. The scene file and a vendored three.js (r160, MIT licence) live in hackkit/twin_assets, so the tab works offline."""
from __future__ import annotations

import os

import streamlit as st

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "twin_assets")


@st.cache_resource(show_spinner=False)
def _component():
    def read(name):
        with open(os.path.join(_DIR, name), encoding="utf-8") as f:
            return f.read()
    css = "#reon-twin{width:100%;border-radius:18px;overflow:hidden;background:#07121f}"
    return st.components.v2.component("reon_twin", html='<div id="reon-twin"></div>', css=css, js=read("three.min.js") + "\n;\n" + read("twin_scene.js"), isolate_styles=False)


def mount(data: dict, key: str = "twin3d", on_pick=None):
    """Draw the scene. A click on a cell sends a `pick` trigger {cell, t}; on_pick runs before the rerun, so it can update session state first."""
    return _component()(data=data, key=key, on_pick_change=on_pick or (lambda: None))


def last_pick(key: str = "twin3d"):
    """The cell index clicked in the run that is starting, or None."""
    v = st.session_state.get(key)
    pick = getattr(v, "pick", None)
    if pick is None and isinstance(v, dict):
        pick = v.get("pick")
    if isinstance(pick, dict) and "cell" in pick:
        return int(pick["cell"])
    return None
