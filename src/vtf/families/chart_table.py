"""Frontier-hard compositional family: a bar chart and a table that must be read together.

The chart gives units sold per product code; the table, in a different order, maps each
code to a product name, a category and a unit price. Every question needs a join across
the two: find a bar, look its code up in the table, or the other way round, and sometimes
multiply. Ambiguity guards drop items where a chart reading error of the allowed size could
change the answer (for example, when two revenues are too close to rank).
"""

from __future__ import annotations

import io
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from ..core import FRUITS, Family, Question, Reject, pick, register  # noqa: E402
from .chart_table_checks import chart_table_probe  # noqa: E402
from .charts import FACES, PALETTES, THEMES, _press  # noqa: E402
from .text import font  # noqa: E402

PRODUCTS = FRUITS + ["Bread", "Milk", "Eggs", "Rice", "Coffee", "Butter", "Cheese", "Pasta", "Tea", "Honey",
                     "Yogurt", "Flour", "Olive oil", "Oats", "Jam", "Cocoa"]
CATEGORIES = ["Fresh", "Pantry", "Dairy", "Bakery"]


def ct_build(rng, diff):
    n = {"easy": int(rng.integers(4, 6)), "medium": int(rng.integers(5, 8)), "hard": int(rng.integers(7, 10))}[diff]
    letters = pick(rng, list("ABCDEFGHKMNPRST"), n)
    codes = [f"{l}{int(rng.integers(1, 10))}" for l in letters]
    names = pick(rng, PRODUCTS, n)
    cats = pick(rng, CATEGORIES, {"easy": 2, "medium": 3, "hard": 4}[diff])
    units = [int(v) for v in rng.integers(8, 96, size=n)]
    table = [[codes[i], names[i], pick(rng, cats), int(rng.integers(12, 400)) * 5] for i in range(n)]
    order = [int(i) for i in rng.permutation(n)]
    knobs = {
        "n_products": n,
        "value_labels": bool({"easy": True, "medium": rng.random() < 0.5, "hard": False}[diff]),
        "gridlines": diff != "hard",
        "theme": pick(rng, sorted(THEMES)),
        "palette": pick(rng, sorted(PALETTES)),
        "font_px": {"easy": 17, "medium": 15, "hard": 14}[diff],
        "currency": pick(rng, ["$", "£", "€"]),
    }
    spec = {"chart": {"codes": codes, "units": units, "title": "Units sold by product code"},
            "table": [table[i] for i in order], "title": pick(rng, ["Weekly sales report", "Store sales review",
                                                                     "Product sales and prices"]),
            "currency": knobs["currency"]}
    return spec, knobs


def _chart(spec, knobs):
    """Render the chart to an RGB array; returns it with bar geometry in its own pixels."""
    th = THEMES[knobs["theme"]]
    color = PALETTES[knobs["palette"]][0]
    fig, ax = plt.subplots(figsize=(5.4, 4.4), dpi=100)
    codes, units = spec["chart"]["codes"], spec["chart"]["units"]
    x = np.arange(len(codes))
    bars = ax.bar(x, units, color=color, width=0.62)
    ax.set_xticks(x, codes, fontsize=10)
    lim = math.ceil(max(units) * 1.15 / 10) * 10
    ax.set_ylim(0, lim)
    _press(fig, ax, knobs, spec["chart"]["title"], "Units, this week", None)
    if knobs["value_labels"]:
        ax.bar_label(bars, padding=2, fontsize=8.5, color=th["text"])
    fig.tight_layout()
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    r = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(r) for t in ax.get_xticklabels() if t.get_text()]
    overlap = any(boxes[i].overlaps(boxes[j]) for i in range(len(boxes)) for j in range(i + 1, len(boxes)))
    geo = []
    for i, v in enumerate(units):
        xc, yb = ax.transData.transform((i, 0))
        _, yt = ax.transData.transform((i, v))
        xr, _ = ax.transData.transform((i + 0.31, 0))
        geo.append({"c": float(xc), "base": float(h - yb), "tip": float(h - yt), "hw": float(xr - xc)})
    ppu = float(ax.transData.transform((0, 1))[1] - ax.transData.transform((0, 0))[1])
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, metadata={"Software": None}, facecolor=fig.get_facecolor())
    plt.close(fig)
    arr = np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))
    return arr, geo, ppu, lim, overlap, color


def _money(cents, cur):
    return f"{cur}{cents // 100}.{cents % 100:02d}"


