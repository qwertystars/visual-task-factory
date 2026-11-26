"""Shared types, seeding and family registry."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

DIFFICULTIES = ("easy", "medium", "hard")


def item_seed(master: int, family: str, difficulty: str, index: int) -> int:
    """Stable 63-bit seed for one item, independent of generation order."""
    h = hashlib.sha256(f"{master}:{family}:{difficulty}:{index}".encode()).digest()
    return int.from_bytes(h[:8], "big") >> 1


@dataclass
class Question:
    qtype: str
    params: dict
    text: str
    answer: Any
    answer_type: str  # exact | numeric | set | ordering | time | yesno
    tolerance: float = 0.0
    format_hint: str = ""
    choices: list | None = None  # valid options for label answers, used to grade free text


@dataclass
class Item:
    id: str
    family: str
    difficulty: str
    seed: int
    knobs: dict
    spec: dict
    image: str
    question: Question
    render: dict = field(default_factory=dict)
    attempts: int = 1

    def to_json(self) -> dict:
        d = asdict(self)
        return d

    @staticmethod
    def from_json(d: dict) -> "Item":
        d = dict(d)
        d["question"] = Question(**d["question"])
        return Item(**d)


class Reject(Exception):
    """Raised when a candidate item is ambiguous or fails a render probe."""


@dataclass
class Family:
    name: str
    # build(rng, difficulty) -> (spec, knobs)
    build: Callable[[np.random.Generator, str], tuple[dict, dict]]
    # render(spec, knobs, path) -> render info (pixel geometry for probes)
    render: Callable[[dict, dict, Path], dict]
    # ask(spec, render_info, rng, difficulty) -> Question (raises Reject if ambiguous)
    ask: Callable[[dict, dict, np.random.Generator, str], Question]
    # probe(spec, render_info, image_array) -> list of failed checks (empty = image matches spec)
    probe: Callable[[dict, dict, np.ndarray], list[str]]


REGISTRY: dict[str, Family] = {}


def register(fam: Family) -> Family:
    REGISTRY[fam.name] = fam
    return fam


def load_items(path: Path) -> list[Item]:
    return [Item.from_json(json.loads(l)) for l in Path(path).read_text().splitlines() if l.strip()]


def save_items(items: list[Item], path: Path) -> None:
    Path(path).write_text("".join(json.dumps(i.to_json(), sort_keys=True) + "\n" for i in items))


def pick(rng: np.random.Generator, seq, k: int | None = None, replace: bool = False):
    idx = rng.choice(len(seq), size=k, replace=replace) if k is not None else rng.integers(len(seq))
    if k is None:
        return seq[int(idx)]
    return [seq[int(i)] for i in idx]


WORDS = [
    "Apex", "Birch", "Cobalt", "Delta", "Ember", "Falcon", "Garnet", "Harbor", "Iris", "Juniper",
    "Kestrel", "Lumen", "Maple", "Nimbus", "Onyx", "Pixel", "Quartz", "Raven", "Sierra", "Tundra",
    "Umber", "Vertex", "Willow", "Xenon", "Yarrow", "Zephyr",
]

FRUITS = [
    "Apples", "Bananas", "Cherries", "Dates", "Figs", "Grapes", "Kiwis", "Lemons", "Mangoes",
    "Melons", "Oranges", "Pears", "Plums", "Peaches", "Limes", "Guavas",
]

# Named colours chosen to stay far apart; names are what questions use.
NAMED_COLORS = {
    "red": (220, 40, 40),
    "blue": (40, 90, 220),
    "green": (40, 160, 60),
    "yellow": (235, 200, 30),
    "purple": (140, 60, 180),
    "orange": (245, 130, 20),
    "black": (30, 30, 30),
    "pink": (240, 120, 190),
}
