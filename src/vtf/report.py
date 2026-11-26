"""Build an HTML and Markdown report: accuracy maps, knob effects, failure gallery."""

from __future__ import annotations

import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .core import DIFFICULTIES  # noqa: E402
from .grade import grade_model, knob_effects, summarise  # noqa: E402


def _pct(x):
    return "n/a" if x is None else f"{100 * x:.0f}%"


def _heatmap(models, summaries, families, path):
    fig, axes = plt.subplots(1, len(models), figsize=(3.2 * len(models) + 1, 0.45 * len(families) + 1.6), squeeze=False)
    for ax, m in zip(axes[0], models):
        cells = summaries[m]["cells"]
        M = np.array([[cells.get(f"{f}|{d}", {}).get("acc", np.nan) or 0.0 if f"{f}|{d}" in cells else np.nan
                       for d in DIFFICULTIES] for f in families], dtype=float)
        ax.imshow(M, vmin=0, vmax=1, cmap="RdYlGn", aspect="auto")
        for i in range(len(families)):
            for j in range(len(DIFFICULTIES)):
                if not np.isnan(M[i, j]):
                    ax.text(j, i, f"{100 * M[i, j]:.0f}", ha="center", va="center", fontsize=9)
        ax.set_xticks(range(len(DIFFICULTIES)), DIFFICULTIES)
        ax.set_yticks(range(len(families)), families if ax is axes[0][0] else [""] * len(families))
        ax.set_title(f"{m}\n{_pct(summaries[m]['acc'])} overall", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110, metadata={"Software": None})
    plt.close(fig)


