"""Generate a dataset: seed -> spec -> image -> probes -> question -> independent re-check."""

from __future__ import annotations

import collections
import re
import json
from pathlib import Path

import numpy as np
from PIL import Image

from . import families  # noqa: F401  (registers families)
from .core import DIFFICULTIES, REGISTRY, Item, Reject, item_seed, save_items
from .verify import rederive, same_answer

MAX_ATTEMPTS = 40


def generate_one(fam_name: str, diff: str, index: int, master: int, img_dir: Path, stats: dict) -> Item:
    fam = REGISTRY[fam_name]
    seed = item_seed(master, fam_name, diff, index)
    rng = np.random.default_rng(seed)
    item_id = f"{fam_name}-{diff}-{index:03d}"
    path = img_dir / f"{item_id}.png"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        spec, knobs = fam.build(rng, diff)
        info = fam.render(spec, knobs, path)
        img = np.asarray(Image.open(path).convert("RGB"))
        fails = fam.probe(spec, info, img)
        if fails:
            stats["probe_reject"][fam_name] += 1
            stats["reasons"][f"{fam_name}: probe: " + re.sub(r"[0-9.]+(px)?", "#", fails[0])] += 1
            continue
        try:
            q = fam.ask(spec, info, rng, diff)
        except Reject as e:
            stats["ambiguity_reject"][fam_name] += 1
            stats["reasons"][f"{fam_name}: {e}"] += 1
            continue
        again = rederive(fam_name, spec, q.qtype, q.params)
        if not same_answer(q.answer, again, q.answer_type):
            raise AssertionError(f"{item_id}: generator says {q.answer!r}, verifier says {again!r}")
        return Item(item_id, fam_name, diff, seed, knobs, spec, f"images/{path.name}", q,
                    render=_jsonable(info), attempts=attempt)
    raise RuntimeError(f"{item_id}: no valid item after {MAX_ATTEMPTS} attempts")


def generate(out: Path, master: int = 7, per_cell: int = 10, fams: list[str] | None = None) -> dict:
    out = Path(out)
    img_dir = out / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    fams = fams or sorted(REGISTRY)
    stats = {"probe_reject": collections.Counter(), "ambiguity_reject": collections.Counter(),
             "reasons": collections.Counter()}
    items = [generate_one(f, d, i, master, img_dir, stats) for f in fams for d in DIFFICULTIES for i in range(per_cell)]
    save_items(items, out / "items.jsonl")
    summary = {
        "master_seed": master, "items": len(items), "families": fams, "per_cell": per_cell,
        "attempts_total": sum(i.attempts for i in items),
        "probe_reject": dict(stats["probe_reject"]), "ambiguity_reject": dict(stats["ambiguity_reject"]),
        "top_reject_reasons": stats["reasons"].most_common(25),
    }
    (out / "generation.json").write_text(json.dumps(summary, indent=2))
    return summary


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return round(float(o), 2)
    if isinstance(o, np.bool_):
        return bool(o)
    return o