def ct_render(spec, knobs, path):
    th = THEMES[knobs["theme"]]
    bg = tuple(int(th["bg"][i:i + 2], 16) for i in (1, 3, 5))
    chart, geo, ppu, lim, overlap, color = _chart(spec, knobs)
    fs = knobs["font_px"]
    f, fb = font(fs, face="sans"), font(fs, bold=True, face="sans")
    ft = font(26, bold=True, face="serif")
    head = ["Code", "Product", "Category", "Unit price"]
    rows = [[c, nm, cat, _money(cents, spec["currency"])] for c, nm, cat, cents in spec["table"]]
    cells = [head] + rows
    pad = 10
    widths = [int(max((fb if i == 0 else f).getbbox(r[j])[2] for i, r in enumerate(cells))) + 2 * pad
              for j in range(4)]
    rh = int(fs * 1.6) + 6
    top = 70
    cx0 = 20
    tx0 = cx0 + chart.shape[1] + 30
    W = tx0 + sum(widths) + 30
    H = max(top + chart.shape[0], top + 40 + rh * len(cells)) + 50
    page = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(page)
    d.text((cx0, 24), spec["title"], font=ft, fill=th["text"], anchor="lt")
    page.paste(Image.fromarray(chart), (cx0, top))
    d.text((tx0, top + 8), "Product list", font=font(16, bold=True, face="serif"), fill=th["text"], anchor="lt")
    y = top + 40
    boxes = []
    for i, row in enumerate(cells):
        if i == 0:
            d.rectangle([tx0, y, tx0 + sum(widths), y + rh], fill=th["grid"])
        x, rb = tx0, []
        for j, txt in enumerate(row):
            ftx = fb if i == 0 else f
            if j == 3:
                d.text((x + widths[j] - pad, y + rh / 2), txt, font=ftx, fill=th["text"], anchor="rm")
            else:
                d.text((x + pad, y + rh / 2), txt, font=ftx, fill=th["text"], anchor="lm")
            rb.append([x, y, x + widths[j], y + rh])
            x += widths[j]
        boxes.append(rb)
        d.line([tx0, y + rh, tx0 + sum(widths), y + rh], fill=th["grid"], width=1)
        y += rh
    d.text((cx0, H - 26), "Bars are labelled by product code; the product list gives each code's name, "
           "category and unit price.", font=font(12, face="sans"), fill=th["muted"], anchor="lt")
    page.save(path)
    bars = [{"c": g["c"] + cx0, "base": g["base"] + top, "tip": g["tip"] + top, "hw": g["hw"]} for g in geo]
    text_w = [[int((fb if i == 0 else f).getbbox(t)[2]) for t in row] for i, row in enumerate(cells)]
    return {"w": W, "h": H, "bars": bars, "px_per_unit": ppu, "axis_max": lim, "label_overlap": overlap,
            "value_labels": knobs["value_labels"], "bar_color": color, "cells": boxes, "text_w": text_w,
            "chart_codes": spec["chart"]["codes"], "table_rows": [r[:1] for r in spec["table"]]}


def ct_ask(spec, info, rng, diff):
    codes, units = spec["chart"]["codes"], spec["chart"]["units"]
    by_code = {r[0]: r for r in spec["table"]}
    names = [r[1] for r in spec["table"]]
    ppu = info["px_per_unit"]
    err = 0.0 if info["value_labels"] else 0.04 * info["axis_max"]  # allowed chart reading error, in units
    qts = {"easy": ["name_of_max", "name_of_min", "price_of_max"],
           "medium": ["name_of_max", "name_of_min", "price_of_max", "units_of_name", "revenue_argmax"],
           "hard": ["revenue_argmax", "revenue_argmax", "category_units", "units_of_name", "price_of_max"]}[diff]
    qt = pick(rng, qts)
    order = sorted(range(len(units)), key=lambda i: -units[i])
    join = "Use the chart and the product list together."
    if qt in ("name_of_max", "price_of_max"):
        if (units[order[0]] - units[order[1]]) * ppu < 4:
            raise Reject("top two bars within 4px")
        row = by_code[codes[order[0]]]
        if qt == "name_of_max":
            return Question(qt, {}, f"Which product sold the most units? {join}", row[1], "exact",
                            format_hint="the product name from the list", choices=names)
        return Question(qt, {}, f"What is the unit price of the product that sold the most units? {join}",
                        row[3] / 100, "numeric", tolerance=0.005,
                        format_hint="a number with two decimals, no currency sign")
    if qt == "name_of_min":
        if (units[order[-2]] - units[order[-1]]) * ppu < 4:
            raise Reject("bottom two bars within 4px")
        return Question(qt, {}, f"Which product sold the fewest units? {join}", by_code[codes[order[-1]]][1],
                        "exact", format_hint="the product name from the list", choices=names)
    if qt == "units_of_name":
        row = pick(rng, spec["table"])
        tol = 0.0 if info["value_labels"] else round(0.05 * info["axis_max"], 2)
        return Question(qt, {"name": row[1]}, f"How many units of {row[1]} were sold? {join}",
                        units[codes.index(row[0])], "numeric", tolerance=tol, format_hint="a number")
    if qt == "revenue_argmax":
        rev = [(units[codes.index(r[0])], r[3], r[1]) for r in spec["table"]]
        rev.sort(key=lambda t: -t[0] * t[1])
        (ub, pb, nb), rest = rev[0], rev[1:]
        # the leader must stay ahead even if every bar is misread by err in the worst direction
        if any((ub - err) * pb < 1.02 * (uo + err) * po for uo, po, _ in rest):
            raise Reject("revenue leader not robust to chart reading error")
        return Question(qt, {}, "Which product brought in the most revenue (units sold times unit price)? " + join,
                        nb, "exact", format_hint="the product name from the list", choices=names)
    cats = sorted({r[2] for r in spec["table"]})
    cat = pick(rng, cats)
    members = [r for r in spec["table"] if r[2] == cat]
    if not 2 <= len(members) <= 3:
        raise Reject("category needs 2 or 3 products")
    total = sum(units[codes.index(r[0])] for r in members)
    tol = 0.0 if info["value_labels"] else round(err * len(members), 2)
    return Question("category_units", {"category": cat},
                    f"How many units were sold in total across all {cat} products? {join}", total, "numeric",
                    tolerance=tol, format_hint="a number")


register(Family("chart_table", ct_build, ct_render, ct_ask, chart_table_probe))
