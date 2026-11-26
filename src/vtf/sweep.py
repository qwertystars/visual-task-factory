"""Controlled knob sweeps: same spec, same question, one knob changed at a time.

The main dataset varies many things at once. A sweep holds the content fixed and
changes a single visual factor, so any change in a model's answer is caused by that
factor alone. Each variant still passes the probes and ambiguity guards; if any
variant of a base fails, the whole base is dropped so every group stays complete.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from . import families  # noqa: F401
from .core import REGISTRY, Item, Reject, item_seed, save_items
from .verify import rederive, same_answer

SWEEPS = {
    "bar_chart": {"value_labels": [True, False], "gridlines": [True, False], "horizontal": [False, True],
                  "label_rotation": [0, 45, 90]},
    "pie_chart": {"labels": ["pct", "name", "legend"]},
    "clock": {"numerals": ["all", "quarters", "roman", "none"], "minute_ticks": [True, False],
              "second_hand": [False, True], "similar_hands": [False, True]},
    "table": {"font_px": [20, 15, 12, 10], "rules": [True, False], "zebra": [False, True]},
    "receipt": {"skew_deg": [0.0, 1.5, -1.5], "blur": [0.0, 0.8, 1.5], "ink": ["dark", "faded"]},
    "shapes": {"background": ["plain", "noise"]},
}


def _variants(base_knobs: dict, fam: str):
    """The base image first, then one image per non-base value of each knob."""
    yield "base", None, dict(base_knobs)
    for knob, values in SWEEPS[fam].items():
        for v in values:
            if v != base_knobs[knob]:
                yield knob, v, dict(base_knobs, **{knob: v})


def sweep(out: Path, master: int = 99, bases: int = 6) -> dict:
    out = Path(out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    items, dropped = [], 0
    for fam_name in SWEEPS:
        fam = REGISTRY[fam_name]
        b, idx = 0, 0
        while b < bases:
            if idx >= 50 * bases:
                raise RuntimeError(f"{fam_name}: only {b} of {bases} sweep bases pass after {idx} tries")
            seed = item_seed(master, fam_name, "sweep", idx)
            idx += 1
            spec, knobs = fam.build(np.random.default_rng(seed), "medium")
            group, ok = [], True
            for j, (knob, val, kn) in enumerate(_variants(knobs, fam_name)):
                iid = f"sweep-{fam_name}-{b:02d}-{j:02d}"
                path = out / "images" / f"{iid}.png"
                info = fam.render(spec, kn, path)
                if fam.probe(spec, info, np.asarray(Image.open(path).convert("RGB"))):
                    ok = False
                    break
                try:  # same question stream for every variant
                    q = fam.ask(spec, info, np.random.default_rng(seed + 1), "medium")
                except Reject:
                    ok = False
                    break
                assert same_answer(q.answer, rederive(fam_name, spec, q.qtype, q.params), q.answer_type)
                it = Item(iid, fam_name, "medium", seed, kn, spec, f"images/{path.name}", q)
                it.render = {"sweep_base": b, "sweep_knob": knob, "sweep_value": val,
                             "sweep_base_knobs": {k: knobs[k] for k in SWEEPS[fam_name]}}
                group.append(it)
            if ok and len({(g.question.qtype, json.dumps(g.question.answer)) for g in group}) == 1:
                items += group
                b += 1
            else:
                dropped += 1
                for g in group:
                    (out / g.image).unlink(missing_ok=True)
    save_items(items, out / "items.jsonl")
    summary = {"items": len(items), "bases_per_family": bases, "dropped_bases": dropped,
               "families": list(SWEEPS), "master_seed": master}
    (out / "generation.json").write_text(json.dumps(summary, indent=1))
    return summary
