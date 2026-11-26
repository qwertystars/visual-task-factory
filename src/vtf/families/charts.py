"""Bar, line and pie charts rendered with matplotlib in a financial-press house style.

Serif headline and grey standfirst at top left, a source line at the bottom, tinted
backgrounds, horizontal rules only, vendored PT fonts. The hard tier adds a second axis
(bar), shaded event bands and callouts (line), and donuts (pie).

Each render returns the pixel geometry of every mark, read from matplotlib's own
transforms, so probes can check the saved PNG against the spec.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ..core import FRUITS, WORDS, Family, Question, Reject, pick, register  # noqa: E402
from .text import register_mpl_fonts  # noqa: E402

FACES = register_mpl_fonts()
plt.rcParams.update({"font.family": FACES["sans"], "svg.hashsalt": "vtf", "axes.unicode_minus": False})

DISTINCT = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#ff9896",
            "#bcbd22", "#17becf", "#393b79", "#637939"]
PALETTES = {
    "harbour": ["#1f4e79", "#c8553d", "#2e8b57", "#e0a526", "#6d3b8e", "#3fa7c9", "#8c6d46", "#b23a6e",
                "#5c7f2e", "#7a8691", "#d97c2b", "#2b2d42"],
    "ledger": ["#0b3c5d", "#d1495b", "#00798c", "#edae49", "#66a182", "#8d5a97", "#30638e", "#c97b63",
               "#2e4057", "#9c9a3a", "#e06c9f", "#5b5b5b"],
    "slate": ["#264653", "#e76f51", "#2a9d8f", "#e9c46a", "#7b5ea7", "#4d908e", "#f4a261", "#9e2a2b",
              "#577590", "#90be6d", "#bc6c25", "#3d405b"],
}
THEMES = {
    "cream": {"bg": "#f5efe4", "grid": "#d8cfc0", "text": "#2d2a26", "muted": "#6f675d"},
    "white": {"bg": "#ffffff", "grid": "#e2e2e2", "text": "#1e1e1e", "muted": "#6a6a6a"},
    "mist": {"bg": "#eef2f5", "grid": "#cdd6de", "text": "#1d2731", "muted": "#5e6b77"},
}
SOURCES = ["Source: company filings", "Source: survey of members", "Source: national statistics office",
           "Source: industry association", "Source: internal records"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _shades(rng, n: int, base_hex: str | None = None) -> list[str]:
    """n similar shades of one hue, each at least ~28 RGB units from the next."""
    base = np.array(_hex(base_hex or pick(rng, ["#1f77b4", "#2ca02c", "#d62728", "#9467bd"])), float)
    out = []
    for i in range(n):
        t = -0.45 + 0.9 * i / max(1, n - 1)
        c = base + (255 - base) * t if t > 0 else base * (1 + t)
        out.append("#%02x%02x%02x" % tuple(int(round(v)) for v in np.clip(c, 0, 255)))
    order = rng.permutation(n)
    return [out[i] for i in order]


def _style_knobs(rng):
    return {"theme": pick(rng, sorted(THEMES)), "palette": pick(rng, sorted(PALETTES))}


def _press(fig, ax, knobs, title, subtitle, source, grid_axis="y"):
    """House style: headline + standfirst top left, source bottom left, rules on one axis only."""
    th = THEMES[knobs.get("theme", "white")]
    fig.patch.set_facecolor(th["bg"])
    ax.set_facecolor(th["bg"])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(th["text"])
    ax.tick_params(length=0, colors=th["text"], labelsize=9)
    if knobs.get("gridlines", True):
        ax.set_axisbelow(True)
        ax.grid(axis=grid_axis, color=th["grid"], linewidth=0.9)
    ax.set_title(title, loc="left", fontfamily=FACES["serif"], fontweight="bold", fontsize=14, color=th["text"],
                 pad=24 if subtitle else 8)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9.5, color=th["muted"], va="bottom")
    if source:
        fig.text(0.012, 0.012, source, fontsize=7.5, color=th["muted"], va="bottom")


def _save(fig, path: Path) -> tuple[int, int]:
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    fig.savefig(path, dpi=fig.dpi, metadata={"Software": None}, facecolor=fig.get_facecolor())
    return w, h


def _px(ax, x, y, h):
    X, Y = ax.transData.transform((x, y))
    return float(X), float(h - Y)


def _color_near(img: np.ndarray, x: float, y: float, rgb, tol=40, r=2) -> bool:
    H, W = img.shape[:2]
    xi, yi = int(round(x)), int(round(y))
    patch = img[max(0, yi - r):min(H, yi + r + 1), max(0, xi - r):min(W, xi + r + 1), :3].astype(int)
    d = np.sqrt(((patch - np.array(rgb)) ** 2).sum(-1))
    return bool((d < tol).any())


def _labels_overlap(fig, ax) -> bool:
    r = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(r) for t in ax.get_xticklabels() + ax.get_yticklabels() if t.get_text()]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if boxes[i].overlaps(boxes[j]):
                return True
    return False


# ---------------------------------------------------------------- bar chart

BAR_TITLES = {"Units sold": "Units sold by product, this quarter", "Votes": "Votes cast per option",
              "Visitors": "Visitors per site, weekly average", "Score": "Average score by group"}
CALLOUTS = ["New entrant", "Promotion", "Supply issue", "Restocked", "Price cut", "Relaunch"]


def bar_build(rng, diff):
    n = {"easy": rng.integers(4, 6), "medium": rng.integers(6, 9), "hard": rng.integers(9, 13)}[diff]
    labels = pick(rng, FRUITS if rng.random() < 0.5 else WORDS, int(n))
    step = 5 if diff == "easy" else 1
    vals = [int(v) for v in rng.integers(2, 20 if step == 5 else 100, size=int(n)) * step]
    if diff == "easy":
        vals = [max(10, v) for v in vals]
    if diff == "hard" and rng.random() < 0.7:  # near-tie at the top
        i, j = rng.choice(int(n), 2, replace=False)
        top = int(rng.integers(70, 96))
        vals[i], vals[j] = top, top - int(rng.integers(2, 4))
    knobs = {
        "n_bars": int(n),
        "horizontal": bool(diff == "hard" and rng.random() < 0.5),
        "label_rotation": int({"easy": 0, "medium": pick(rng, [0, 30]), "hard": pick(rng, [45, 60, 90])}[diff]),
        "value_labels": bool({"easy": True, "medium": rng.random() < 0.5, "hard": False}[diff]),
        "gridlines": bool(diff != "hard"),
        "colors": {"easy": "single", "medium": "distinct", "hard": pick(rng, ["shades", "distinct"])}[diff],
        "near_tie": bool(diff == "hard"),
        "size": [6.4, 4.8] if diff != "hard" else [6.0, 4.6],
    }
    knobs.update(_style_knobs(rng))
    pal = PALETTES[knobs["palette"]]
    if knobs["colors"] == "single":
        colors = [pal[0]] * int(n)
    elif knobs["colors"] == "distinct":
        colors = pal[: int(n)]
    else:
        colors = _shades(rng, int(n), pal[0])
    title = pick(rng, sorted(BAR_TITLES))
    spec = {"labels": labels, "values": vals, "colors": colors, "title": title,
            "subtitle": BAR_TITLES[title], "source": pick(rng, SOURCES)}
    knobs["dual_axis"] = bool(diff == "hard" and not knobs["horizontal"])
    knobs["callout"] = bool(diff == "hard" or (diff == "medium" and rng.random() < 0.4))
    if knobs["dual_axis"]:
        spec["overlay"] = {"name": pick(rng, ["Margin, %", "Share of total, %", "Growth, %"]),
                           "values": _overlay_values(rng, vals),
                           "color": "#3b3b3b" if knobs["colors"] != "single" else pal[1]}
    if knobs["callout"]:
        spec["callout"] = {"index": int(rng.integers(int(n))), "text": pick(rng, CALLOUTS)}
    return spec, knobs


def _overlay_values(rng, vals):
    """Second-axis values that keep clear of every bar tip (both axes share the plot height)."""
    lim = math.ceil(max(vals) * 1.3 / 10) * 10
    out = []
    for v in vals:
        o = int(rng.integers(8, 93))
        while abs(o / 100 - v / lim) < 0.06:
            o = int(rng.integers(8, 93))
        out.append(o)
    return out


def bar_render(spec, knobs, path):
    th = THEMES[knobs.get("theme", "white")]
    fig, ax = plt.subplots(figsize=knobs["size"], dpi=100)
    n = len(spec["values"])
    x = np.arange(n)
    if knobs["horizontal"]:
        bars = ax.barh(x, spec["values"], color=spec["colors"], height=0.6)
        ax.set_yticks(x, spec["labels"])
        ax.invert_yaxis()
    else:
        bars = ax.bar(x, spec["values"], color=spec["colors"], width=0.6)
        ax.set_xticks(x, spec["labels"], rotation=knobs["label_rotation"], fontsize=9,
                      ha="right" if knobs["label_rotation"] not in (0, 90) else "center")
    vmax = max(spec["values"])
    head = 1.3 if (spec.get("callout") or spec.get("overlay")) else 1.15
    lim = math.ceil(vmax * head / 10) * 10
    (ax.set_xlim if knobs["horizontal"] else ax.set_ylim)(0, lim)
    _press(fig, ax, knobs, spec["title"], spec.get("subtitle"), spec.get("source"),
           grid_axis="x" if knobs["horizontal"] else "y")
    if knobs["value_labels"]:
        ax.bar_label(bars, padding=2, fontsize=8, color=th["text"])
    ov = spec.get("overlay")
    ax2 = None
    if ov:
        ax2 = ax.twinx()
        ax2.plot(x, ov["values"], color=ov["color"], lw=1.6, marker="o", ms=4, zorder=5)
        ax2.set_ylim(0, 100)
        for s in ("top", "left", "bottom"):
            ax2.spines[s].set_visible(False)
        ax2.spines["right"].set_visible(False)
        ax2.tick_params(length=0, colors=th["muted"], labelsize=8)
        ax2.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%d%%"))
        from matplotlib.lines import Line2D
        from matplotlib.patches import Patch
        ax.legend([Patch(color=spec["colors"][0]), Line2D([0], [0], color=ov["color"], marker="o", ms=4)],
                  [f"{spec['title']} (left)", f"{ov['name']} (right)"], loc="upper left", fontsize=8,
                  frameon=False, ncol=2, bbox_to_anchor=(0, 1.0))
    co = spec.get("callout")
    if co:
        i, v = co["index"], spec["values"][co["index"]]
        if knobs["horizontal"]:
            ax.annotate(co["text"], xy=(v + 0.015 * lim, i), xytext=(26, 0), textcoords="offset points",
                        va="center", fontsize=8, color=th["text"], fontstyle="italic",
                        arrowprops={"arrowstyle": "-", "color": th["muted"], "lw": 0.8})
        else:
            ax.annotate(co["text"], xy=(i, v + 0.02 * lim), xytext=(0, 22), textcoords="offset points",
                        ha="center", fontsize=8, color=th["text"], fontstyle="italic",
                        arrowprops={"arrowstyle": "-", "color": th["muted"], "lw": 0.8})
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.canvas.draw()
    overlap = _labels_overlap(fig, ax)
    w, h = fig.canvas.get_width_height()
    geo = []
    half = 0.3
    for i, v in enumerate(spec["values"]):
        if knobs["horizontal"]:
            x0, yc = _px(ax, 0, i, h)
            x1, _ = _px(ax, v, i, h)
            hw = abs(_px(ax, 0, i + half, h)[1] - yc)
            geo.append({"axis": "x", "c": yc, "base": x0, "tip": x1, "hw": hw})
        else:
            xc, y0 = _px(ax, i, 0, h)
            _, y1 = _px(ax, i, v, h)
            hw = abs(_px(ax, i + half, 0, h)[0] - xc)
            geo.append({"axis": "y", "c": xc, "base": y0, "tip": y1, "hw": hw})
    _, ppu = _px(ax, 0, 1, h)
    _, p0 = _px(ax, 0, 0, h)
    if knobs["horizontal"]:
        ppu = abs(_px(ax, 1, 0, h)[0] - _px(ax, 0, 0, h)[0])
    else:
        ppu = abs(ppu - p0)
    overlay_px = [_px(ax2, i, v, h) for i, v in enumerate(ov["values"])] if ov else []
    legend_box = None
    if ax.get_legend() is not None:
        bb = ax.get_legend().get_window_extent(fig.canvas.get_renderer())
        legend_box = [float(bb.x0), float(h - bb.y1), float(bb.x1), float(h - bb.y0)]
    _save(fig, path)
    plt.close(fig)
    return {"w": w, "h": h, "bars": geo, "px_per_unit": ppu, "axis_max": lim, "label_overlap": overlap,
            "value_labels": knobs["value_labels"], "overlay_px": overlay_px, "dual_axis": bool(ov), "legend_box": legend_box}


def bar_probe(spec, info, img):
    fails = []
    if info["label_overlap"]:
        fails.append("tick labels overlap")
    for i, (g, c) in enumerate(zip(info["bars"], spec["colors"])):
        rgb = np.array(_hex(c))
        if g["axis"] == "y":
            col = img[:, int(round(g["c"])), :3].astype(int)
        else:
            col = img[int(round(g["c"])), :, :3].astype(int)
        mask = np.sqrt(((col - rgb) ** 2).sum(-1)) < 12
        mid = int(round((g["base"] + g["tip"]) / 2))
        if not mask[mid]:
            fails.append(f"bar {i} colour not found at its midpoint")
            continue
        lo, hi = mid, mid
        while lo > 0 and mask[lo - 1]:
            lo -= 1
        while hi < len(mask) - 1 and mask[hi + 1]:
            hi += 1
        measured = hi - lo + 1
        expected = abs(g["base"] - g["tip"])
        if abs(measured - expected) > 3:
            fails.append(f"bar {i} length {measured}px, expected {expected:.1f}px")
    return fails


def bar_ask(spec, info, rng, diff):
    labels, vals = spec["labels"], spec["values"]
    ppu = info["px_per_unit"]
    order = sorted(range(len(vals)), key=lambda i: -vals[i])
    qtypes = ["tallest", "shortest", "value_of", "count_above", "diff", "top3"]
    qt = pick(rng, qtypes)
    word = "longest" if spec and info["bars"][0]["axis"] == "x" else "tallest"
    axis = " (read it on the left axis)" if info.get("dual_axis") else ""
    if qt == "tallest":
        if (vals[order[0]] - vals[order[1]]) * ppu < 3:
            raise Reject("top two bars within 3px")
        return Question(qt, {}, f"Which bar is the {word}?", labels[order[0]], "exact",
                        format_hint="the bar's label", choices=labels)
    if qt == "shortest":
        if (vals[order[-2]] - vals[order[-1]]) * ppu < 3:
            raise Reject("bottom two bars within 3px")
        word2 = "shortest"
        return Question(qt, {}, f"Which bar is the {word2}?", labels[order[-1]], "exact",
                        format_hint="the bar's label", choices=labels)
    if qt == "value_of":
        i = int(rng.integers(len(vals)))
        tol = 0.0 if _labelled(spec, info) else round(0.05 * info["axis_max"], 2)
        return Question(qt, {"label": labels[i]}, f"What is the value of the bar labelled {labels[i]}{axis}?",
                        vals[i], "numeric", tolerance=tol, format_hint="a number")
    if qt == "count_above":
        lim = info["axis_max"]
        cands = [t for t in range(10, lim, 5) if min(vals) < t < max(vals) and all(abs(v - t) >= 0.04 * lim for v in vals)]
        if not cands:
            raise Reject("no clear threshold")
        t = pick(rng, cands)
        return Question(qt, {"threshold": t}, f"How many bars have a value greater than {t}{axis}?",
                        sum(v > t for v in vals), "numeric", format_hint="a whole number")
    if qt == "diff":
        i, j = (int(k) for k in rng.choice(len(vals), 2, replace=False))
        tol = 0.0 if _labelled(spec, info) else round(0.08 * info["axis_max"], 2)
        return Question(qt, {"a": labels[i], "b": labels[j]},
                        f"What is the value of {labels[i]} minus the value of {labels[j]}{axis}?",
                        vals[i] - vals[j], "numeric", tolerance=tol, format_hint="a number (may be negative)")
    # top3: ordering of the three largest
    for k in range(3):
        if (vals[order[k]] - vals[order[k + 1]]) * ppu < 3:
            raise Reject("top-3 ordering within 3px")
    return Question(qt, {}, "List the three largest bars from largest to smallest.",
                    [labels[i] for i in order[:3]], "ordering", format_hint="three labels separated by commas", choices=labels)


def _labelled(spec, info):
    return info.get("value_labels", False)


# ---------------------------------------------------------------- line chart

LINE_TITLES = {"Monthly revenue": "Revenue index by business line", "Active users": "Active users by app, index",
               "Temperature index": "Regional temperature index", "Orders": "Orders by channel, index"}
BANDS = ["Promotion", "Holiday period", "Strike", "Outage", "Trial period"]


def line_build(rng, diff):
    k = {"easy": 2, "medium": int(rng.integers(2, 4)), "hard": int(rng.integers(3, 5))}[diff]
    n = {"easy": 6, "medium": 8, "hard": 12}[diff]
    names = pick(rng, WORDS, k)
    series = []
    for _ in range(k):
        v = [float(rng.integers(20, 80))]
        for _ in range(n - 1):
            v.append(float(np.clip(v[-1] + rng.normal(0, 12 if diff != "easy" else 8), 5, 95)))
        series.append([int(round(x)) for x in v])
    knobs = {
        "n_series": k, "n_points": n,
        "markers": bool(diff != "hard"),
        "gridlines": bool(diff == "easy" or (diff == "medium" and rng.random() < 0.5)),
        "legend": "outside" if diff == "hard" else "inside",
        "linestyles": bool(diff == "hard" and rng.random() < 0.5),
        "size": [6.4, 4.8],
    }
    knobs.update(_style_knobs(rng))
    knobs["gridlines"] = True if knobs["theme"] != "white" else knobs["gridlines"]
    knobs["band"] = bool(diff == "hard")
    title = pick(rng, sorted(LINE_TITLES))
    spec = {"x": MONTHS[:n], "names": names, "series": series, "colors": PALETTES[knobs["palette"]][:k],
            "title": title, "subtitle": LINE_TITLES[title], "source": pick(rng, SOURCES)}
    if knobs["band"]:
        a = int(rng.integers(1, n - 3))
        spec["band"] = {"from": a, "to": a + int(rng.integers(1, 3)), "text": pick(rng, BANDS)}
    return spec, knobs


def line_render(spec, knobs, path):
    th = THEMES[knobs.get("theme", "white")]
    fig, ax = plt.subplots(figsize=knobs["size"], dpi=100)
    xs = np.arange(len(spec["x"]))
    styles = ["-", "--", ":", "-."] if knobs["linestyles"] else ["-"] * 4
    band = spec.get("band")
    if band:
        ax.axvspan(band["from"], band["to"], color=th["grid"], alpha=0.55, lw=0, zorder=0)
        ax.text((band["from"] + band["to"]) / 2, 98, band["text"], ha="center", va="top", fontsize=8,
                color=th["muted"], fontstyle="italic", zorder=1)
    for s, (name, ys, c) in enumerate(zip(spec["names"], spec["series"], spec["colors"])):
        ax.plot(xs, ys, styles[s], color=c, lw=2.2, marker="o" if knobs["markers"] else None, ms=5, label=name)
    ax.set_xticks(xs, spec["x"])
    ax.set_ylim(0, 100)
    _press(fig, ax, knobs, spec["title"], spec.get("subtitle"), spec.get("source"))
    if knobs["legend"] == "outside":
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False, fontsize=9)
    else:
        ax.legend(loc="upper right", fontsize=8, frameon=False, ncol=len(spec["names"]))
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    pts = [[_px(ax, i, y, h) for i, y in enumerate(ys)] for ys in spec["series"]]
    ppu = abs(_px(ax, 0, 1, h)[1] - _px(ax, 0, 0, h)[1])
    legend_box = None
    if knobs["legend"] != "outside":
        bb = ax.get_legend().get_window_extent(fig.canvas.get_renderer())
        legend_box = [float(bb.x0), float(h - bb.y1), float(bb.x1), float(h - bb.y0)]
    band_box = None
    if band:
        bb = ax.texts[0].get_window_extent(fig.canvas.get_renderer())
        band_box = [float(bb.x0), float(h - bb.y1), float(bb.x1), float(h - bb.y0)]
    _save(fig, path)
    plt.close(fig)
    return {"w": w, "h": h, "points": pts, "px_per_unit": ppu, "legend_box": legend_box, "band_box": band_box}


def line_probe(spec, info, img):
    fails = []
    for s, (pts, c) in enumerate(zip(info["points"], spec["colors"])):
        rgb = _hex(c)
        miss = [i for i, (x, y) in enumerate(pts) if not _color_near(img, x, y, rgb, tol=60, r=3)]
        # a point may be hidden under another series' line; allow at most one per series
        if len(miss) > 1:
            fails.append(f"series {s} points {miss} not visible")
    return fails


def line_ask(spec, info, rng, diff):
    names, S, xs = spec["names"], np.array(spec["series"]), spec["x"]
    ppu = info["px_per_unit"]
    qt = pick(rng, ["highest_at", "value_at", "peak_month", "crossings"])
    if qt == "highest_at":
        j = int(rng.integers(len(xs)))
        col = sorted(S[:, j], reverse=True)
        if (col[0] - col[1]) * ppu < 5:
            raise Reject("near tie at x")
        return Question(qt, {"x": xs[j]}, f"Which series has the highest value in {xs[j]}?",
                        names[int(np.argmax(S[:, j]))], "exact", format_hint="a series name from the legend", choices=names)
    if qt == "value_at":
        s, j = int(rng.integers(len(names))), int(rng.integers(len(xs)))
        tol = 5.0 if spec and diff != "easy" else 4.0
        return Question(qt, {"series": names[s], "x": xs[j]}, f"What is the value of {names[s]} in {xs[j]}?",
                        int(S[s, j]), "numeric", tolerance=tol, format_hint="a number")
    if qt == "peak_month":
        s = int(rng.integers(len(names)))
        row = sorted(S[s], reverse=True)
        if (row[0] - row[1]) * ppu < 5:
            raise Reject("near tie peak")
        return Question(qt, {"series": names[s]}, f"In which month does {names[s]} reach its highest value?",
                        xs[int(np.argmax(S[s]))], "exact", format_hint="a month name as on the x axis", choices=xs)
    a, b = (int(k) for k in rng.choice(len(names), 2, replace=False))
    d = S[a] - S[b]
    if (np.abs(d) * ppu < 6).any():
        raise Reject("series too close at some x")
    crossings = int((np.sign(d[1:]) != np.sign(d[:-1])).sum())
    return Question(qt, {"a": names[a], "b": names[b]},
                    f"How many times do the lines {names[a]} and {names[b]} cross each other?",
                    crossings, "numeric", format_hint="a whole number")


# ---------------------------------------------------------------- pie chart

def _split100(rng, k, min_share):
    while True:
        cuts = np.sort(rng.choice(np.arange(1, 100), k - 1, replace=False))
        parts = np.diff(np.concatenate([[0], cuts, [100]]))
        if parts.min() >= min_share:
            return [int(p) for p in parts]


PIE_TITLES = {"Market share": "Share of unit sales, %", "Budget split": "Planned spending by area, %",
              "Survey answers": "Preferred option among respondents, %"}


def pie_build(rng, diff):
    k = {"easy": int(rng.integers(3, 5)), "medium": int(rng.integers(4, 7)), "hard": int(rng.integers(6, 9))}[diff]
    shares = _split100(rng, k, 4)
    knobs = {
        "n_slices": k,
        "labels": {"easy": "pct", "medium": "name", "hard": "legend"}[diff],
        "colors": "shades" if diff == "hard" and rng.random() < 0.5 else "distinct",
        "start_angle": int(pick(rng, [90, 0, 45, 135])) if diff != "easy" else 90,
        "size": [5.8, 4.8],
    }
    knobs.update(_style_knobs(rng))
    knobs["donut"] = bool(diff == "hard")
    pal = PALETTES[knobs["palette"]]
    colors = pal[:k] if knobs["colors"] == "distinct" else _shades(rng, k, pal[0])
    title = pick(rng, sorted(PIE_TITLES))
    spec = {"names": pick(rng, FRUITS, k), "shares": shares, "colors": colors, "title": title,
            "subtitle": PIE_TITLES[title], "source": pick(rng, SOURCES)}
    return spec, knobs


def pie_render(spec, knobs, path):
    th = THEMES[knobs.get("theme", "white")]
    fig, ax = plt.subplots(figsize=knobs["size"], dpi=100)
    lab = spec["names"] if knobs["labels"] in ("pct", "name") else None
    kw = {"autopct": (lambda p: f"{round(p)}%")} if knobs["labels"] == "pct" else {}
    if kw:
        kw["textprops"] = {"color": th["text"], "fontsize": 9}
    donut = knobs.get("donut", False)
    wp = {"edgecolor": th["bg"], "linewidth": 1.5}
    if donut:
        wp["width"] = 0.42
    res = ax.pie(spec["shares"], labels=lab, colors=spec["colors"], startangle=knobs["start_angle"],
                 counterclock=False, wedgeprops=wp, labeldistance=1.08, **kw)
    wedges = res[0]
    if knobs["labels"] == "pct":
        for t in res[2]:
            t.set_color("white")
            t.set_fontweight("bold")
    if donut:
        ax.text(0, 0, "Share of\ntotal", ha="center", va="center", fontsize=9, color=th["muted"])
    if knobs["labels"] == "legend":
        ax.legend(wedges, spec["names"], loc="center left", bbox_to_anchor=(0.98, 0.5), fontsize=9, frameon=False)
    _press(fig, ax, dict(knobs, gridlines=False), spec["title"], spec.get("subtitle"), spec.get("source"))
    ax.spines["bottom"].set_visible(False)
    ax.set_aspect("equal")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    probes = []
    for wd in wedges:
        mid = math.radians((wd.theta1 + wd.theta2) / 2)
        cx, cy, r = wd.center[0], wd.center[1], wd.r
        r_frac = 0.79 if donut else (0.8 if knobs["labels"] == "pct" else 0.55)
        probes.append(_px(ax, cx + r_frac * r * math.cos(mid), cy + r_frac * r * math.sin(mid), h))
    _save(fig, path)
    plt.close(fig)
    return {"w": w, "h": h, "probes": probes, "pct_shown": knobs["labels"] == "pct"}


def pie_probe(spec, info, img):
    fails = []
    for i, ((x, y), c) in enumerate(zip(info["probes"], spec["colors"])):
        if not _color_near(img, x, y, _hex(c), tol=20, r=1):
            fails.append(f"wedge {i} colour missing at mid-angle")
    cols = [np.array(_hex(c)) for c in spec["colors"]]
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            if np.sqrt(((cols[i] - cols[j]) ** 2).sum()) < 25:
                fails.append(f"wedges {i},{j} colours too similar")
    return fails


def pie_ask(spec, info, rng, diff):
    names, sh = spec["names"], spec["shares"]
    qt = pick(rng, ["largest", "smallest", "share_of"])
    srt = sorted(sh, reverse=True)
    if qt == "largest":
        if srt[0] - srt[1] < 3:
            raise Reject("near tie largest")
        return Question(qt, {}, "Which slice is the largest?", names[sh.index(srt[0])], "exact",
                        format_hint="the slice name", choices=names)
    if qt == "smallest":
        if srt[-2] - srt[-1] < 3:
            raise Reject("near tie smallest")
        return Question(qt, {}, "Which slice is the smallest?", names[sh.index(srt[-1])], "exact",
                        format_hint="the slice name", choices=names)
    i = int(rng.integers(len(names)))
    tol = 0.0 if info.get("pct_shown") else 5.0
    return Question(qt, {"name": names[i]}, f"What percentage of the whole is {names[i]}?", sh[i], "numeric",
                    tolerance=tol, format_hint="a percentage number without the % sign")


def _fam(name, build, render, ask, probe):
    register(Family(name, build, render, ask, probe))


_fam("bar_chart", bar_build, bar_render, bar_ask, bar_probe)
_fam("line_chart", line_build, line_render, line_ask, line_probe)
_fam("pie_chart", pie_build, pie_render, pie_ask, pie_probe)
