"""Render probe for the chart_table family.

Kept apart from the renderer: it only reads the render geometry and the saved pixels, so a
renderer bug cannot also hide itself in the check.
"""

from __future__ import annotations

import numpy as np


def _rgb(hex_color: str) -> np.ndarray:
    c = hex_color.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)])


def _run(img, x, base, tip, rgb):
    """Bar-coloured run from just above the base toward the tip along column x (gaps up to 3px)."""
    col = img[:, int(round(x)), :3].astype(int)
    mask = np.sqrt(((col - rgb) ** 2).sum(-1)) < 12
    p = int(round(base)) - 2
    if not mask[p]:
        return None
    last, gap = p, 0
    while p - 1 >= 0:
        p -= 1
        if mask[p]:
            last, gap = p, 0
        else:
            gap += 1
            if gap > 3:
                break
    return base - last


def chart_table_probe(spec, info, img):
    fails = []
    if info.get("label_overlap"):
        fails.append("tick labels overlap")
    for i, g in enumerate(info["bars"]):
        rgb = _rgb(info["bar_color"])
        want = g["base"] - g["tip"]
        got = [_run(img, g["c"] + off, g["base"], g["tip"], rgb) for off in (-0.5 * g["hw"], 0.0, 0.5 * g["hw"])]
        if sum(1 for r in got if r is not None and abs(r - want) <= 3) < 2:
            fails.append(f"bar {i} length {got}px, expected {want:.1f}px")
    gray = img.astype(int).sum(-1) / 3
    for i, row in enumerate(info["cells"]):
        for j, (x0, y0, x1, y1) in enumerate(row):
            if info["text_w"][i][j] > (x1 - x0) - 4:
                fails.append(f"cell {i},{j} text wider than cell")
            if (gray[y0 + 2:y1 - 2, x0 + 1:x1 - 1] < 110).sum() < 6:
                fails.append(f"cell {i},{j} has no ink")
    # every code drawn under a bar must also be a code in the table
    if sorted(info["chart_codes"]) != sorted(r[0] for r in info["table_rows"]):
        fails.append("chart and table codes differ")
    return fails
