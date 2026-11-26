"""Shape scenes, analog clocks and grid mazes drawn with Pillow."""

from __future__ import annotations

import math
from collections import deque

import numpy as np
from PIL import Image, ImageDraw

from ..core import NAMED_COLORS, Family, Question, Reject, pick, register
from .text import font

# ---------------------------------------------------------------- shapes

KINDS = ["circle", "square", "triangle", "diamond"]


def _poly(kind, x, y, r):
    if kind == "square":
        return [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]
    if kind == "triangle":
        return [(x + r * math.cos(a), y + r * math.sin(a)) for a in (-math.pi / 2, math.pi / 6, 5 * math.pi / 6)]
    if kind == "diamond":
        return [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
    return None


def _area(kind, r):
    return {"circle": math.pi * r * r, "square": 4 * r * r, "triangle": 3 * math.sqrt(3) / 4 * r * r,
            "diamond": 2 * r * r}[kind]


def shapes_build(rng, diff):
    W, H = (640, 480)
    n = int({"easy": rng.integers(4, 8), "medium": rng.integers(8, 13), "hard": rng.integers(13, 21)}[diff])
    ncol = {"easy": 3, "medium": 5, "hard": 8}[diff]
    colors = pick(rng, list(NAMED_COLORS), ncol)
    kinds = KINDS[:3] if diff == "easy" else KINDS
    overlap = diff == "hard"
    objs = []
    tries = 0
    while len(objs) < n and tries < 2000:
        tries += 1
        r = int(rng.integers(16, 46 if diff != "hard" else 40))
        x, y = int(rng.integers(r + 4, W - r - 4)), int(rng.integers(r + 4, H - r - 4))
        gap = 6 if not overlap else -0.3 * (r + 30)
        if any(math.hypot(x - o["x"], y - o["y"]) < r + o["r"] + gap for o in objs):
            continue
        k = pick(rng, kinds)
        objs.append({"kind": k, "color": pick(rng, colors), "x": x, "y": y, "r": r, "size": round(_area(k, r), 1)})
    knobs = {"n_objects": len(objs), "n_colors": ncol, "overlap": overlap,
             "background": "noise" if diff == "hard" else "plain", "kinds": len(kinds)}
    return {"w": W, "h": H, "objects": objs}, knobs


def shapes_render(spec, knobs, path):
    W, H = spec["w"], spec["h"]
    img = Image.new("RGB", (W, H), (255, 255, 255))
    if knobs["background"] == "noise":
        rng = np.random.default_rng(len(spec["objects"]) * 7919 + spec["objects"][0]["x"])
        arr = 235 + rng.integers(0, 20, size=(H, W, 1))
        img = Image.fromarray(np.repeat(arr, 3, axis=2).astype("uint8"))
    mask = Image.new("I", (W, H), 0)
    d, dm = ImageDraw.Draw(img), ImageDraw.Draw(mask)
    full = []
    for i, o in enumerate(spec["objects"]):
        c = NAMED_COLORS[o["color"]]
        solo = Image.new("L", (W, H), 0)
        ds = ImageDraw.Draw(solo)
        p = _poly(o["kind"], o["x"], o["y"], o["r"])
        box = [o["x"] - o["r"], o["y"] - o["r"], o["x"] + o["r"], o["y"] + o["r"]]
        if p is None:
            d.ellipse(box, fill=c, outline=(0, 0, 0), width=2)
            dm.ellipse(box, fill=i + 1)
            ds.ellipse(box, fill=255)
        else:
            d.polygon(p, fill=c, outline=(0, 0, 0), width=2)
            dm.polygon(p, fill=i + 1)
            ds.polygon(p, fill=255)
        full.append(int((np.asarray(solo) > 0).sum()))
    img.save(path, optimize=False)
    m = np.asarray(mask)
    visible = [int((m == i + 1).sum()) for i in range(len(spec["objects"]))]
    return {"w": W, "h": H, "full_px": full, "visible_px": visible, "_mask": m}


def shapes_probe(spec, info, img):
    fails = []
    m = info.pop("_mask")
    for i, o in enumerate(spec["objects"]):
        full, vis = info["full_px"][i], info["visible_px"][i]
        if abs(full - o["size"]) > 0.12 * o["size"] + 20:
            fails.append(f"object {i} area {full}px vs spec {o['size']}")
        if vis < 0.6 * full:
            fails.append(f"object {i} only {vis / max(full, 1):.0%} visible")
            continue
        region = img[m == i + 1].astype(int)
        good = (np.sqrt(((region - np.array(NAMED_COLORS[o["color"]])) ** 2).sum(-1)) < 30).mean()
        if good < 0.45:  # outlines and antialiasing eat a margin
            fails.append(f"object {i} colour match {good:.0%}")
    return fails


def shapes_ask(spec, info, rng, diff):
    objs = spec["objects"]
    qt = pick(rng, ["count_color", "count_kind", "count_combo", "largest_color", "leftmost_kind", "total"])
    if qt == "count_color":
        c = pick(rng, sorted({o["color"] for o in objs}))
        return Question(qt, {"color": c}, f"How many {c} shapes are there?",
                        sum(o["color"] == c for o in objs), "numeric", format_hint="a whole number")
    if qt == "count_kind":
        k = pick(rng, sorted({o["kind"] for o in objs}))
        return Question(qt, {"kind": k}, f"How many {k}s are there?",
                        sum(o["kind"] == k for o in objs), "numeric", format_hint="a whole number")
    if qt == "count_combo":
        o = pick(rng, objs)
        k, c = o["kind"], o["color"]
        return Question(qt, {"kind": k, "color": c}, f"How many {c} {k}s are there?",
                        sum(x["kind"] == k and x["color"] == c for x in objs), "numeric", format_hint="a whole number")
    if qt == "largest_color":
        s = sorted(objs, key=lambda o: -o["size"])
        if s[0]["size"] < 1.3 * s[1]["size"]:
            raise Reject("largest shape not clearly largest")
        i = objs.index(s[0])
        if info["visible_px"][i] < 0.95 * info["full_px"][i]:
            raise Reject("largest shape partly hidden")
        return Question(qt, {}, "What colour is the largest shape?", s[0]["color"], "exact", format_hint="a colour name",
                        choices=list(NAMED_COLORS))
    if qt == "leftmost_kind":
        s = sorted(objs, key=lambda o: o["x"] - o["r"])
        if (s[1]["x"] - s[1]["r"]) - (s[0]["x"] - s[0]["r"]) < 15:
            raise Reject("leftmost not clear")
        return Question(qt, {}, "What kind of shape is furthest to the left?", s[0]["kind"], "exact",
                        format_hint="one of: circle, square, triangle, diamond", choices=KINDS)
    return Question(qt, {}, "How many shapes are in the image in total?", len(objs), "numeric",
                    format_hint="a whole number")


# ---------------------------------------------------------------- clock

def clock_build(rng, diff):
    h = int(rng.integers(1, 13))
    m = int(rng.integers(0, 12) * 5) if diff != "hard" else int(rng.integers(0, 60))
    knobs = {
        "numerals": {"easy": "all", "medium": pick(rng, ["quarters", "roman"]), "hard": "none"}[diff],
        "minute_ticks": diff != "medium",
        "second_hand": diff == "hard",
        "similar_hands": diff == "hard",
        "size": 400 if diff != "hard" else 320,
    }
    sec = int(rng.integers(0, 60))
    return {"hour": h, "minute": m, "second": sec}, knobs


def _angles(spec):
    h, m, s = spec["hour"], spec["minute"], spec["second"]
    return (30 * (h % 12) + 0.5 * m) % 360, 6 * m, 6 * s


ROMAN = ["XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]


def clock_render(spec, knobs, path):
    S = knobs["size"]
    img = Image.new("RGB", (S, S), (250, 248, 240))
    d = ImageDraw.Draw(img)
    c, R = S / 2, S * 0.44
    d.ellipse([c - R, c - R, c + R, c + R], fill=(255, 255, 255), outline=(20, 20, 20), width=4)
    for t in range(60):
        a = math.radians(t * 6)
        if t % 5 == 0:
            r0, w = R * (0.84 if t == 0 and knobs["numerals"] == "none" else 0.88), 4 if t else 7
        elif knobs["minute_ticks"]:
            r0, w = R * 0.94, 1
        else:
            continue
        d.line([(c + r0 * math.sin(a), c - r0 * math.cos(a)), (c + R * 0.98 * math.sin(a), c - R * 0.98 * math.cos(a))],
               fill=(20, 20, 20), width=w)
    f = font(int(S * 0.07))
    for k in range(12):
        if knobs["numerals"] == "none" or (knobs["numerals"] == "quarters" and k % 3):
            continue
        txt = ROMAN[k] if knobs["numerals"] == "roman" else str(12 if k == 0 else k)
        a = math.radians(k * 30)
        d.text((c + R * 0.74 * math.sin(a), c - R * 0.74 * math.cos(a)), txt, fill=(20, 20, 20), font=f, anchor="mm")
    ha, ma, sa = _angles(spec)
    hl, ml = (0.62, 0.72) if knobs["similar_hands"] else (0.5, 0.8)
    hw, mw = (7, 6) if knobs["similar_hands"] else (10, 5)
    hands = {"hour": (ha, hl, hw), "minute": (ma, ml, mw)}
    for a, L, w in hands.values():
        r = math.radians(a)
        d.line([(c, c), (c + R * L * math.sin(r), c - R * L * math.cos(r))], fill=(15, 15, 15), width=w)
    if knobs["second_hand"]:
        r = math.radians(sa)
        d.line([(c - R * 0.15 * math.sin(r), c + R * 0.15 * math.cos(r)), (c + R * 0.85 * math.sin(r), c - R * 0.85 * math.cos(r))],
               fill=(200, 30, 30), width=2)
    d.ellipse([c - 7, c - 7, c + 7, c + 7], fill=(15, 15, 15))
    img.save(path)
    return {"w": S, "h": S, "c": c, "R": R, "hands": {k: [a, L] for k, (a, L, _) in hands.items()},
            "second_hand": knobs["second_hand"]}


def clock_probe(spec, info, img):
    fails = []
    c, R = info["c"], info["R"]
    for name, (a, L) in info["hands"].items():
        r = math.radians(a)
        for frac in (0.35, 0.9):
            x, y = c + R * L * frac * math.sin(r), c - R * L * frac * math.cos(r)
            if img[int(round(y)), int(round(x))].astype(int).sum() > 3 * 90:
                fails.append(f"{name} hand missing at {frac:.0%} of its length")
    return fails


def _angdiff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def clock_ask(spec, info, rng, diff):
    ha, ma, sa = _angles(spec)
    if _angdiff(ha, ma) < 12:
        raise Reject("hour and minute hands overlap")
    if info.get("second_hand") and min(_angdiff(sa, ha), _angdiff(sa, ma)) < 10:
        raise Reject("second hand covers another hand")
    h, m = spec["hour"], spec["minute"]
    tol = 1.0 if diff == "hard" else 0.0
    if m != 0 and rng.random() < 0.3:
        return Question("minutes_to_hour", {}, "How many minutes are left until the next full hour?", 60 - m,
                        "numeric", tolerance=tol, format_hint="a whole number")
    return Question("time", {}, "What time does the clock show? Ignore any red second hand.", f"{h}:{m:02d}", "time",
                    tolerance=tol, format_hint="H:MM in 12-hour form, for example 7:05")


# ---------------------------------------------------------------- grid path

def _bfs(n, walls, s, g):
    seen = {tuple(s): 0}
    q = deque([tuple(s)])
    while q:
        cur = q.popleft()
        if cur == tuple(g):
            return seen[cur]
        r, c = cur
        for nb in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nb[0] < n and 0 <= nb[1] < n and nb not in walls and nb not in seen:
                seen[nb] = seen[cur] + 1
                q.append(nb)
    return None


def grid_build(rng, diff):
    n = {"easy": 5, "medium": 7, "hard": 10}[diff]
    dens = {"easy": 0.15, "medium": 0.25, "hard": 0.3}[diff]
    cells = [(r, c) for r in range(n) for c in range(n)]
    s, g = pick(rng, cells, 2)
    walls = [list(x) for x in cells if x not in (s, g) and rng.random() < dens]
    knobs = {"n": n, "wall_density": dens, "gridlines": diff != "hard"}
    return {"n": n, "walls": walls, "start": list(s), "goal": list(g)}, knobs


def grid_render(spec, knobs, path):
    n = spec["n"]
    cell = 400 // n
    S = cell * n + 40
    img = Image.new("RGB", (S, S), (255, 255, 255))
    d = ImageDraw.Draw(img)
    o = 20
    walls = {tuple(w) for w in spec["walls"]}
    centres = {}
    for r in range(n):
        for c in range(n):
            box = [o + c * cell, o + r * cell, o + (c + 1) * cell - 1, o + (r + 1) * cell - 1]
            fill = (40, 40, 40) if (r, c) in walls else (255, 255, 255)
            if [r, c] == spec["start"]:
                fill = NAMED_COLORS["green"]
            if [r, c] == spec["goal"]:
                fill = NAMED_COLORS["red"]
            d.rectangle(box, fill=fill, outline=(160, 160, 160) if knobs["gridlines"] else None)
            centres[(r, c)] = (o + c * cell + cell // 2, o + r * cell + cell // 2)
    d.rectangle([o, o, o + n * cell, o + n * cell], outline=(0, 0, 0), width=2)
    img.save(path)
    return {"w": S, "h": S, "cell": cell, "origin": o}


def grid_probe(spec, info, img):
    fails = []
    n, cell, o = spec["n"], info["cell"], info["origin"]
    walls = {tuple(w) for w in spec["walls"]}
    for r in range(n):
        for c in range(n):
            px = img[o + r * cell + cell // 2, o + c * cell + cell // 2].astype(int)
            want = (40, 40, 40) if (r, c) in walls else (255, 255, 255)
            if [r, c] == spec["start"]:
                want = NAMED_COLORS["green"]
            if [r, c] == spec["goal"]:
                want = NAMED_COLORS["red"]
            if np.abs(px - np.array(want)).max() > 10:
                fails.append(f"cell {r},{c} colour {tuple(px)}")
    return fails


def grid_ask(spec, info, rng, diff):
    walls = {tuple(w) for w in spec["walls"]}
    L = _bfs(spec["n"], walls, spec["start"], spec["goal"])
    qt = pick(rng, ["path_len", "path_len", "reachable", "walls"])
    rule = ("Moves go up, down, left or right one cell at a time; dark cells are walls and cannot be entered.")
    if qt == "walls":
        if len(walls) > 30:
            raise Reject("too many walls to count fairly")
        return Question(qt, {}, "How many dark wall cells are in the grid?", len(walls), "numeric",
                        format_hint="a whole number")
    if qt == "reachable":
        return Question(qt, {}, f"Can you get from the green cell to the red cell? {rule}",
                        "yes" if L is not None else "no", "yesno", format_hint="yes or no", choices=["yes", "no"])
    if L is None:
        raise Reject("goal unreachable for a path-length question")
    return Question(qt, {}, f"What is the smallest number of moves from the green cell to the red cell? {rule}",
                    L, "numeric", format_hint="a whole number")


register(Family("shapes", shapes_build, shapes_render, shapes_ask, shapes_probe))
register(Family("clock", clock_build, clock_render, clock_ask, clock_probe))
register(Family("grid_path", grid_build, grid_render, grid_ask, grid_probe))
