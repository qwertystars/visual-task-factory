"""Grade predictions against verified answers and summarise by family, difficulty and knob."""

from __future__ import annotations

import collections
import json
from pathlib import Path

from .check import grade
from .core import load_items


def latest_preds(path: Path) -> dict:
    """Last successful reply per item (earlier error lines are superseded by retries)."""
    out = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if "error" in r and r["id"] in out:
            continue
        out[r["id"]] = r
    return out


def grade_model(dataset: Path, model: str) -> list[dict]:
    dataset = Path(dataset)
    items = {i.id: i for i in load_items(dataset / "items.jsonl")}
    preds = latest_preds(dataset / "preds" / f"{model}.jsonl")
    rows = []
    for iid, item in items.items():
        p = preds.get(iid)
        if p is None:
            continue
        if "error" in p:
            g = {"correct": False, "parsed": None, "mode": "error"}
        else:
            g = grade(item.question, p["reply"])
        rows.append({"id": iid, "model": model, "family": item.family, "difficulty": item.difficulty,
                     "qtype": item.question.qtype, "answer": item.question.answer, "reply": p.get("reply"),
                     "latency_s": p.get("latency_s"), **g, "knobs": item.knobs})
    out = dataset / "graded" / f"{model}.jsonl"
    out.parent.mkdir(exist_ok=True)
    out.write_text("".join(json.dumps(r, default=str) + "\n" for r in rows))
    return rows


def acc(rows):
    return (sum(r["correct"] for r in rows) / len(rows)) if rows else None


def summarise(rows: list[dict]) -> dict:
    by = lambda key: {k: {"n": len(v), "acc": acc(v)} for k, v in sorted(_group(rows, key).items())}  # noqa: E731
    cell = {f"{f}|{d}": {"n": len(v), "acc": acc(v)}
            for (f, d), v in sorted(_group(rows, lambda r: (r["family"], r["difficulty"])).items())}
    modes = collections.Counter(r["mode"] for r in rows)
    lat = sorted(r["latency_s"] for r in rows if r.get("latency_s") is not None)
    return {
        "n": len(rows), "acc": acc(rows),
        "by_family": by(lambda r: r["family"]), "by_difficulty": by(lambda r: r["difficulty"]),
        "by_qtype": by(lambda r: f'{r["family"]}/{r["qtype"]}'), "cells": cell, "modes": dict(modes),
        "median_latency_s": lat[len(lat) // 2] if lat else None,
    }


def knob_effects(rows: list[dict]) -> list[dict]:
    """Accuracy split by each knob value within a family; shows which knob hurts most."""
    out = []
    for fam, fr in _group(rows, lambda r: r["family"]).items():
        keys = set().union(*(r["knobs"].keys() for r in fr))
        for k in sorted(keys):
            groups = _group(fr, lambda r: json.dumps(r["knobs"].get(k)))
            if len(groups) < 2 or len(groups) > 6:
                continue
            vals = {v: {"n": len(g), "acc": acc(g)} for v, g in sorted(groups.items())}
            accs = [x["acc"] for x in vals.values() if x["n"] >= 3]
            if len(accs) >= 2:
                out.append({"family": fam, "knob": k, "values": vals, "spread": max(accs) - min(accs)})
    return sorted(out, key=lambda x: -x["spread"])


def _group(rows, key):
    g = collections.defaultdict(list)
    for r in rows:
        g[key(r)].append(r)
    return g
