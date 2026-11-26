"""Bar, line and pie charts rendered with matplotlib.

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

plt.rcParams.update({"font.family": "DejaVu Sans", "svg.hashsalt": "vtf"})

DISTINCT = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#ff9896",
            "#bcbd22", "#17becf", "#393b79", "#637939"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _shades(rng, n: int) -> list[str]:
    """n similar shades of one hue, each at least ~28 RGB units from the next."""
    base = np.array(_hex(pick(rng, ["#1f77b4", "#2ca02c", "#d62728", "#9467bd"])), float)
    out = []
    for i in range(n):
        t = -0.45 + 0.9 * i / max(1, n - 1)
        c = base + (255 - base) * t if t > 0 else base * (1 + t)
        out.append("#%02x%02x%02x" % tuple(int(round(v)) for v in np.clip(c, 0, 255)))
    order = rng.permutation(n)
    return [out[i] for i in order]


def _save(fig, path: Path) -> tuple[int, int]:
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    fig.savefig(path, dpi=fig.dpi, metadata={"Software": None})
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
        "size": [6.4, 4.8] if diff != "hard" else [5.6, 4.2],
    }
    if knobs["colors"] == "single":
        colors = ["#1f77b4"] * int(n)
    elif knobs["colors"] == "distinct":
        colors = DISTINCT[: int(n)]
    else:
        colors = _shades(rng, int(n))
    spec = {"labels": labels, "values": vals, "colors": colors, "title": pick(rng, ["Units sold", "Votes", "Visitors", "Score"])}
    return spec, knobs


def bar_render(spec, knobs, path):
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
    lim = math.ceil(vmax * 1.15 / 10) * 10
    (ax.set_xlim if knobs["horizontal"] else ax.set_ylim)(0, lim)
    if knobs["gridlines"]:
        ax.set_axisbelow(True)
        ax.grid(axis="x" if knobs["horizontal"] else "y", color="#dddddd")
    if knobs["value_labels"]:
        ax.bar_label(bars, padding=2, fontsize=8)
    ax.set_title(spec["title"])
    fig.tight_layout()
    fig.canvas.draw()
    overlap = _labels_overlap(fig, ax)
    w, h = fig.canvas.get_width_height()
    geo = []
    for i, v in enumerate(spec["values"]):
        if knobs["horizontal"]:
            x0, yc = _px(ax, 0, i, h)
            x1, _ = _px(ax, v, i, h)
            geo.append({"axis": "x", "c": yc, "base": x0, "tip": x1})
        else:
            xc, y0 = _px(ax, i, 0, h)
            _, y1 = _px(ax, i, v, h)
            geo.append({"axis": "y", "c": xc, "base": y0, "tip": y1})
    _, ppu = _px(ax, 0, 1, h)
    _, p0 = _px(ax, 0, 0, h)
    if knobs["horizontal"]:
        ppu = abs(_px(ax, 1, 0, h)[0] - _px(ax, 0, 0, h)[0])
    else:
        ppu = abs(ppu - p0)
    _save(fig, path)
    plt.close(fig)
    return {"w": w, "h": h, "bars": geo, "px_per_unit": ppu, "axis_max": lim, "label_overlap": overlap,
            "value_labels": knobs["value_labels"]}


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
        return Question(qt, {"label": labels[i]}, f"What is the value of the bar labelled {labels[i]}?",
                        vals[i], "numeric", tolerance=tol, format_hint="a number")
    if qt == "count_above":
        lim = info["axis_max"]
        cands = [t for t in range(10, lim, 5) if min(vals) < t < max(vals) and all(abs(v - t) >= 0.04 * lim for v in vals)]
        if not cands:
            raise Reject("no clear threshold")
        t = pick(rng, cands)
        return Question(qt, {"threshold": t}, f"How many bars have a value greater than {t}?",
                        sum(v > t for v in vals), "numeric", format_hint="a whole number")
    if qt == "diff":
        i, j = (int(k) for k in rng.choice(len(vals), 2, replace=False))
        tol = 0.0 if _labelled(spec, info) else round(0.08 * info["axis_max"], 2)
        return Question(qt, {"a": labels[i], "b": labels[j]},
                        f"What is the value of {labels[i]} minus the value of {labels[j]}?",
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
    spec = {"x": MONTHS[:n], "names": names, "series": series, "colors": DISTINCT[:k],
            "title": pick(rng, ["Monthly revenue", "Active users", "Temperature index", "Orders"])}
    return spec, knobs


def line_render(spec, knobs, path):
    fig, ax = plt.subplots(figsize=knobs["size"], dpi=100)
    xs = np.arange(len(spec["x"]))
    styles = ["-", "--", ":", "-."] if knobs["linestyles"] else ["-"] * 4
    for s, (name, ys, c) in enumerate(zip(spec["names"], spec["series"], spec["colors"])):
        ax.plot(xs, ys, styles[s], color=c, lw=2, marker="o" if knobs["markers"] else None, ms=5, label=name)
    ax.set_xticks(xs, spec["x"])
    ax.set_ylim(0, 100)
    if knobs["gridlines"]:
        ax.grid(color="#dddddd")
    if knobs["legend"] == "outside":
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
    else:
        ax.legend(loc="upper right", fontsize=8)
    ax.set_title(spec["title"])
    fig.tight_layout()
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    pts = [[_px(ax, i, y, h) for i, y in enumerate(ys)] for ys in spec["series"]]
    ppu = abs(_px(ax, 0, 1, h)[1] - _px(ax, 0, 0, h)[1])
    _save(fig, path)
    plt.close(fig)
    return {"w": w, "h": h, "points": pts, "px_per_unit": ppu}


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


def pie_build(rng, diff):
    k = {"easy": int(rng.integers(3, 5)), "medium": int(rng.integers(4, 7)), "hard": int(rng.integers(6, 9))}[diff]
    shares = _split100(rng, k, 4)
    knobs = {
        "n_slices": k,
        "labels": {"easy": "pct", "medium": "name", "hard": "legend"}[diff],
        "colors": "shades" if diff == "hard" and rng.random() < 0.5 else "distinct",
        "start_angle": int(pick(rng, [90, 0, 45, 135])) if diff != "easy" else 90,
        "size": [5.6, 4.8],
    }
    colors = DISTINCT[:k] if knobs["colors"] == "distinct" else _shades(rng, k)
    spec = {"names": pick(rng, FRUITS, k), "shares": shares, "colors": colors,
            "title": pick(rng, ["Market share", "Budget split", "Survey answers"])}
    return spec, knobs


def pie_render(spec, knobs, path):
    fig, ax = plt.subplots(figsize=knobs["size"], dpi=100)
    lab = spec["names"] if knobs["labels"] in ("pct", "name") else None
    kw = {"autopct": "%d%%"} if knobs["labels"] == "pct" else {}
    if kw:
        kw["autopct"] = lambda p: f"{round(p)}%"
    wedges = ax.pie(spec["shares"], labels=lab, colors=spec["colors"], startangle=knobs["start_angle"],
                    counterclock=False, wedgeprops={"edgecolor": "white"}, **kw)[0]
    if knobs["labels"] == "legend":
        ax.legend(wedges, spec["names"], loc="center left", bbox_to_anchor=(0.95, 0.5), fontsize=8)
    ax.set_title(spec["title"])
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    probes = []
    for wd in wedges:
        mid = math.radians((wd.theta1 + wd.theta2) / 2)
        cx, cy, r = wd.center[0], wd.center[1], wd.r
        r_frac = 0.8 if knobs["labels"] == "pct" else 0.55
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
