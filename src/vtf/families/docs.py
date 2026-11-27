"""Document-like images: printed data tables and thermal shop receipts.

Both are laid out flat, printed as an ink mask onto seeded paper texture, then placed on a
desk surface with a small rotation and perspective, uneven light and sensor noise. The
render returns the homography from sheet to photo and the sheet box of every answer-bearing
token, so probes can check legibility in the final photo, not in the clean layout.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from .. import realism as R
from ..core import FRUITS, WORDS, Family, Question, Reject, pick, register
from .text import font


def _photo_knobs(rng, diff, rot):
    """Seeded camera and lighting knobs shared by tables and receipts."""
    lvl = {"easy": 0, "medium": 1, "hard": 2}[diff]
    ang = float(rng.uniform(0, 2 * np.pi))
    return {
        "noise_seed": int(rng.integers(0, 2 ** 31)),
        "skew_deg": round(float(rng.uniform(-rot[lvl], rot[lvl])), 2),
        "perspective": [0.0, 0.012, 0.028][lvl],
        "light": [0.10, 0.20, 0.32][lvl],
        "light_dir": [round(float(np.cos(ang)), 3), round(float(np.sin(ang)), 3)],
        "vignette": [0.10, 0.20, 0.30][lvl],
        "sensor": [1.5, 2.5, 3.5][lvl],
        "surface": pick(rng, ["wood", "desk", "linen", "slate"]),
    }


def _photograph(sheet_rgb, sheet_alpha, knobs, rng):
    """Put a flat sheet on a surface and photograph it. Returns (photo, homography)."""
    h, w = sheet_rgb.shape[:2]
    m = int(0.10 * max(w, h)) + 50
    W, H = w + 2 * m, h + 2 * m
    bg = R.surface(rng, W, H, knobs["surface"])
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    dst = R.quad(w, h, W / 2, H / 2, knobs["skew_deg"], knobs["perspective"], rng)
    Hm = R.homography(src, dst)
    out = R.place(sheet_rgb, sheet_alpha, bg, Hm)
    gx, gy = knobs["light_dir"]
    out = R.lighting(out, gx, gy, knobs["light"], knobs["vignette"], warm=0.02)
    out = R.blur(out, knobs.get("blur", 0.0))
    out = R.sensor(out, rng, knobs["sensor"])
    return out, Hm


def _token_boxes(text, x0, y0, y1, cw):
    """Sheet boxes of each run of non-space characters in a monospaced line."""
    out, i = [], 0
    while i < len(text):
        if text[i] == " ":
            i += 1
            continue
        j = i
        while j < len(text) and text[j] != " ":
            j += 1
        out.append([x0 + i * cw, y0, x0 + j * cw, y1])
        i = j
    return out


# ---------------------------------------------------------------- table

THEMES = {
    "sports": {"label": "Team", "noun": "team", "plural": "teams",
               "cols": ["Q1", "Q2", "Q3", "Q4", "Wins", "Goals", "Points", "Games"],
               "titles": ["Season standings", "League table", "Club results"]},
    "sales": {"label": "Branch", "noun": "branch", "plural": "branches",
              "cols": ["Q1", "Q2", "Q3", "Q4", "Orders", "Units", "Returns", "Visits"],
              "titles": ["Branch sales by quarter", "Regional sales summary", "Store performance"]},
}


def table_build(rng, diff):
    nrows = {"easy": 4, "medium": int(rng.integers(6, 9)), "hard": int(rng.integers(10, 15))}[diff]
    ncols = {"easy": 3, "medium": 4, "hard": 5}[diff]
    theme = pick(rng, sorted(THEMES))
    th = THEMES[theme]
    cols = [th["label"]] + pick(rng, th["cols"], ncols)
    names = pick(rng, WORDS, nrows)
    hi = {"easy": 100, "medium": 1000, "hard": 1000 if theme == "sports" else 20000}[diff]
    rows = [[nm] + [int(v) for v in rng.integers(1, hi, size=ncols)] for nm in names]
    knobs = {"rows": nrows, "cols": ncols + 1, "font_px": {"easy": 20, "medium": 15, "hard": 12}[diff],
             "zebra": diff == "medium", "rules": diff != "hard", "dense": diff == "hard",
             "face": pick(rng, ["sans", "serif", "narrow", "dejavu"]), "thousands": diff == "hard"}
    knobs.update(_photo_knobs(rng, diff, (0.8, 1.8, 3.0)))
    if diff == "hard":
        knobs["blur"] = 0.5
    spec = {"columns": cols, "rows": rows, "theme": theme, "noun": th["noun"], "plural": th["plural"],
            "title": pick(rng, th["titles"]), "note": pick(rng, ["Figures are provisional.", "Final figures.",
                                                                   "Compiled at period end."])}
    return spec, knobs


def _num(v, thousands):
    return f"{v:,}" if thousands else str(v)


def table_render(spec, knobs, path):
    rng = np.random.default_rng(knobs["noise_seed"])
    face = knobs.get("face", "dejavu")
    fs = knobs["font_px"]
    f, fb = font(fs, face=face), font(fs, bold=True, face=face)
    ft, fn = font(fs + 8, bold=True, face="serif"), font(max(10, fs - 3), face=face)
    pad = 6 if knobs["dense"] else 10
    cols, rows = spec["columns"], spec["rows"]
    th = knobs.get("thousands", False)
    cells = [cols] + [[r[0]] + [_num(v, th) for v in r[1:]] for r in rows]
    widths = [int(max((fb if i == 0 else f).getbbox(str(c[j]))[2] for i, c in enumerate(cells))) + 2 * pad
              for j in range(len(cols))]
    rh = int(fs * 1.5) + pad
    mx, top = 36, 36 + int(fs * 2.6)
    W = max(sum(widths) + 2 * mx, int(ft.getlength(spec.get("title", ""))) + 2 * mx)
    H = top + rh * len(cells) + int(fs * 2.4) + 30
    sheet = Image.fromarray(R.paper(rng, W, H, base=(247, 246, 241), blotch=5, grain=3, fibers=12))
    shade = ImageDraw.Draw(sheet, "RGBA")
    ink = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(ink)
    if spec.get("title"):
        d.text((mx, 30), spec["title"], font=ft, fill=255, anchor="lt")
    boxes, y = [], top
    x_end = mx + sum(widths)
    for i, row in enumerate(cells):
        if i == 0:
            shade.rectangle([mx, y, x_end, y + rh], fill=(40, 60, 90, 38))
        elif knobs["zebra"] and i % 2 == 0:
            shade.rectangle([mx, y, x_end, y + rh], fill=(40, 70, 120, 18))
        x, rb = mx, []
        for j, txt in enumerate(row):
            ftx = fb if i == 0 else f
            if j == 0:
                d.text((x + pad, y + rh / 2), txt, font=ftx, fill=255, anchor="lm")
            else:
                d.text((x + widths[j] - pad, y + rh / 2), txt, font=ftx, fill=255, anchor="rm")
            rb.append([x, y, x + widths[j], y + rh])
            x += widths[j]
        boxes.append(rb)
        if knobs["rules"] or i == 0:
            d.line([mx, y + rh, x_end, y + rh], fill=110 if i else 230, width=1 if i else 2)
        y += rh
    if knobs["rules"]:
        d.rectangle([mx, top, x_end, y], outline=200)
    if spec.get("note"):
        d.text((mx, y + 10), spec["note"], font=fn, fill=200, anchor="lt")
    clean = np.asarray(ink, np.float32) / 255.0
    printed = R.ink(np.asarray(sheet), clean, (22, 24, 30), 0.93)
    alpha = np.full((H, W), 255, np.uint8)
    photo, Hm = _photograph(printed, alpha, knobs, rng)
    Image.fromarray(photo).save(path)
    text_w = [[int((fb if i == 0 else f).getbbox(t)[2]) for t in row] for i, row in enumerate(cells)]
    rows_y = [[r[0][0], r[-1][2], (r[0][1] + r[0][3]) / 2] for r in boxes]
    return {"w": photo.shape[1], "h": photo.shape[0], "sheet": [W, H], "H": Hm.tolist(), "boxes": boxes,
            "text_w": text_w, "pad": pad, "rows": rows_y, "lh": rh}


def _legible(img, Hm, box, min_contrast, inset=0):
    """Contrast of one sheet box in the photo: bright paper vs dark ink inside its warped outline.
    inset keeps cell borders and rules out of the measurement, so only the text counts."""
    x0, y0, x1, y1 = box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset
    poly = R.apply_h(Hm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    Hh, Ww = img.shape[:2]
    if any(not (2 <= px < Ww - 2 and 2 <= py < Hh - 2) for px, py in poly):
        return "outside the photo"
    m = R.polygon_mask(img.shape, poly)
    g = img[m].astype(np.float32).mean(-1)
    if g.size < 10:
        return "too small"
    c = float(np.percentile(g, 95) - np.percentile(g, 3))
    if c < min_contrast:
        return f"contrast {c:.0f}"
    return None


def _row_drift(Hm, rows, lh):
    """A printed row may tilt in the photo, but not so far that its ends look like different rows."""
    out = []
    for k, (x0, x1, yc) in enumerate(rows):
        (_, ya), (_, yb) = R.apply_h(Hm, [(x0, yc), (x1, yc)])
        if abs(ya - yb) > 0.75 * lh:
            out.append(f"row {k} drifts {abs(ya - yb):.0f}px across")
    return out


def table_probe(spec, info, img):
    fails = []
    Hm = np.array(info["H"])
    for i, row in enumerate(info["boxes"]):
        for j, box in enumerate(row):
            if info["text_w"][i][j] > (box[2] - box[0]) - info["pad"]:
                fails.append(f"cell {i},{j} text wider than cell")
            bad = _legible(img, Hm, box, 60, inset=3)
            if bad:
                fails.append(f"cell {i},{j} {bad}")
    fails += _row_drift(Hm, info["rows"], info["lh"])
    W, H = info["sheet"]
    for px, py in R.apply_h(Hm, [(0, 0), (W, 0), (W, H), (0, H)]):
        if not (4 <= px < info["w"] - 4 and 4 <= py < info["h"] - 4):
            fails.append("sheet touches the image edge")
            break
    return fails


def table_ask(spec, info, rng, diff):
    cols, rows = spec["columns"], spec["rows"]
    noun, plural = spec.get("noun", "team"), spec.get("plural", "teams")
    c = pick(rng, cols[1:])
    ci = cols.index(c)
    qt = pick(rng, ["lookup", "lookup", "col_sum", "row_max", "count_gt"])
    if qt == "lookup":
        r = pick(rng, rows)
        return Question(qt, {"row": r[0], "col": c}, f"In the table, what is the {c} value for {r[0]}?", r[ci],
                        "numeric", format_hint="a number")
    if qt == "col_sum":
        if len(rows) > 8:
            raise Reject("column too long to sum fairly")
        return Question(qt, {"col": c}, f"What is the sum of the {c} column?", sum(r[ci] for r in rows), "numeric",
                        format_hint="a number")
    if qt == "row_max":
        v = sorted((r[ci] for r in rows), reverse=True)
        if v[0] == v[1]:
            raise Reject("tied maximum")
        best = max(rows, key=lambda r: r[ci])
        return Question(qt, {"col": c}, f"Which {noun} has the highest {c}?", best[0], "exact",
                        format_hint=f"a {noun} name", choices=[r[0] for r in rows])
    vals = [r[ci] for r in rows]
    t = int(np.median(vals)) + int(rng.integers(-5, 6))
    if t in vals:
        raise Reject("threshold equals a value")
    return Question(qt, {"col": c, "threshold": t}, f"How many {plural} have a {c} greater than {t}?",
                    sum(v > t for v in vals), "numeric", format_hint="a whole number")


# ---------------------------------------------------------------- receipt

GROCERIES = FRUITS + ["Bread", "Milk", "Eggs", "Rice", "Coffee", "Butter", "Cheese", "Pasta", "Tea", "Honey"]
STORE_KINDS = ["Market", "Grocers", "Fresh Mart", "Food Hall", "Corner Store", "Supermarket"]
STREETS = ["Road", "Street", "Lane", "Avenue", "Parade", "Way"]
CITIES = ["Northfield", "Lakeside", "Easton", "Millbrook", "Westgate", "Hillcrest", "Riverton", "Oakdale"]
CASHIERS = ["MAYA", "OMAR", "LENA", "RAVI", "JUNE", "TOMAS", "ADA", "KENJI"]
# symbol, position, decimal mark
CURRENCIES = [["$", "pre", "."], ["£", "pre", "."], ["€", "post", ","], ["CHF", "pre", "."], ["₹", "pre", "."]]


def receipt_build(rng, diff):
    n = {"easy": 3, "medium": int(rng.integers(5, 8)), "hard": int(rng.integers(8, 12))}[diff]
    items = [{"name": nm, "qty": int(rng.integers(1, 5)), "price_cents": int(rng.integers(5, 400)) * 5}
             for nm in pick(rng, GROCERIES, n)]
    disc = int(rng.integers(1, 20)) * 25 if diff != "easy" else 0
    tax = int(pick(rng, [0, 5, 8, 12, 18]))
    cur = pick(rng, CURRENCIES)
    header = {
        "street": f"{int(rng.integers(2, 480))} {pick(rng, WORDS)} {pick(rng, STREETS)}",
        "city": pick(rng, CITIES),
        "phone": "TEL " + "".join(str(int(v)) for v in rng.integers(0, 10, 3)) + "-"
                 + "".join(str(int(v)) for v in rng.integers(0, 10, 4)),
        "date": f"{int(rng.integers(1, 29)):02d}/{int(rng.integers(1, 13)):02d}/2026",
        "time": f"{int(rng.integers(7, 23)):02d}:{int(rng.integers(0, 60)):02d}",
        "till": int(rng.integers(1, 9)), "cashier": pick(rng, CASHIERS),
        "receipt_no": int(rng.integers(1000, 999999)),
        "barcode": "".join(str(int(v)) for v in rng.integers(0, 10, 12)),
    }
    sub = sum(it["qty"] * it["price_cents"] for it in items) - disc
    total = sub + (sub * tax + 50) // 100
    if diff != "easy" and rng.random() < 0.6:
        step = int(pick(rng, [500, 1000, 2000]))
        tender = {"kind": "cash", "paid_cents": (total // step + 1) * step}
    else:
        tender = {"kind": "card", "last4": "".join(str(int(v)) for v in rng.integers(0, 10, 4))}
    face = pick(rng, ["courier", "mono"])
    if cur[0] == "₹":
        face = "mono"  # Courier Prime has no rupee sign
    knobs = {"items": n, "discount": disc > 0, "blur": 0.8 if diff == "hard" else (0.3 if diff == "medium" else 0.0),
             "ink": "faded" if diff == "hard" else "dark", "font_px": {"easy": 18, "medium": 16, "hard": 15}[diff],
             "face": face, "layout": "twoline" if diff == "hard" and rng.random() < 0.6 else "inline",
             "thermal_fade": [0.15, 0.28, 0.38][("easy", "medium", "hard").index(diff)],
             "dropout": [0.0, 0.015, 0.035][("easy", "medium", "hard").index(diff)]}
    knobs.update(_photo_knobs(rng, diff, (1.0, 2.0, 3.0)))
    spec = {"store": pick(rng, WORDS) + " " + pick(rng, STORE_KINDS), "items": items, "discount_cents": disc,
            "tax_rate_pct": tax, "currency": cur, "header": header, "tender": tender}
    return spec, knobs


def _money(c, cur=None, sym=False):
    dec = cur[2] if cur else "."
    s = f"{c // 100}{dec}{c % 100:02d}"
    if sym and cur:
        s = f"{cur[0]}{s}" if cur[1] == "pre" else f"{s} {cur[0]}"
    return s


def _totals(spec):
    sub = sum(it["qty"] * it["price_cents"] for it in spec["items"])
    base = sub - spec["discount_cents"]
    tax = (base * spec["tax_rate_pct"] + 50) // 100
    return sub, base, tax, base + tax


def _receipt_lines(spec, knobs, width):
    """(kind, text, key) lines; key lines carry answer-bearing tokens checked by the probe."""
    cur = spec.get("currency")
    hd = spec.get("header")
    lines = [("title", spec["store"].upper(), False)]
    if hd:
        lines += [("center", hd["street"].upper(), False), ("center", hd["city"].upper(), False),
                  ("center", hd["phone"], False), ("blank", "", False),
                  ("text", f"DATE {hd['date']}".ljust(width - 10) + f"TIME {hd['time']}"[-10:].rjust(10), False),
                  ("text", f"TILL {hd['till']:02d}  CASHIER {hd['cashier']}".ljust(width - 8)
                   + f"#{hd['receipt_no']:06d}".rjust(8), False)]
    lines.append(("rule", "-" * width, False))

    def row(left, amount, kind="text"):
        return (kind, left.ljust(width - 10)[: width - 10] + amount.rjust(10), True)

    for it in spec["items"]:
        amt = _money(it["qty"] * it["price_cents"], cur)
        if knobs.get("layout") == "twoline":
            lines.append(("text", it["name"].upper(), True))
            lines.append(row(f"  {it['qty']} @ {_money(it['price_cents'], cur)}", amt))
        else:
            lines.append(row(f"{it['qty']} x {it['name']} @ {_money(it['price_cents'], cur)}", amt))
    sub, base, tax, total = _totals(spec)
    lines.append(("rule", "-" * width, False))
    lines.append(row("SUBTOTAL", _money(sub, cur)))
    if spec["discount_cents"]:
        lines.append(row("DISCOUNT", "-" + _money(spec["discount_cents"], cur)))
    lines.append(row(f"TAX {spec['tax_rate_pct']}%", _money(tax, cur)))
    lines.append(row("TOTAL", _money(total, cur, sym=True), "bold"))
    td = spec.get("tender")
    if td and td["kind"] == "cash":
        lines.append(("text", "CASH".ljust(width - 10) + _money(td["paid_cents"], cur).rjust(10), False))
        lines.append(("text", "CHANGE".ljust(width - 10) + _money(td["paid_cents"] - total, cur).rjust(10), False))
    elif td:
        lines.append(("text", f"CARD **** {td['last4']}".ljust(width - 10) + _money(total, cur).rjust(10), False))
    if hd:
        lines += [("blank", "", False), ("center", "THANK YOU FOR SHOPPING", False), ("barcode", hd["barcode"], False)]
    return lines


def _serrated(W, H, tooth):
    a = Image.new("L", (W, H), 0)
    pts = [(0, tooth)]
    for x in range(0, W + tooth, tooth):
        pts.append((min(x, W), 0 if (x // tooth) % 2 else tooth))
    pts += [(W, H - tooth)]
    for x in range(W, -tooth, -tooth):
        pts.append((max(x, 0), H if (x // tooth) % 2 else H - tooth))
    ImageDraw.Draw(a).polygon(pts, fill=255)
    return np.asarray(a)


def receipt_render(spec, knobs, path):
    rng = np.random.default_rng(knobs.get("noise_seed", 0))
    face = knobs.get("face", "mono")
    f = font(knobs["font_px"], face=face)
    fb = font(knobs["font_px"], bold=True, face=face)
    ftitle = font(knobs["font_px"] + 6, bold=True, face=face)
    width = 36
    cw = f.getlength("0")
    lh = int(knobs["font_px"] * 1.45)
    lines = _receipt_lines(spec, knobs, width)
    mx = 26
    W = int(cw * width) + 2 * mx
    hgt = sum(lh * (3 if k == "barcode" else 1) for k, _, _ in lines)
    H = hgt + 2 * 36
    ink = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(ink)
    y = 36
    bands, tokens, rows = [], [], []
    for kind, txt, key in lines:
        if kind == "title":
            d.text((W / 2, y + lh / 2), txt, font=ftitle, fill=255, anchor="mm")
            bands.append([y, y + lh, int(W / 2 + ftitle.getlength(txt) / 2)])
        elif kind == "center":
            d.text((W / 2, y + lh / 2), txt, font=f, fill=255, anchor="mm")
        elif kind == "rule":
            d.text((mx, y + lh / 2), txt, font=f, fill=255, anchor="lm")
        elif kind == "barcode":
            code, bits = R.ean13(txt)
            mod = max(1, int((W - 2 * mx) / 110))
            bx = (W - 95 * mod) // 2
            for k, b in enumerate(bits):
                if b == "1":
                    d.rectangle([bx + k * mod, y, bx + (k + 1) * mod - 1, y + int(lh * 2.1)], fill=255)
            d.text((W / 2, y + int(lh * 2.6)), code, font=f, fill=255, anchor="mm")
            y += 2 * lh
        elif kind in ("text", "bold"):
            ft = fb if kind == "bold" else f
            d.text((mx, y + lh / 2), txt, font=ft, fill=255, anchor="lm")
            bands.append([y, y + lh, int(mx + ft.getlength(txt.rstrip()))])
            if key:
                tokens += _token_boxes(txt, mx, y + 2, y + lh - 2, cw)
                rows.append([mx, mx + cw * len(txt.rstrip()), y + lh / 2])
        y += lh
    clean = np.asarray(ink, np.float32) / 255.0
    worn = R.thermal(clean, rng, knobs.get("thermal_fade", 0.0), knobs.get("dropout", 0.0))
    base = (250, 249, 245) if knobs["ink"] == "dark" else (246, 244, 238)
    color, strength = ((26, 24, 32), 0.95) if knobs["ink"] == "dark" else ((78, 76, 92), 0.82)
    paper = R.paper(rng, W, H, base=base, blotch=4, grain=3)
    printed = R.ink(paper, worn, color, strength)
    alpha = _serrated(W, H, 6)
    photo, Hm = _photograph(printed, alpha, knobs, rng)
    Image.fromarray(photo).save(path)
    return {"w": photo.shape[1], "h": photo.shape[0], "paper_w": W, "sheet": [W, H], "H": Hm.tolist(),
            "bands": bands, "tokens": tokens, "rows": rows, "lh": lh, "_clean": clean, "_worn": worn}


def receipt_probe(spec, info, img):
    fails = []
    clean, worn = info.pop("_clean"), info.pop("_worn")
    Hm = np.array(info["H"])
    for k, (y0, y1, right) in enumerate(info["bands"]):
        if right > info["paper_w"] - 16:
            fails.append(f"line {k} runs off the paper")
    for k, (x0, y0, x1, y1) in enumerate(info["tokens"]):
        a, b = int(x0), int(np.ceil(x1))
        full = clean[int(y0):int(y1), a:b].sum()
        if full < 4:
            fails.append(f"token {k} has no ink")
            continue
        kept = worn[int(y0):int(y1), a:b].sum() / full
        if kept < 0.6:
            fails.append(f"token {k} keeps {kept:.0%} of its ink")
        bad = _legible(img, Hm, [x0, y0, x1, y1], 40)
        if bad:
            fails.append(f"token {k} {bad}")
    fails += _row_drift(Hm, info["rows"], info["lh"])
    W, H = info["sheet"]
    for px, py in R.apply_h(Hm, [(0, 0), (W, 0), (W, H), (0, H)]):
        if not (4 <= px < info["w"] - 4 and 4 <= py < info["h"] - 4):
            fails.append("paper touches the image edge")
            break
    return fails


def receipt_ask(spec, info, rng, diff):
    items = spec["items"]
    qt = pick(rng, ["total", "units", "line_total", "priciest"])
    if qt == "total":
        return Question(qt, {}, "What is the final total on this receipt?", _totals(spec)[3] / 100, "numeric",
                        tolerance=0.005, format_hint="a number with two decimals, no currency sign")
    if qt == "units":
        return Question(qt, {}, "How many units were bought in total (add up the quantities)?",
                        sum(it["qty"] for it in items), "numeric", format_hint="a whole number")
    if qt == "line_total":
        it = pick(rng, items)
        return Question(qt, {"name": it["name"]}, f"How much was charged in total for {it['name']}?",
                        it["qty"] * it["price_cents"] / 100, "numeric", tolerance=0.005,
                        format_hint="a number with two decimals, no currency sign")
    lt = sorted((it["qty"] * it["price_cents"] for it in items), reverse=True)
    if lt[0] - lt[1] < 100:
        raise Reject("top two line totals within 1.00")
    best = max(items, key=lambda it: it["qty"] * it["price_cents"])
    return Question(qt, {}, "Which item has the largest line total?", best["name"], "exact",
                    format_hint="the item name", choices=[it["name"] for it in items])


register(Family("table", table_build, table_render, table_ask, table_probe))
register(Family("receipt", receipt_build, receipt_render, receipt_ask, receipt_probe))
