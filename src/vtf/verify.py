"""Independent answer re-derivation.

These functions recompute every answer from the spec with code written separately
from the generators (plain loops, no shared helpers), so a bug in one path shows up
as a disagreement instead of a silently wrong label.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal



def same_answer(a, b, answer_type: str) -> bool:
    if answer_type in ("set",):
        return sorted(map(str, a)) == sorted(map(str, b))
    if answer_type == "numeric":
        return abs(float(a) - float(b)) < 1e-9
    return a == b


def _argbest(keys, values, larger=True):
    best_k, best_v = None, None
    for k, v in zip(keys, values):
        if best_v is None or (v > best_v if larger else v < best_v):
            best_k, best_v = k, v
    return best_k


# ---- charts

def _bar(spec, qt, p):
    L, V = spec["labels"], spec["values"]
    if qt == "tallest":
        return _argbest(L, V, True)
    if qt == "shortest":
        return _argbest(L, V, False)
    if qt == "value_of":
        return dict(zip(L, V))[p["label"]]
    if qt == "count_above":
        c = 0
        for v in V:
            if v > p["threshold"]:
                c += 1
        return c
    if qt == "diff":
        m = dict(zip(L, V))
        return m[p["a"]] - m[p["b"]]
    if qt == "top3":
        pairs = list(zip(V, L))
        pairs.sort(key=lambda t: t[0], reverse=True)
        return [l for _, l in pairs[:3]]
    raise KeyError(qt)


def _line(spec, qt, p):
    names, S, xs = spec["names"], spec["series"], spec["x"]
    if qt == "highest_at":
        j = xs.index(p["x"])
        return _argbest(names, [s[j] for s in S])
    if qt == "value_at":
        return S[names.index(p["series"])][xs.index(p["x"])]
    if qt == "peak_month":
        return _argbest(xs, S[names.index(p["series"])])
    if qt == "crossings":
        a, b = S[names.index(p["a"])], S[names.index(p["b"])]
        n = 0
        for k in range(1, len(a)):
            if (a[k - 1] > b[k - 1]) != (a[k] > b[k]):
                n += 1
        return n
    raise KeyError(qt)


def _pie(spec, qt, p):
    N, S = spec["names"], spec["shares"]
    if qt == "largest":
        return _argbest(N, S)
    if qt == "smallest":
        return _argbest(N, S, False)
    if qt == "share_of":
        return S[N.index(p["name"])]
    raise KeyError(qt)


# ---- scenes

def _shapes(spec, qt, p):
    objs = spec["objects"]
    if qt == "count_color":
        return len([o for o in objs if o["color"] == p["color"]])
    if qt == "count_kind":
        return len([o for o in objs if o["kind"] == p["kind"]])
    if qt == "count_combo":
        return len([o for o in objs if o["kind"] == p["kind"] and o["color"] == p["color"]])
    if qt == "largest_color":
        return _argbest([o["color"] for o in objs], [o["size"] for o in objs])
    if qt == "leftmost_kind":
        return _argbest([o["kind"] for o in objs], [o["x"] - o["r"] for o in objs], larger=False)
    if qt == "total":
        return len(objs)
    raise KeyError(qt)


def _clock(spec, qt, p):
    h, m = spec["hour"], spec["minute"]
    if qt == "time":
        return str(h) + ":" + str(m).zfill(2)
    if qt == "minutes_to_hour":
        return (60 - m) % 60
    raise KeyError(qt)


def _table(spec, qt, p):
    cols, rows = spec["columns"], spec["rows"]
    ci = {c: k for k, c in enumerate(cols)}
    if qt == "lookup":
        for r in rows:
            if r[0] == p["row"]:
                return r[ci[p["col"]]]
    if qt == "col_sum":
        t = 0
        for r in rows:
            t += r[ci[p["col"]]]
        return t
    if qt == "row_max":
        return _argbest([r[0] for r in rows], [r[ci[p["col"]]] for r in rows])
    if qt == "count_gt":
        return len([1 for r in rows if r[ci[p["col"]]] > p["threshold"]])
    raise KeyError(qt)


def _receipt(spec, qt, p):
    items = spec["items"]
    cents = [it["qty"] * it["price_cents"] for it in items]
    if qt == "total":
        base = Decimal(sum(cents) - spec.get("discount_cents", 0))
        tax = (base * Decimal(spec["tax_rate_pct"]) / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        return float((base + tax) / 100)
    if qt == "units":
        return sum(it["qty"] for it in items)
    if qt == "line_total":
        for it, c in zip(items, cents):
            if it["name"] == p["name"]:
                return round(c / 100, 2)
    if qt == "priciest":
        return _argbest([it["name"] for it in items], cents)
    raise KeyError(qt)


def _grid(spec, qt, p):
    n, walls = spec["n"], {tuple(w) for w in spec["walls"]}
    if qt == "walls":
        return len(walls)
    if qt in ("path_len", "reachable"):
        # Bellman-Ford style relaxation, deliberately different from the BFS in the generator.
        INF = 10 ** 9
        dist = {(r, c): INF for r in range(n) for c in range(n) if (r, c) not in walls}
        dist[tuple(spec["start"])] = 0
        changed = True
        while changed:
            changed = False
            for (r, c), d in list(dist.items()):
                if d == INF:
                    continue
                for nb in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if nb in dist and dist[nb] > d + 1:
                        dist[nb] = d + 1
                        changed = True
        d = dist[tuple(spec["goal"])]
        if qt == "reachable":
            return "yes" if d < INF else "no"
        return d
    raise KeyError(qt)



RULES = {
    "bar_chart": _bar, "line_chart": _line, "pie_chart": _pie, "shapes": _shapes, "clock": _clock,
    "table": _table, "receipt": _receipt, "grid_path": _grid,
}


def rederive(family: str, spec: dict, qtype: str, params: dict):
    return RULES[family](spec, qtype, params)
