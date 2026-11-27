"""Turn a model's free-text reply into a typed answer and grade it.

Each answer type has its own checker. Every grade records why it passed or failed,
so reports can separate "could not parse" from "read the picture wrong".
"""

from __future__ import annotations

import re

from .core import Question

WORD_NUM = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen twenty".split())}


def answer_segment(text: str) -> str:
    """The part of the reply that holds the answer (after the last 'Answer:' if present)."""
    t = text.strip()
    m = list(re.finditer(r"answer\s*[:\-]", t, flags=re.I))
    if m:
        t = t[m[-1].end():]
    t = t.replace("**", "").strip()
    return t


MONTHS = {m: m[:3] for m in ("january february march april may june july august september october november "
                              "december").split()} | {"sept": "sep"}


def _norm(s: str) -> str:
    t = re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()
    return " ".join(MONTHS.get(w, w) for w in t.split())


def parse_number(seg: str):
    s = seg.replace("−", "-")
    s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", s)  # thousands separators
    s = re.sub(r"(?<=\d),(?=\d{2}(?!\d))", ".", s)  # decimal comma, as on euro receipts: 12,50
    nums = re.findall(r"-?\d+(?:\.\d+)?", s)
    if nums:
        return float(nums[-1])
    words = [WORD_NUM[w] for w in re.findall(r"[a-z]+", s.lower()) if w in WORD_NUM]
    return float(words[-1]) if words else None


def parse_time(seg: str):
    m = re.search(r"(\d{1,2})\s*[:.h]\s*(\d{2})", seg)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if mi > 59 or h > 24:
        return None
    return h % 12 * 60 + mi


def match_choice(seg: str, choices: list[str]):
    """Return the single choice named in the text, or None if zero or several are named."""
    n = _norm(seg)
    exact = [c for c in choices if _norm(c) == n]
    if exact:
        return exact[0]
    found = [c for c in choices if re.search(rf"\b{re.escape(_norm(c))}s?\b", n)]
    return found[0] if len(found) == 1 else None


def grade(q: Question, reply: str) -> dict:
    seg = answer_segment(reply or "")
    t = q.answer_type
    parsed, ok = None, False
    if t == "numeric":
        parsed = parse_number(seg)
        if parsed is not None:
            ok = abs(parsed - float(q.answer)) <= q.tolerance + 1e-9
    elif t == "time":
        parsed = parse_time(seg)
        if parsed is not None:
            h, m = q.answer.split(":")
            want = int(h) % 12 * 60 + int(m)
            d = abs(parsed - want) % 720
            ok = min(d, 720 - d) <= q.tolerance
    elif t in ("exact", "yesno"):
        choices = q.choices or [q.answer]
        parsed = match_choice(seg.splitlines()[0] if seg else "", choices) or match_choice(seg, choices)
        ok = parsed is not None and _norm(parsed) == _norm(q.answer)
    elif t == "ordering":
        parts = [p for p in re.split(r",|\n|>|;|\bthen\b", seg) if p.strip()]
        seq = [match_choice(p, q.choices or q.answer) for p in parts]
        seq = [s for s in seq if s is not None]
        parsed = seq
        ok = [_norm(s) for s in seq[: len(q.answer)]] == [_norm(a) for a in q.answer]
    elif t == "set":
        parts = {_norm(p) for p in re.split(r",|\n|;|\band\b", seg) if p.strip()}
        parsed = sorted(parts)
        ok = parts == {_norm(a) for a in q.answer}
    else:
        raise ValueError(t)
    if parsed is None or parsed == []:
        mode = "unparseable"
    elif ok:
        mode = "correct"
    elif t == "numeric" and abs(parsed - float(q.answer)) <= max(2 * q.tolerance, 0.1 * abs(float(q.answer)), 1):
        mode = "near_miss"
    else:
        mode = "wrong"
    return {"correct": bool(ok), "parsed": parsed, "mode": mode}
