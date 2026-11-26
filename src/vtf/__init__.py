"""Visual Task Factory: synthetic visual questions with verified answers."""

import argparse
import json
from pathlib import Path


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="vtf", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="make a dataset of images, questions and verified answers")
    g.add_argument("out", type=Path)
    g.add_argument("--seed", type=int, default=7)
    g.add_argument("--per-cell", type=int, default=10, help="items per family x difficulty")
    g.add_argument("--families", nargs="*")
    v = sub.add_parser("validate", help="regenerate, re-derive, re-probe and grader-test every item")
    v.add_argument("dataset", type=Path)
    v.add_argument("--seed", type=int, default=7)
    r = sub.add_parser("run", help="ask a model every question")
    r.add_argument("dataset", type=Path)
    r.add_argument("model", help="oracle | random | openai:<base_url>:<model>")
    r.add_argument("--workers", type=int, default=1)
    r.add_argument("--limit", type=int)
    r.add_argument("--name")
    p = sub.add_parser("report", help="grade predictions and write REPORT.md + index.html")
    p.add_argument("dataset", type=Path)
    p.add_argument("models", nargs="+")
    p.add_argument("--out", type=Path)
    sub.add_parser("families", help="list task families")
    w = sub.add_parser("sweep", help="controlled set: same content, one visual knob changed at a time")
    w.add_argument("out", type=Path)
    w.add_argument("--seed", type=int, default=99)
    w.add_argument("--bases", type=int, default=6)
    s = sub.add_parser("samples", help="contact sheet: one image per family x difficulty")
    s.add_argument("dataset", type=Path)
    s.add_argument("out", type=Path)
    a = ap.parse_args(argv)

    if a.cmd == "generate":
        from .generate import generate
        print(json.dumps(generate(a.out, a.seed, a.per_cell, a.families), indent=1))
    elif a.cmd == "validate":
        from .validate import validate
        res = validate(a.dataset, a.seed)
        print(json.dumps({k: v for k, v in res.items() if k != "problems"}, indent=1))
        for line in res["problems"]:
            print("PROBLEM", line)
        if res["problems"]:
            raise SystemExit(1)
    elif a.cmd == "run":
        from .run import run
        print(run(a.dataset, a.model, a.workers, a.limit, a.name))
    elif a.cmd == "report":
        from .report import build
        print(build(a.dataset, a.models, a.out) / "REPORT.md")
    elif a.cmd == "sweep":
        from .sweep import sweep
        print(json.dumps(sweep(a.out, a.seed, a.bases), indent=1))
    elif a.cmd == "samples":
        from .samples import sheet
        print(sheet(a.dataset, a.out))
    elif a.cmd == "families":
        from . import families  # noqa: F401
        from .core import REGISTRY
        print("\n".join(sorted(REGISTRY)))
