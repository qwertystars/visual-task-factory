"""Render the demo video: a 1920x1080, 30 fps MP4 built from real runs.

Every number and hash on screen comes from this script's own runs (generate twice, validate,
grade) or from the committed results file. Nothing is typed in by hand.

Usage: uv run --frozen python scripts/render_demo_video.py [--work DIR] [--out FILE.mp4]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

import vtf.families  # noqa: F401  (registers families)
import vtf.generate
from vtf.check import grade
from vtf.core import REGISTRY, load_items
from vtf.families.text import font
from vtf.validate import _corrupt
from vtf.verify import rederive, same_answer

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1920, 1080, 30
FADE = 10  # frames of crossfade into each new step
DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"  # hyphen-like dashes that must never appear

BG = (248, 248, 245)
INK = (24, 24, 30)
MUTED = (105, 105, 112)
LINE = (210, 210, 205)
GOOD = (28, 125, 62)
BAD = (185, 38, 38)
BOX = (236, 236, 230)
BAR = (52, 98, 170)


# ---------------------------------------------------------------- data from real runs

def _vtf(*args: str, cwd: Path) -> str:
    exe = Path(sys.executable).parent / "vtf"
    return subprocess.run([str(exe), *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def _hash_tree(d: Path) -> list[tuple[str, str]]:
    files = sorted(p for p in d.rglob("*") if p.is_file() and p.suffix in (".png", ".json", ".jsonl"))
    return [(hashlib.sha256(p.read_bytes()).hexdigest(), "./" + p.relative_to(d).as_posix()) for p in files]


def _digest(rows: list[tuple[str, str]]) -> str:
    return hashlib.sha256("".join(f"{h}  {p}\n" for h, p in rows).encode()).hexdigest()


def _answer_text(a) -> str:
    return ", ".join(map(str, a)) if isinstance(a, list) else str(a)


def _table_after(md: str, heading: str) -> list[list[str]]:
    lines = md.splitlines()
    start = next(i for i, l in enumerate(lines) if l.lstrip("#").strip() == heading)
    rows = []
    for l in lines[start + 1:]:
        if l.startswith("|"):
            cells = [c.strip() for c in l.strip().strip("|").split("|")]
            if not set("".join(cells)) <= set("-: "):
                rows.append(cells)
        elif rows:
            break
    return rows


def read_results(path: Path) -> dict:
    md = path.read_text()
    main = md.split("## Sweep set")[0]
    return {
        "dataset_line": re.search(r"^Dataset: .*$", main, re.M).group(0),
        "validation_line": re.search(r"^Validation: .*$", main, re.M).group(0),
        "by_model": _table_after(main, "Accuracy by model"),
        "by_family": _table_after(main, "Accuracy by family"),
    }


def collect(work: Path, seed: int = 42, per_cell: int = 2, results: Path | None = None) -> dict:
    """Run generate twice on one seed, hash both trees, validate, grade true and corrupt answers."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    cmd = ["generate", "{d}", "--seed", str(seed), "--per-cell", str(per_cell)]
    runs = {}
    for d in ("a", "b"):
        shutil.rmtree(work / d, ignore_errors=True)
        _vtf(*[c.format(d=d) for c in cmd], cwd=work)
        rows = _hash_tree(work / d)
        runs[d] = {"files": len(rows), "digest": _digest(rows), "rows": rows}
    same = runs["a"]["rows"] == runs["b"]["rows"]
    if not same:
        raise SystemExit("determinism check failed: the two runs differ")
    items = load_items(work / "a" / "items.jsonl")
    val = json.loads(_vtf("validate", "a", "--seed", str(seed), cwd=work))

    fams = sorted(REGISTRY)
    grid = []
    for f in fams:
        it = next(i for i in items if i.family == f and i.difficulty == "hard")
        grid.append({"family": f, "image": str(work / "a" / it.image)})

    receipt = max((i for i in items if i.family == "receipt"), key=lambda i: abs(i.knobs.get("skew_deg", 0)))
    chart = next(i for i in items if i.family == "chart_table" and i.difficulty == "hard")

    def show(it):
        return {"id": it.id, "image": str(work / "a" / it.image), "question": it.question.text,
                "answer": _answer_text(it.question.answer), "knobs": it.knobs}

    again = rederive(chart.family, chart.spec, chart.question.qtype, chart.question.params)
    verifier = {**show(chart), "generator": _answer_text(chart.question.answer), "rederived": _answer_text(again),
                "agree": same_answer(chart.question.answer, again, chart.question.answer_type)}

    picks = [next(i for i in items if i.family == "receipt" and i.question.answer_type == "numeric"),
             next(i for i in items if i.question.answer_type == "exact" and i.question.choices)]
    grading = []
    for it in picks:
        true_txt, bad_txt = _answer_text(it.question.answer), _corrupt(it.question)
        grading.append({"id": it.id, "question": it.question.text, "true": true_txt, "corrupt": bad_txt,
                        "true_ok": grade(it.question, true_txt)["correct"],
                        "corrupt_ok": grade(it.question, bad_txt)["correct"]})

    first = runs["a"]["rows"][:3]
    data = {
        "seed": seed, "per_cell": per_cell, "n_families": len(fams), "n_items": len(items),
        "pipeline": vtf.generate.__doc__.split(":", 1)[1].strip().rstrip(".").split(" -> "),
        "command": "vtf " + " ".join(cmd),
        "runs": {d: {"files": r["files"], "digest": r["digest"]} for d, r in runs.items()},
        "identical": same,
        "sample_hashes": [{"path": p, "a": h, "b": dict((q, x) for x, q in runs["b"]["rows"])[p]} for h, p in first],
        "validation": val, "grid": grid, "receipt": show(receipt), "chart_table": show(chart),
        "verifier": verifier, "grading": grading,
        "results": read_results(results or ROOT / "docs" / "RESULTS.md"),
    }
    (work / "data.json").write_text(json.dumps(data, indent=1))
    return data


