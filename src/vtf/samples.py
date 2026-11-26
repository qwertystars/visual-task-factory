"""Contact sheet: one image per family x difficulty, with its question and answer."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

from .core import DIFFICULTIES
from .families.text import font


def sheet(dataset: Path, out: Path, tile: int = 300) -> Path:
    dataset = Path(dataset)
    items = [json.loads(l) for l in (dataset / "items.jsonl").read_text().splitlines()]
    fams = sorted({i["family"] for i in items})
    cap = 70
    W, H = tile * 3 + 120, (tile + cap) * len(fams) + 30
    c = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(c)
    f, fb = font(11), font(14, bold=True)
    for j, diff in enumerate(DIFFICULTIES):
        d.text((120 + j * tile + tile // 2, 15), diff, font=fb, fill="black", anchor="mm")
    for i, fam in enumerate(fams):
        y = 30 + i * (tile + cap)
        d.text((5, y + tile // 2), fam, font=fb, fill="black", anchor="lm")
        for j, diff in enumerate(DIFFICULTIES):
            it = next(x for x in items if x["family"] == fam and x["difficulty"] == diff)
            im = Image.open(dataset / it["image"]).convert("RGB")
            im.thumbnail((tile - 8, tile - 8))
            x = 120 + j * tile
            c.paste(im, (x + (tile - im.width) // 2, y + (tile - im.height) // 2))
            a = it["question"]["answer"]
            txt = f"Q: {it['question']['text'].split(' Moves go')[0]}  A: {', '.join(a) if isinstance(a, list) else a}"
            d.multiline_text((x + 4, y + tile), "\n".join(textwrap.wrap(txt, 48)[:4]), font=f, fill=(40, 40, 40))
    c.save(out)
    return Path(out)
