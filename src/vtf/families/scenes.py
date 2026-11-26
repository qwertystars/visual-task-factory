"""Shape scenes, analog watches and grid mazes drawn with Pillow."""

from __future__ import annotations

import math
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .. import realism as R
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

DIALS = {
    # dial colour, print colour, hand fill, hand outline, case metal
    "classic": {"dial": (244, 239, 226), "print": (28, 28, 34), "hand": (24, 34, 64), "edge": None,
                "metal": (196, 198, 202), "face": "serif"},
    "dress": {"dial": (214, 216, 220), "print": (34, 34, 38), "hand": (30, 30, 34), "edge": None,
              "metal": (214, 186, 132), "face": "serif"},
    "sport": {"dial": (30, 34, 42), "print": (232, 232, 222), "hand": (238, 236, 220), "edge": (12, 12, 14),
              "metal": (150, 154, 160), "face": "sans"},
}
DIAL_WORDS = ["AUTOMATIC", "QUARTZ", "CHRONOMETER", "SWISS MOVEMENT", "SELF-WINDING"]


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
    knobs.update({
        "dial": {"easy": pick(rng, ["classic", "dress"]), "medium": pick(rng, ["classic", "dress", "sport"]),
                 "hard": pick(rng, ["classic", "dress", "sport"])}[diff],
        "subdial": bool(diff != "easy" and rng.random() < 0.5),
        "date_window": bool(diff == "hard" and rng.random() < 0.5),
        "dial_text": pick(rng, DIAL_WORDS),
        "noise_seed": int(rng.integers(0, 2 ** 31)),
        "light_deg": int(rng.integers(200, 340)),
        "surface": pick(rng, ["wood", "desk", "linen", "slate"]),
    })
    return {"hour": h, "minute": m, "second": sec, "date": int(rng.integers(1, 32))}, knobs


def _angles(spec):
    h, m, s = spec["hour"], spec["minute"], spec["second"]
    return (30 * (h % 12) + 0.5 * m) % 360, 6 * m, 6 * s


ROMAN = ["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"]


def _rot(cx, cy, deg, pts):
    """Hand-frame points (u along the hand, v across) to image points for a hand at deg."""
    r = math.radians(deg)
    su, cu = math.sin(r), -math.cos(r)  # unit vector along the hand (0 deg = 12 o'clock)
    sv, cv = math.cos(r), math.sin(r)   # unit vector across the hand
    return [(cx + u * su + v * sv, cy + u * cu + v * cv) for u, v in pts]


def _hand_poly(style, L, w):
    if style == "sword":
        return [(-0.14 * L, -w / 2), (0.8 * L, -w / 2), (L, 0), (0.8 * L, w / 2), (-0.14 * L, w / 2)]
    return [(-0.16 * L, -w * 0.3), (0.0, -w / 2), (L, 0), (0.0, w / 2), (-0.16 * L, w * 0.3)]  # dauphine


def _shade_ring(arr, cx, cy, r0, r1, metal, light, flip=False):
    """Metal ring lit from one side: brightness follows the outward normal's dot with the light."""
    H, W = arr.shape[:2]
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    dx, dy = x - cx, y - cy
    r = np.sqrt(dx * dx + dy * dy) + 1e-6
    ring = (r >= r0) & (r < r1)
    dot = (dx * light[0] + dy * light[1]) / r
    if flip:
        dot = -dot
    shade = 0.78 + 0.32 * dot
    arr[ring] = np.clip(np.array(metal, np.float32) * shade[ring][:, None], 0, 255)
    return arr


