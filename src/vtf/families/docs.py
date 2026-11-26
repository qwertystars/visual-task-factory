"""Document-like images: data tables and shop receipts."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from ..core import FRUITS, WORDS, Family, Question, Reject, pick, register
from .text import font

# ---------------------------------------------------------------- table


def table_build(rng, diff):
    nrows = {"easy": 4, "medium": int(rng.integers(6, 9)), "hard": int(rng.integers(10, 15))}[diff]
    ncols = {"easy": 3, "medium": 4, "hard": 5}[diff]
    cols = ["Team"] + pick(rng, ["Q1", "Q2", "Q3", "Q4", "Wins", "Goals", "Points", "Games"], ncols)
    names = pick(rng, WORDS, nrows)
    hi = 100 if diff == "easy" else 1000
    rows = [[nm] + [int(v) for v in rng.integers(1, hi, size=ncols)] for nm in names]
    knobs = {"rows": nrows, "cols": ncols + 1, "font_px": {"easy": 20, "medium": 15, "hard": 12}[diff],
             "zebra": diff == "medium", "rules": diff != "hard", "dense": diff == "hard"}
    return {"columns": cols, "rows": rows}, knobs


def table_render(spec, knobs, path):
    f, fb = font(knobs["font_px"]), font(knobs["font_px"], bold=True)
    pad = 6 if knobs["dense"] else 10
    cols, rows = spec["columns"], spec["rows"]
    cells = [cols] + [[str(v) for v in r] for r in rows]
    widths = [max(f.getbbox(str(c[j]))[2] if i else fb.getbbox(str(c[j]))[2] for i, c in enumerate(cells)) + 2 * pad
              for j in range(len(cols))]
    rh = int(knobs["font_px"] * 1.5) + pad
    W, H = sum(widths) + 40, rh * len(cells) + 40
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    boxes = []
    y = 20
    for i, row in enumerate(cells):
        x = 20
        if knobs["zebra"] and i % 2 == 0 and i:
            d.rectangle([20, y, W - 20, y + rh], fill=(235, 240, 248))
        if i == 0:
            d.rectangle([20, y, W - 20, y + rh], fill=(220, 225, 235))
        rb = []
        for j, txt in enumerate(row):
            ft = fb if i == 0 else f
            if j == 0:
                d.text((x + pad, y + rh / 2), txt, font=ft, fill=(0, 0, 0), anchor="lm")
            else:
                d.text((x + widths[j] - pad, y + rh / 2), txt, font=ft, fill=(0, 0, 0), anchor="rm")
            rb.append([x, y, x + widths[j], y + rh])
            x += widths[j]
        boxes.append(rb)
        if knobs["rules"]:
            d.line([20, y + rh, W - 20, y + rh], fill=(150, 150, 150))
        y += rh
    if knobs["rules"]:
        d.rectangle([20, 20, W - 20, y], outline=(80, 80, 80))
    img.save(path)
    text_w = [[(fb if i == 0 else f).getbbox(t)[2] for t in row] for i, row in enumerate(cells)]
    return {"w": W, "h": H, "boxes": boxes, "text_w": text_w, "pad": pad}


def table_probe(spec, info, img):
    fails = []
    gray = img.astype(int).sum(-1) / 3
    for i, row in enumerate(info["boxes"]):
        for j, (x0, y0, x1, y1) in enumerate(row):
            if info["text_w"][i][j] > (x1 - x0) - info["pad"]:
                fails.append(f"cell {i},{j} text wider than cell")
            ink = (gray[y0 + 2:y1 - 2, x0 + 1:x1 - 1] < 110).sum()
            if ink < 6:
                fails.append(f"cell {i},{j} has no ink")
    return fails


def table_ask(spec, info, rng, diff):
    cols, rows = spec["columns"], spec["rows"]
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
        return Question(qt, {"col": c}, f"Which team has the highest {c}?", best[0], "exact", format_hint="a team name",
                        choices=[r[0] for r in rows])
    vals = [r[ci] for r in rows]
    t = int(np.median(vals)) + int(rng.integers(-5, 6))
    if t in vals:
        raise Reject("threshold equals a value")
    return Question(qt, {"col": c, "threshold": t}, f"How many teams have a {c} greater than {t}?",
                    sum(v > t for v in vals), "numeric", format_hint="a whole number")


# ---------------------------------------------------------------- receipt

GROCERIES = FRUITS + ["Bread", "Milk", "Eggs", "Rice", "Coffee", "Butter", "Cheese", "Pasta", "Tea", "Honey"]


def receipt_build(rng, diff):
    n = {"easy": 3, "medium": int(rng.integers(5, 8)), "hard": int(rng.integers(8, 12))}[diff]
    items = [{"name": nm, "qty": int(rng.integers(1, 5)), "price_cents": int(rng.integers(5, 400)) * 5}
             for nm in pick(rng, GROCERIES, n)]
    disc = int(rng.integers(1, 20)) * 25 if diff != "easy" else 0
    tax = int(pick(rng, [0, 5, 8, 12, 18]))
    knobs = {"items": n, "discount": disc > 0, "skew_deg": float(rng.uniform(-4, 4)) if diff == "hard" else 0.0,
             "blur": 0.8 if diff == "hard" else 0.0, "ink": "faded" if diff == "hard" else "dark",
             "font_px": {"easy": 18, "medium": 16, "hard": 14}[diff]}
    spec = {"store": pick(rng, WORDS) + " Market", "items": items, "discount_cents": disc, "tax_rate_pct": tax}
    return spec, knobs


def _money(c):
    return f"{c // 100}.{c % 100:02d}"


def _totals(spec):
    sub = sum(it["qty"] * it["price_cents"] for it in spec["items"])
    base = sub - spec["discount_cents"]
    tax = (base * spec["tax_rate_pct"] + 50) // 100
    return sub, base, tax, base + tax


def receipt_render(spec, knobs, path):
    f = font(knobs["font_px"], mono=True)
    fb = font(knobs["font_px"] + 4, mono=True, bold=True)
    ink = (20, 20, 20) if knobs["ink"] == "dark" else (95, 95, 105)
    width_chars = 34
    lh = int(knobs["font_px"] * 1.45)
    lines = [("title", spec["store"].upper()), ("rule", "")]
    for it in spec["items"]:
        lines.append(("text", f"{it['qty']} x {it['name']} @ {_money(it['price_cents'])}"
                      .ljust(width_chars - 9) + _money(it["qty"] * it["price_cents"]).rjust(9)))
    sub, base, tax, total = _totals(spec)
    lines.append(("rule", ""))
    lines.append(("text", "SUBTOTAL".ljust(width_chars - 9) + _money(sub).rjust(9)))
    if spec["discount_cents"]:
        lines.append(("text", "DISCOUNT".ljust(width_chars - 9) + ("-" + _money(spec["discount_cents"])).rjust(9)))
    lines.append(("text", f"TAX {spec['tax_rate_pct']}%".ljust(width_chars - 9) + _money(tax).rjust(9)))
    lines.append(("bold", "TOTAL".ljust(width_chars - 9) + _money(total).rjust(9)))
    W = int(max((fb if k in ("bold", "title") else f).getlength(t) for k, t in lines)) + 60
    H = lh * (len(lines) + 2) + 60
    paper = Image.new("RGB", (W, H), (252, 250, 244))
    d = ImageDraw.Draw(paper)
    y = 30
    bands = []
    for kind, txt in lines:
        if kind == "rule":
            d.line([30, y + lh // 2, W - 30, y + lh // 2], fill=ink)
        elif kind == "title":
            d.text((W / 2, y + lh / 2), txt, font=fb, fill=ink, anchor="mm")
        else:
            d.text((30, y + lh / 2), txt, font=fb if kind == "bold" else f, fill=ink, anchor="lm")
            right = 30 + (fb if kind == "bold" else f).getbbox(txt)[2]
            bands.append([y, y + lh, right])
        y += lh
    pre = np.asarray(paper).copy()
    bg = Image.new("RGB", (W + 80, H + 80), (90, 90, 95))
    bg.paste(paper, (40, 40))
    out = bg
    if knobs["skew_deg"]:
        out = out.rotate(knobs["skew_deg"], resample=Image.BICUBIC, expand=True, fillcolor=(90, 90, 95))
    if knobs["blur"]:
        out = out.filter(ImageFilter.GaussianBlur(knobs["blur"]))
    out.save(path)
    return {"w": out.width, "h": out.height, "paper_w": W, "bands": bands, "_pre": pre}


def receipt_probe(spec, info, img):
    fails = []
    pre = info.pop("_pre")
    gray = pre.astype(int).sum(-1) / 3
    for k, (y0, y1, right) in enumerate(info["bands"]):
        if right > info["paper_w"] - 20:
            fails.append(f"line {k} runs off the paper")
        if (gray[y0:y1, 25:info["paper_w"] - 25] < 160).sum() < 20:
            fails.append(f"line {k} has no ink")
    # the paper must stay fully inside the final image (no cropping after skew)
    edge = np.concatenate([img[0], img[-1], img[:, 0], img[:, -1]]).astype(int)
    if (edge.sum(-1) > 600).any():
        fails.append("paper touches the image edge")
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
                        format_hint="a number with two decimals")
    lt = sorted((it["qty"] * it["price_cents"] for it in items), reverse=True)
    if lt[0] - lt[1] < 100:
        raise Reject("top two line totals within 1.00")
    best = max(items, key=lambda it: it["qty"] * it["price_cents"])
    return Question(qt, {}, "Which item has the largest line total?", best["name"], "exact",
                    format_hint="the item name", choices=[it["name"] for it in items])


register(Family("table", table_build, table_render, table_ask, table_probe))
register(Family("receipt", receipt_build, receipt_render, receipt_ask, receipt_probe))