def build(dataset: Path, models: list[str], out: Path | None = None, gallery: int = 24) -> Path:
    dataset = Path(dataset)
    out = Path(out or dataset / "report")
    out.mkdir(parents=True, exist_ok=True)
    rows = {m: grade_model(dataset, m) for m in models}
    summaries = {m: summarise(r) for m, r in rows.items()}
    families = sorted({r["family"] for rs in rows.values() for r in rs})
    gen = json.loads((dataset / "generation.json").read_text()) if (dataset / "generation.json").exists() else {}
    val = json.loads((dataset / "validation.json").read_text()) if (dataset / "validation.json").exists() else {}
    _heatmap(models, summaries, families, out / "heatmap.png")
    effects = {m: knob_effects(r) for m, r in rows.items()}
    (out / "summary.json").write_text(json.dumps({"models": summaries, "knob_effects": effects,
                                                  "generation": gen, "validation": val}, indent=1, default=str))

    real = [m for m in models if m not in ("oracle", "random")]
    md = ["# Visual Task Factory: results", ""]
    md.append(f"Dataset: {gen.get('items', '?')} items, {len(families)} families x 3 difficulties, master seed "
              f"{gen.get('master_seed', '?')}.")
    if val:
        md.append(f"Validation: {val.get('items_checked')} items re-checked; answer re-derivation "
                  f"{val.get('rederive_agree')}/{val.get('items_checked')} agree; render probes "
                  f"{val.get('probe_pass')}/{val.get('items_checked')} pass; byte-identical regeneration "
                  f"{val.get('identical_images')}/{val.get('items_checked')}.")
    md += ["", "## Accuracy by model", "", "| model | overall | easy | medium | hard | unparseable | median latency |",
           "|---|---|---|---|---|---|---|"]
    for m in models:
        s = summaries[m]
        bd = s["by_difficulty"]
        md.append(f"| {m} | {_pct(s['acc'])} | " + " | ".join(_pct(bd.get(d, {}).get("acc")) for d in DIFFICULTIES)
                  + f" | {s['modes'].get('unparseable', 0)} | {s['median_latency_s']}s |")
    md += ["", "## Accuracy by family", "", "| family | " + " | ".join(models) + " |",
           "|---|" + "---|" * len(models)]
    for f in families:
        md.append(f"| {f} | " + " | ".join(_pct(summaries[m]["by_family"].get(f, {}).get("acc")) for m in models) + " |")
    md += ["", "## Question types (real models)", "", "| family/question | " + " | ".join(real) + " | n |",
           "|---|" + "---|" * (len(real) + 1)]
    qts = sorted({q for m in real for q in summaries[m]["by_qtype"]})
    for q in qts:
        n = summaries[real[0]]["by_qtype"].get(q, {}).get("n", 0) if real else 0
        md.append(f"| {q} | " + " | ".join(_pct(summaries[m]["by_qtype"].get(q, {}).get("acc")) for m in real) + f" | {n} |")
    md += ["", "## Knobs that hurt most", "", "Accuracy for each value of a difficulty knob, within one family "
           "(largest spread first; groups of 3 or more items).", ""]
    for m in real:
        md.append(f"**{m}**")
        md.append("")
        for e in effects[m][:8]:
            vals = ", ".join(f"{k}: {_pct(v['acc'])} (n={v['n']})" for k, v in e["values"].items())
            md.append(f"- {e['family']} / {e['knob']}: {vals}")
        md.append("")
    items_by_id = {}
    for line in (dataset / "items.jsonl").read_text().splitlines():
        d = json.loads(line)
        items_by_id[d["id"]] = d
    md += _sweep_section(rows, real, items_by_id)
    (out / "REPORT.md").write_text("\n".join(md) + "\n")

    # HTML with failure gallery
    fails = []
    for m in real:
        fails += [r for r in rows[m] if not r["correct"]]
    fails.sort(key=lambda r: (r["family"], r["difficulty"], r["id"], r["model"]))
    seen, pick_f = set(), []
    for r in fails:
        key = (r["family"], r["model"])
        if sum(1 for k in seen if k[:2] == key) < max(1, gallery // max(1, len(families) * max(1, len(real)))):
            seen.add(key + (r["id"],))
            pick_f.append(r)
    body = [f"<h1>Visual Task Factory: results</h1><img src='heatmap.png' style='max-width:100%'>"]
    body.append("<pre>" + html.escape("\n".join(md)) + "</pre><h2>Failure gallery</h2><div class='g'>")
    for r in pick_f:
        it = items_by_id[r["id"]]
        img = Path("..") / it["image"]
        body.append(f"<figure><img src='{html.escape(str(img))}'><figcaption><b>{html.escape(r['model'])}</b> "
                    f"{html.escape(r['id'])}<br>Q: {html.escape(it['question']['text'])}<br>"
                    f"Expected: <b>{html.escape(str(r['answer']))}</b> (tol {it['question']['tolerance']})<br>"
                    f"Model: {html.escape(str(r['reply'])[:200])}<br>mode: {r['mode']}</figcaption></figure>")
    body.append("</div>")
    css = ("body{font-family:sans-serif;max-width:1100px;margin:auto;padding:0 16px}pre{white-space:pre-wrap}"
           ".g{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}"
           "figure{margin:0;border:1px solid #ccc;padding:6px}figure img{width:100%}figcaption{font-size:12px}")
    (out / "index.html").write_text(f"<!doctype html><meta charset=utf-8><title>VTF report</title><style>{css}</style>"
                                    + "".join(body))
    return out


def _sweep_section(rows, models, items_by_id) -> list[str]:
    """Paired analysis for sweep datasets: per knob value accuracy and how often one knob flips the outcome."""
    if not any("sweep_knob" in it.get("render", {}) for it in items_by_id.values()):
        return []
    md = ["", "## Controlled sweeps (same content, one knob changed)", "",
          "Accuracy for each knob value; *flips* = groups where changing only this knob turned a right answer "
          "wrong or the reverse.", ""]
    for m in models:
        md += [f"**{m}**", "", "| family / knob | value: accuracy | flips |", "|---|---|---|"]
        by = {}
        for r in rows[m]:
            rd = items_by_id[r["id"]]["render"]
            if rd["sweep_knob"] == "base":  # the base image counts for every knob at its base value
                pairs = list(rd["sweep_base_knobs"].items())
            else:
                pairs = [(rd["sweep_knob"], rd["sweep_value"])]
            for knob, val in pairs:
                by.setdefault((r["family"], knob), {}).setdefault(rd["sweep_base"], {})[json.dumps(val)] = r["correct"]
        for (fam, knob), groups in sorted(by.items()):
            vals = sorted({v for g in groups.values() for v in g})
            accs = ", ".join(
                f"{v}: {_pct(sum(g[v] for g in groups.values() if v in g) / max(1, sum(v in g for g in groups.values())))}"
                for v in vals)
            flips = sum(len(set(g.values())) > 1 for g in groups.values())
            md.append(f"| {fam} / {knob} | {accs} | {flips}/{len(groups)} |")
        md.append("")
    return md
