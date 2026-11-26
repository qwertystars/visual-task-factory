"""Ask a model every question in a dataset. Resumable; one JSON line per item.

Model spec forms:
  openai:<base_url>:<model_name>   any OpenAI-compatible chat endpoint (llama.cpp, vLLM, Ollama, ...)
  oracle                           reads the answer from the spec (grader self-test, must score 100%)
  random                           seeded guessing (lower bound)
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from .core import Item, load_items

PROMPT = "{q}\nReply with only the answer: {hint}."


def prompt_for(item: Item) -> str:
    return PROMPT.format(q=item.question.text, hint=item.question.format_hint or "a short answer")


def _oracle(item: Item, root: Path) -> str:
    a = item.question.answer
    return ", ".join(a) if isinstance(a, list) else str(a)


def _random(item: Item, root: Path) -> str:
    q = item.question
    rng = np.random.default_rng(item.seed ^ 0xBADC0DE)
    if q.choices:
        if q.answer_type == "ordering":
            return ", ".join(rng.permutation(q.choices)[:3])
        return str(rng.choice(q.choices))
    if q.answer_type == "time":
        return f"{rng.integers(1, 13)}:{rng.integers(0, 60):02d}"
    a = float(q.answer)
    return str(int(rng.integers(0, max(10, int(abs(a) * 2) + 1))))


class OpenAIChat:
    def __init__(self, base_url: str, model: str, timeout: float = 600, max_tokens: int = 48):
        self.url = base_url.rstrip("/") + "/v1/chat/completions"
        self.model, self.timeout, self.max_tokens = model, timeout, max_tokens
        self.key = os.environ.get("VTF_API_KEY", "none")

    def __call__(self, item: Item, root: Path) -> str:
        img = base64.b64encode((root / item.image).read_bytes()).decode()
        body = {
            "model": self.model, "temperature": 0, "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}},
                {"type": "text", "text": prompt_for(item)},
            ]}],
        }
        req = urllib.request.Request(self.url, json.dumps(body).encode(),
                                     {"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            out = json.load(r)
        return out["choices"][0]["message"]["content"]


def make_model(spec: str):
    if spec == "oracle":
        return "oracle", _oracle
    if spec == "random":
        return "random", _random
    if spec.startswith("openai:"):
        rest = spec[len("openai:"):]
        base, name = rest.rsplit(":", 1)
        return name, OpenAIChat(base, name)
    raise ValueError(f"unknown model spec {spec!r}")


def run(dataset: Path, model_spec: str, workers: int = 1, limit: int | None = None, name: str | None = None) -> Path:
    dataset = Path(dataset)
    items = load_items(dataset / "items.jsonl")
    if limit:
        items = items[:limit]
    mname, fn = make_model(model_spec)
    mname = name or mname
    out = dataset / "preds" / f"{mname}.jsonl"
    out.parent.mkdir(exist_ok=True)
    done = set()
    if out.exists():
        done = {json.loads(l)["id"] for l in out.read_text().splitlines() if l.strip() and "error" not in json.loads(l)}
    todo = [i for i in items if i.id not in done]

    def one(item):
        t = time.time()
        try:
            reply = fn(item, dataset)
            return {"id": item.id, "model": mname, "reply": reply, "latency_s": round(time.time() - t, 2)}
        except Exception as e:  # keep going; errors are retried on the next run
            return {"id": item.id, "model": mname, "error": repr(e), "latency_s": round(time.time() - t, 2)}

    with open(out, "a") as f, ThreadPoolExecutor(workers) as ex:
        for k, rec in enumerate(ex.map(one, todo), 1):
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if k % 10 == 0 or k == len(todo):
                print(f"[{mname}] {k}/{len(todo)} last {rec['latency_s']}s", flush=True)
    return out