def _watch(spec, knobs, hands: bool):
    """Render the watch photo; returns (rgb array at final size, hand masks at final size)."""
    Z = 2
    S = knobs["size"]
    s2 = S * Z
    rng = np.random.default_rng(knobs.get("noise_seed", 0))
    style = DIALS[knobs.get("dial", "classic")]
    la = math.radians(knobs.get("light_deg", 250))
    light = (math.cos(la), math.sin(la))
    c = s2 / 2
    Rd = s2 * 0.36
    Rc = Rd * 1.17
    bg = R.surface(rng, s2, s2, knobs.get("surface", "desk")).astype(np.float32)
    # strap and drop shadow
    sh = Image.new("L", (s2, s2), 0)
    dsh = ImageDraw.Draw(sh)
    off = 6 * Z
    dsh.ellipse([c - Rc + off, c - Rc + off, c + Rc + off, c + Rc + off], fill=200)
    dsh.rectangle([c - 0.62 * Rd + off, 0, c + 0.62 * Rd + off, s2], fill=150)
    sh = np.asarray(sh.filter(ImageFilter.GaussianBlur(9 * Z)), np.float32) / 255.0
    bg *= (1 - 0.55 * sh)[..., None]
    img = Image.fromarray(np.clip(bg + 0.5, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    strap = (58, 40, 30) if knobs.get("dial") != "sport" else (34, 36, 40)
    d.rectangle([c - 0.62 * Rd, 0, c + 0.62 * Rd, s2], fill=strap)
    for yy in range(0, s2, 7 * Z):  # stitching
        for sx in (-0.55, 0.55):
            d.line([(c + sx * Rd, yy), (c + sx * Rd, yy + 3 * Z)], fill=(150, 130, 100), width=Z)
    # lugs
    for sy in (-1, 1):
        for sx in (-1, 1):
            x0 = c + sx * 0.66 * Rd
            d.polygon([(x0 - 0.1 * Rd, c + sy * 0.8 * Rd), (x0 + 0.1 * Rd, c + sy * 0.8 * Rd),
                       (x0 + 0.08 * Rd, c + sy * 1.32 * Rd), (x0 - 0.08 * Rd, c + sy * 1.32 * Rd)],
                      fill=style["metal"])
    arr = np.asarray(img, np.float32).copy()
    arr = _shade_ring(arr, c, c, Rd * 1.035, Rc, style["metal"], light)
    arr = _shade_ring(arr, c, c, Rd, Rd * 1.035, style["metal"], light, flip=True)
    # dial with a soft falloff to the rim and a light sunray texture
    y, x = np.mgrid[0:s2, 0:s2].astype(np.float32)
    dx, dy = x - c, y - c
    rr = np.sqrt(dx * dx + dy * dy)
    inside = rr < Rd
    t = rr / Rd
    tone = 1 - 0.10 * t * t * t * t + 0.05 * ((dx * light[0] + dy * light[1]) / (rr + 1e-6)) * t
    if knobs.get("dial") == "dress":
        ang_noise = R.value_noise(rng, 1, 720, 360)[0]
        ai = ((np.arctan2(dy, dx) + math.pi) / (2 * math.pi) * 719).astype(int)
        tone = tone + (ang_noise[ai] - 0.5) * 0.06
    else:
        rng.random(1)  # keep the noise stream aligned across dial styles
    dial = np.array(style["dial"], np.float32)[None, None, :] * tone[..., None]
    arr[inside] = np.clip(dial[inside], 0, 255)
    img = Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    ink = style["print"]
    # minute track
    if knobs["minute_ticks"]:
        d.ellipse([c - 0.985 * Rd, c - 0.985 * Rd, c + 0.985 * Rd, c + 0.985 * Rd], outline=ink, width=Z)
        d.ellipse([c - 0.91 * Rd, c - 0.91 * Rd, c + 0.91 * Rd, c + 0.91 * Rd], outline=ink, width=Z)
        for k in range(60):
            if k % 5:
                a = math.radians(k * 6)
                d.line([(c + 0.91 * Rd * math.sin(a), c - 0.91 * Rd * math.cos(a)),
                        (c + 0.985 * Rd * math.sin(a), c - 0.985 * Rd * math.cos(a))], fill=ink, width=Z)
    skip = set()
    if knobs.get("date_window"):
        skip.add(3)
    if knobs.get("subdial"):
        skip.add(6)
    num = knobs["numerals"]
    f = font(int(Rd * (0.2 if num != "roman" else 0.16)), bold=style["face"] == "sans", face=style["face"])
    for k in range(12):
        if k in skip:
            continue
        a = math.radians(k * 30)
        show_num = num in ("all", "roman") or (num == "quarters" and k % 3 == 0)
        if show_num:
            txt = ROMAN[k] if num == "roman" else str(12 if k == 0 else k)
            d.text((c + Rd * 0.74 * math.sin(a), c - Rd * 0.74 * math.cos(a)), txt, fill=ink, font=f, anchor="mm")
        else:
            wdt = (0.045 if k else 0.07) * Rd
            for side in ((-1, 1) if k == 0 else (0,)):
                ux = side * 0.04 * Rd
                pts = [(0.66 * Rd, -wdt / 2 + ux), (0.88 * Rd, -wdt / 2 + ux), (0.88 * Rd, wdt / 2 + ux),
                       (0.66 * Rd, wdt / 2 + ux)]
                d.polygon(_rot(c, c, k * 30, pts), fill=ink)
    d.text((c, c - 0.38 * Rd), knobs.get("dial_text", ""), fill=ink, font=font(int(Rd * 0.07), face="sans"),
           anchor="mm")
    if knobs.get("date_window"):
        bx, by, bw, bh = c + 0.66 * Rd, c, 0.13 * Rd, 0.09 * Rd
        d.rectangle([bx - bw, by - bh, bx + bw, by + bh], fill=(250, 250, 246), outline=ink, width=Z)
        d.text((bx, by), str(spec.get("date", 1)), fill=(20, 20, 20), font=font(int(Rd * 0.12), face="sans"),
               anchor="mm")
    if knobs.get("subdial"):
        sx, sy, sr = c, c + 0.47 * Rd, 0.19 * Rd
        d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], outline=ink, width=Z)
        for k in range(12):
            a = math.radians(k * 30)
            d.line([(sx + 0.78 * sr * math.sin(a), sy - 0.78 * sr * math.cos(a)),
                    (sx + sr * math.sin(a), sy - sr * math.cos(a))], fill=ink, width=Z)
        a = math.radians(6 * spec["second"])
        d.line([(sx, sy), (sx + 0.85 * sr * math.sin(a), sy - 0.85 * sr * math.cos(a))], fill=ink, width=Z)
        d.ellipse([sx - 2 * Z, sy - 2 * Z, sx + 2 * Z, sy + 2 * Z], fill=ink)
    ha, ma, sa = _angles(spec)
    hl, ml = (0.62, 0.72) if knobs["similar_hands"] else (0.5, 0.8)
    hw, mw = (0.07, 0.06) if knobs["similar_hands"] else (0.085, 0.055)
    hstyle = "sword" if knobs.get("dial") == "sport" else "dauphine"
    polys = {"hour": _rot(c, c, ha, _hand_poly(hstyle, hl * Rd, hw * Rd)),
             "minute": _rot(c, c, ma, _hand_poly(hstyle, ml * Rd, mw * Rd))}
    masks = {}
    if hands:
        hm = Image.new("L", (s2, s2), 0)
        dm = ImageDraw.Draw(hm)
        for p in polys.values():
            dm.polygon(p, fill=255)
        sec_line = None
        if knobs["second_hand"]:
            r = math.radians(sa)
            sec_line = [(c - Rd * 0.2 * math.sin(r), c + Rd * 0.2 * math.cos(r)),
                        (c + Rd * 0.9 * math.sin(r), c - Rd * 0.9 * math.cos(r))]
            dm.line(sec_line, fill=255, width=2 * Z)
        shadow = Image.new("L", (s2, s2), 0)
        shadow.paste(hm, (int(-light[0] * 4 * Z), int(-light[1] * 4 * Z)))
        shadow = np.asarray(shadow.filter(ImageFilter.GaussianBlur(3 * Z)), np.float32) / 255.0
        a2 = np.asarray(img, np.float32) * (1 - 0.35 * shadow)[..., None]
        img = Image.fromarray(np.clip(a2 + 0.5, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        for name in ("hour", "minute"):
            d.polygon(polys[name], fill=style["hand"], outline=style["edge"], width=Z if style["edge"] else 0)
            # a raised ridge down the middle catches the light
            ridge = _rot(c, c, (ha if name == "hour" else ma), [(0, 0), ((hl if name == "hour" else ml) * Rd * 0.95, 0)])
            d.line(ridge, fill=tuple(min(255, v + 45) for v in style["hand"]), width=Z)
        if sec_line:
            d.line(sec_line, fill=(200, 30, 30), width=2 * Z)
            r = math.radians(sa)
            px, py = c - Rd * 0.14 * math.sin(r), c + Rd * 0.14 * math.cos(r)
            d.ellipse([px - 4 * Z, py - 4 * Z, px + 4 * Z, py + 4 * Z], fill=(200, 30, 30))
        d.ellipse([c - 6 * Z, c - 6 * Z, c + 6 * Z, c + 6 * Z], fill=style["hand"], outline=style["edge"] or style["hand"])
        for name, p in polys.items():
            m = Image.new("L", (s2, s2), 0)
            ImageDraw.Draw(m).polygon(p, fill=255)
            masks[name] = np.asarray(m.resize((S, S), Image.BOX)) > 127
        if sec_line:
            m = Image.new("L", (s2, s2), 0)
            ImageDraw.Draw(m).line(sec_line, fill=255, width=2 * Z)
            masks["second"] = np.asarray(m.resize((S, S), Image.BOX)) > 60
    # crystal glare
    gl = Image.new("L", (s2, s2), 0)
    ImageDraw.Draw(gl).ellipse([c - 0.85 * Rd, c - 0.95 * Rd, c + 0.15 * Rd, c - 0.25 * Rd], fill=255)
    gl = np.asarray(gl.filter(ImageFilter.GaussianBlur(14 * Z)), np.float32) / 255.0 * inside
    a3 = np.asarray(img, np.float32)
    a3 = a3 + (255 - a3) * (0.10 * gl)[..., None]
    out = Image.fromarray(np.clip(a3 + 0.5, 0, 255).astype(np.uint8)).resize((S, S), Image.LANCZOS)
    out = R.sensor(np.asarray(out), rng, 1.5)
    return out, masks, {"c": c / Z, "R": Rd / Z, "hl": hl, "ml": ml}


def clock_render(spec, knobs, path):
    photo, masks, geo = _watch(spec, knobs, hands=True)
    bare, _, _ = _watch(spec, knobs, hands=False)
    Image.fromarray(photo).save(path)
    ha, ma, _ = _angles(spec)
    S = knobs["size"]
    return {"w": S, "h": S, "c": geo["c"], "R": geo["R"],
            "hands": {"hour": [ha, geo["hl"]], "minute": [ma, geo["ml"]]},
            "second_hand": knobs["second_hand"], "_bare": bare, "_masks": masks}


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
    return Question("time", {}, "What time does the watch show? Ignore the seconds (a red seconds hand or a "
                    "small seconds dial) and the date.", f"{h}:{m:02d}", "time",
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
