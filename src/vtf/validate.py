"""Re-check a generated dataset from scratch.

For every item: regenerate it from its seed in a scratch folder and require the same
spec, question and image bytes; recompute the answer with the independent verifier;
re-run the render probes; and test the grader with the true answer and a corrupted one.
"""

from __future__ import annotations

import collections
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from .check import grade
from .core import REGISTRY, Question, load_items
from .generate import generate_one
from .verify import rederive, same_answer


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _corrupt(q: Question) -> str:
    a = q.answer
    if q.answer_type == "numeric":
        return str(float(a) + max(1.0, 3 * q.tolerance + 1))
    if q.answer_type == "time":
        h, m = a.split(":")
        return f"{int(h) % 12 + 1}:{m}"
    if q.answer_type == "ordering":
        return ", ".join(reversed(a))
    others = [c for c in (q.choices or []) if c != a]
    return others[0] if others else "none"


def validate(dataset: Path, master: int) -> dict:
    dataset = Path(dataset)
    items = load_items(dataset / "items.jsonl")
    scratch = dataset / "_regen"
    scratch.mkdir(exist_ok=True)
    res = collections.Counter()
    problems = []
    stats = {"probe_reject": collections.Counter(), "ambiguity_reject": collections.Counter(),
             "reasons": collections.Counter()}
    for it in items:
        res["items_checked"] += 1
        if "sweep_knob" not in it.render:  # sweep items are checked by re-render below
            idx = int(it.id.rsplit("-", 1)[1])
            again = generate_one(it.family, it.difficulty, idx, master, scratch, stats)
            if again.spec == it.spec and again.question == it.question:
                res["identical_spec"] += 1
            else:
                problems.append(f"{it.id}: spec/question differ on regeneration")
            if _sha(scratch / Path(it.image).name) == _sha(dataset / it.image):
                res["identical_images"] += 1
            else:
                problems.append(f"{it.id}: image bytes differ on regeneration")
        if same_answer(it.question.answer, rederive(it.family, it.spec, it.question.qtype, it.question.params),
                       it.question.answer_type):
            res["rederive_agree"] += 1
        else:
            problems.append(f"{it.id}: verifier disagrees")
        # probes on a fresh render (probes need render-time geometry such as masks)
        fam = REGISTRY[it.family]
        p = scratch / "probe.png"
        info = fam.render(it.spec, it.knobs, p)
        fails = fam.probe(it.spec, info, np.asarray(Image.open(p).convert("RGB")))
        if "sweep_knob" in it.render and _sha(p) == _sha(dataset / it.image):
            res["identical_images"] += 1
        if not fails:
            res["probe_pass"] += 1
        else:
            problems.append(f"{it.id}: probe {fails[0]}")
        a = it.question.answer
        true_txt = ", ".join(a) if isinstance(a, list) else str(a)
        if grade(it.question, true_txt)["correct"]:
            res["grader_accepts_truth"] += 1
        else:
            problems.append(f"{it.id}: grader rejects the true answer")
        if not grade(it.question, _corrupt(it.question))["correct"]:
            res["grader_rejects_corrupt"] += 1
        else:
            problems.append(f"{it.id}: grader accepts a corrupted answer")
    shutil.rmtree(scratch)
    out = dict(res)
    out["problems"] = problems
    (dataset / "validation.json").write_text(json.dumps(out, indent=1))
    return out