# ---------------------------------------------------------------- frame builder

@dataclass(frozen=True)
class Text:
    xy: tuple[int, int]
    s: str
    size: int = 34
    bold: bool = False
    mono: bool = False
    color: tuple = INK
    anchor: str = "la"


@dataclass(frozen=True)
class Img:
    path: str
    box: tuple[int, int, int, int]  # x, y, w, h; image is fitted and centred


@dataclass(frozen=True)
class Rect:
    box: tuple[int, int, int, int]  # x0, y0, x1, y1
    fill: tuple | None = BOX
    outline: tuple | None = None
    width: int = 2


@dataclass(frozen=True)
class Line:
    pts: tuple[int, int, int, int]
    color: tuple = MUTED
    width: int = 4


@dataclass
class Step:
    seconds: float
    ops: list = field(default_factory=list)


@dataclass
class Scene:
    name: str
    steps: list[Step]


def _face(t: Text):
    return font(t.size, bold=t.bold, face="courier" if t.mono else "sans")


def render_step(step: Step) -> Image.Image:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for op in step.ops:
        if isinstance(op, Rect):
            d.rounded_rectangle(op.box, radius=12, fill=op.fill, outline=op.outline, width=op.width)
        elif isinstance(op, Line):
            d.line(op.pts, fill=op.color, width=op.width)
        elif isinstance(op, Img):
            x, y, w, h = op.box
            src = Image.open(op.path).convert("RGB")
            src.thumbnail((w, h), Image.Resampling.LANCZOS)
            im.paste(src, (x + (w - src.width) // 2, y + (h - src.height) // 2))
            d.rectangle((x + (w - src.width) // 2 - 1, y + (h - src.height) // 2 - 1,
                         x + (w + src.width) // 2, y + (h + src.height) // 2), outline=LINE, width=1)
        elif isinstance(op, Text):
            d.text(op.xy, op.s, font=_face(op), fill=op.color, anchor=op.anchor)
    return im


def png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def all_text(scenes: list[Scene]) -> list[str]:
    return [op.s for sc in scenes for st in sc.steps for op in st.ops if isinstance(op, Text)]


def total_seconds(scenes: list[Scene]) -> float:
    return sum(st.seconds for sc in scenes for st in sc.steps)


def _wrap(s: str, size: int, width: int, bold: bool = False, mono: bool = False) -> list[str]:
    f = font(size, bold=bold, face="courier" if mono else "sans")
    out, cur = [], ""
    for w in s.split():
        nxt = f"{cur} {w}".strip()
        if f.getlength(nxt) <= width or not cur:
            cur = nxt
        else:
            out.append(cur)
            cur = w
    return out + ([cur] if cur else [])


def _para(x, y, s, size=34, width=800, gap=1.35, **kw) -> list[Text]:
    return [Text((x, y + int(k * size * gap)), l, size, **kw)
            for k, l in enumerate(_wrap(s, size, width, kw.get("bold", False), kw.get("mono", False)))]


def _head(title: str, sub: str = "") -> list:
    ops = [Text((100, 70), title, 60, bold=True)]
    if sub:
        ops.append(Text((100, 150), sub, 32, color=MUTED))
    ops.append(Line((100, 205, W - 100, 205), LINE, 2))
    return ops


def _pct(s: str) -> float:
    return float(s.rstrip("%")) / 100


def build_scenes(data: dict) -> list[Scene]:
    scenes = []
    nf = data["n_families"]

    # 1. title
    scenes.append(Scene("title", [Step(6, [
        Text((W // 2, 420), "Visual Task Factory", 110, bold=True, anchor="mm"),
        Text((W // 2, 540), "Synthetic visual questions with answers known by construction", 44, color=MUTED, anchor="mm"),
        Text((W // 2, 650), f"{nf} task families. Same seed, same bytes. Every answer checked twice.", 36,
             anchor="mm"),
    ])]))

    # 2. pipeline
    stages = data["pipeline"]
    bw, gap = 230, 46
    x0 = (W - (len(stages) * bw + (len(stages) - 1) * gap)) // 2
    ops = _head("How one item is made", "Each stage can reject a candidate; rejected items are drawn again.")
    for k, s in enumerate(stages):
        x = x0 + k * (bw + gap)
        ops.append(Rect((x, 470, x + bw, 590), BOX, LINE))
        for j, line in enumerate(_wrap(s, 34, bw - 24, bold=True)):
            ops.append(Text((x + bw // 2, 530 + (j - (len(_wrap(s, 34, bw - 24, bold=True)) - 1) / 2) * 40), line,
                            34, bold=True, anchor="mm"))
        if k:
            ops.append(Line((x - gap + 6, 530, x - 8, 530), MUTED, 5))
            ops.append(Line((x - 22, 518, x - 8, 530), MUTED, 5))
            ops.append(Line((x - 22, 542, x - 8, 530), MUTED, 5))
    ops += _para(100, 700, "The spec holds the true answer before any pixel is drawn. Probes read the rendered image "
                 "back and check it matches the spec. A separate verifier, written apart from the generator, "
                 "computes the answer again.", 34, W - 200)
    scenes.append(Scene("pipeline", [Step(7, ops)]))

    # 3. family grid
    ops = _head(f"{nf} task families", f"Hard difficulty, seed {data['seed']}, straight from the generator")
    cw, ch = (W - 200) // 3, (H - 250) // 3
    for k, g in enumerate(data["grid"]):
        x, y = 100 + (k % 3) * cw, 230 + (k // 3) * ch
        ops.append(Img(g["image"], (x + 10, y + 4, cw - 20, ch - 50)))
        ops.append(Text((x + cw // 2, y + ch - 24), g["family"], 30, bold=True, anchor="mm"))
    scenes.append(Scene("families", [Step(10, ops)]))

    # 4. showcase: skewed receipt, then chart_table
    steps = []
    r = data["receipt"]
    kn = r["knobs"]
    ops = _head("Realistic receipts", "Paper is skewed, warped by perspective and blurred, and the answer stays exact")
    ops.append(Img(r["image"], (100, 230, 760, 820)))
    ops += [Text((960, 260), f"item {r['id']}", 30, mono=True, color=MUTED),
            Text((960, 330), f"skew_deg     {kn.get('skew_deg')}", 34, mono=True),
            Text((960, 380), f"perspective  {kn.get('perspective')}", 34, mono=True),
            Text((960, 430), f"blur         {kn.get('blur')}", 34, mono=True)]
    ops += _para(960, 540, "Q: " + r["question"], 38, 860)
    ops.append(Text((960, 800), f"Answer: {r['answer']}", 48, bold=True, color=GOOD))
    steps.append(Step(7, ops))
    c = data["chart_table"]
    ops = _head("chart_table: read two parts together", "A bar chart of units sold and a product table, joined by code")
    ops.append(Img(c["image"], (100, 240, 1060, 660)))
    ops += _para(1220, 300, "Q: " + c["question"], 38, 600)
    ops.append(Text((1220, 700), f"Answer: {c['answer']}", 48, bold=True, color=GOOD))
    ops.append(Text((1220, 770), f"item {c['id']}", 30, mono=True, color=MUTED))
    steps.append(Step(7, ops))
    scenes.append(Scene("showcase", steps))

    # 5. determinism
    ra, rb = data["runs"]["a"], data["runs"]["b"]
    cmd = data["command"]
    base = _head("Determinism, run live", "The generator runs twice on one seed; every output file is hashed")

    def run_block(y, tag, run):
        return [Rect((100, y, W - 100, y + 170), BOX, LINE),
                Text((130, y + 22), "$ " + cmd.format(d=tag), 32, mono=True),
                Text((130, y + 75), f"{run['files']} files, sha256 of all file hashes:", 30, color=MUTED),
                Text((130, y + 115), run["digest"], 32, mono=True, bold=True)]

    s1 = base + run_block(240, "a", ra)
    s2 = s1 + run_block(440, "b", rb)
    match = ra["digest"] == rb["digest"] and data["identical"]
    s3 = list(s2)
    s3.append(Text((130, 640), f"{'first files':<34} {'run a':<24}  {'run b':<24}", 26, mono=True, color=MUTED))
    y = 680
    for sh in data["sample_hashes"]:
        ok = sh["a"] == sh["b"]
        s3.append(Text((130, y), f"{sh['path']:<34} {sh['a'][:24]}  {sh['b'][:24]}  {'same' if ok else 'DIFFERENT'}",
                       26, mono=True, color=GOOD if ok else BAD))
        y += 40
    verdict = (f"IDENTICAL: {ra['files']} of {rb['files']} files match byte for byte" if match
               else "DIFFERENT")
    s3.append(Text((W // 2, 880), verdict, 54, bold=True, color=GOOD if match else BAD, anchor="mm"))
    s3.append(Text((W // 2, 950), "Item seeds come from sha256(master seed, family, difficulty, index), "
                   "so order does not matter.", 30, color=MUTED, anchor="mm"))
    scenes.append(Scene("determinism", [Step(4, s1), Step(4, s2), Step(6, s3)]))

    # 6. verifier and rejection
    v, val = data["verifier"], data["validation"]
    n = val["items_checked"]
    ops = _head("Independent verifier", "A second code path computes every answer again from the spec")
    ops.append(Img(v["image"], (100, 240, 900, 540)))
    ops += _para(1060, 250, "Q: " + v["question"], 32, 760)
    ops += [Text((1060, 470), f"generator answer    {v['generator']}", 34, mono=True),
            Text((1060, 520), f"verifier answer     {v['rederived']}", 34, mono=True),
            Text((1060, 590), "agree" if v["agree"] else "DISAGREE", 44, bold=True, color=GOOD if v["agree"] else BAD)]
    labels = [("rederive_agree", "answers re-derived and agree"), ("identical_images", "images byte-identical on regeneration"),
              ("probe_pass", "render probes pass"), ("grader_accepts_truth", "grader accepts the true answer"),
              ("grader_rejects_corrupt", "grader rejects a corrupted answer")]
    ops.append(Text((100, 810), f"vtf validate on this run ({n} items):", 30, color=MUTED))
    for k, (key, lab) in enumerate(labels):
        x, y = 100 + (k % 2) * 880, 860 + (k // 2) * 55
        ops.append(Text((x, y), f"{val[key]}/{n}  {lab}", 30, bold=True, color=GOOD if val[key] == n else BAD))
    s1 = ops
    ops = _head("Corrupt answers are rejected", "The real grader scores the true answer and a corrupted one")
    y = 250
    for g in data["grading"]:
        ops.append(Rect((100, y, W - 100, y + 330), BOX, LINE))
        ops += _para(130, y + 24, "Q: " + g["question"], 32, W - 260)
        for j, (lab, txt, ok) in enumerate((("true answer", g["true"], g["true_ok"]),
                                             ("corrupted", g["corrupt"], g["corrupt_ok"]))):
            yy = y + 150 + j * 80
            ops.append(Text((130, yy), f"{lab:<12} {txt}", 36, mono=True))
            ops.append(Text((W - 140, yy), "ACCEPTED" if ok else "REJECTED", 40, bold=True,
                            color=GOOD if ok else BAD, anchor="ra"))
        ops.append(Text((W - 140, y + 24), g["id"], 26, mono=True, color=MUTED, anchor="ra"))
        y += 370
    scenes.append(Scene("verifier", [Step(7, s1), Step(7, ops)]))

    # 7. benchmark (committed results, v1 renderers)
    res = data["results"]
    rows = res["by_model"]
    hdr = rows[0]
    ops = _head("Benchmark results, measured on v1 renderers",
                "Before chart_table existed. " + res["dataset_line"])
    ops.append(Text((100, 240), res["validation_line"], 26, color=MUTED))
    cols = [hdr.index(c) for c in ("overall", "easy", "medium", "hard")]
    bx, bwid = 480, 620
    for k, row in enumerate(rows[1:]):
        y = 330 + k * 120
        ops.append(Text((100, y + 30), row[0], 40, bold=True, anchor="lm"))
        frac = _pct(row[cols[0]])
        ops.append(Rect((bx, y, bx + bwid, y + 60), BOX, None))
        if frac > 0:
            ops.append(Rect((bx, y, bx + max(24, int(bwid * frac)), y + 60), BAR, None))
        ops.append(Text((bx + bwid + 30, y + 30), row[cols[0]], 44, bold=True, anchor="lm"))
        ops.append(Text((bx + bwid + 180, y + 30),
                        "   ".join(f"{hdr[c]} {row[c]}" for c in cols[1:]), 28, color=MUTED, anchor="lm"))
    s1 = ops
    fr = res["by_family"]
    ops = _head("Accuracy by family, v1 renderers", "Same run. Cells under 30% in red.")
    colw = (W - 200 - 340) // (len(fr[0]) - 1)
    for k, cell in enumerate(fr[0]):
        x = 100 if k == 0 else 440 + (k - 1) * colw + colw // 2
        ops.append(Text((x, 250), cell, 30, bold=True, anchor="la" if k == 0 else "ma"))
    for j, row in enumerate(fr[1:]):
        y = 310 + j * 82
        ops.append(Line((100, y - 12, W - 100, y - 12), LINE, 1))
        for k, cell in enumerate(row):
            x = 100 if k == 0 else 440 + (k - 1) * colw + colw // 2
            col = INK if k == 0 else (BAD if _pct(cell) < 0.3 else INK)
            ops.append(Text((x, y + 10), cell, 34, bold=k == 0, color=col, anchor="la" if k == 0 else "ma"))
    scenes.append(Scene("benchmark", [Step(7, s1), Step(7, ops)]))

    # 8. end card
    scenes.append(Scene("end", [Step(5, [
        Text((W // 2, 360), "Run it yourself", 72, bold=True, anchor="mm"),
        Text((W // 2, 500), "$ " + cmd.format(d="out"), 40, mono=True, anchor="mm"),
        Text((W // 2, 570), f"$ vtf validate out --seed {data['seed']}", 40, mono=True, anchor="mm"),
        Text((W // 2, 720), "Same seed gives the same images, questions and answers on any machine.", 36,
             color=MUTED, anchor="mm"),
    ])]))
    return scenes


def frames(scenes: list[Scene]):
    """Yield raw RGB frames; each new step crossfades in over FADE frames."""
    prev = None
    for sc in scenes:
        for st in sc.steps:
            cur = render_step(st)
            raw = cur.tobytes()
            n = round(st.seconds * FPS)
            for i in range(n):
                if prev is not None and i < FADE:
                    yield Image.blend(prev, cur, (i + 1) / (FADE + 1)).tobytes()
                else:
                    yield raw
            prev = cur


def encode(scenes: list[Scene], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-fflags", "+bitexact",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "4",
           "-flags:v", "+bitexact", "-fflags", "+bitexact", "-map_metadata", "-1",
           "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in frames(scenes):
        p.stdin.write(f)
    p.stdin.close()
    if p.wait():
        raise SystemExit(f"ffmpeg failed with code {p.returncode}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, default=ROOT / "runs" / "demo" / "video-work")
    ap.add_argument("--out", type=Path, default=ROOT / "runs" / "demo" / "vtf-demo-v2.mp4")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--per-cell", type=int, default=2)
    a = ap.parse_args(argv)
    data = collect(a.work, a.seed, a.per_cell)
    scenes = build_scenes(data)
    bad = [s for s in all_text(scenes) if any(c in s for c in DASHES)]
    if bad:
        raise SystemExit(f"dash characters on screen: {bad}")
    encode(scenes, a.out)
    print(json.dumps({"out": str(a.out), "seconds": total_seconds(scenes), "scenes": [s.name for s in scenes]}))


if __name__ == "__main__":
    main()
