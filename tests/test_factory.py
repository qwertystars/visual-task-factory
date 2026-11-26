"""Generators are deterministic, answers agree with the independent verifier, probes pass,
and the grader accepts true answers while rejecting wrong ones."""

import hashlib

import pytest

from vtf.check import grade
from vtf.core import DIFFICULTIES, REGISTRY, Question
from vtf.generate import generate, generate_one
from vtf.validate import validate
import vtf.families  # noqa: F401

FAMS = sorted(REGISTRY)


@pytest.fixture(scope="module")
def ds(tmp_path_factory):
    out = tmp_path_factory.mktemp("ds")
    generate(out, master=11, per_cell=2)
    return out


def test_all_families_registered():
    assert set(FAMS) == {"bar_chart", "line_chart", "pie_chart", "shapes", "clock", "table", "receipt", "grid_path"}


def test_validate_passes(ds):
    res = validate(ds, 11)
    n = res["items_checked"]
    assert n == len(FAMS) * len(DIFFICULTIES) * 2
    assert res["problems"] == []
    for k in ("identical_spec", "identical_images", "rederive_agree", "probe_pass",
              "grader_accepts_truth", "grader_rejects_corrupt"):
        assert res[k] == n, k


@pytest.mark.parametrize("fam", FAMS)
def test_seed_changes_output(tmp_path, fam):
    import collections
    st = {"probe_reject": collections.Counter(), "ambiguity_reject": collections.Counter(),
          "reasons": collections.Counter()}
    a = generate_one(fam, "medium", 0, 1, tmp_path, st)
    ha = hashlib.sha256((tmp_path / a.image.split("/")[1]).read_bytes()).hexdigest()
    b = generate_one(fam, "medium", 0, 2, tmp_path, st)
    hb = hashlib.sha256((tmp_path / b.image.split("/")[1]).read_bytes()).hexdigest()
    assert a.spec != b.spec and ha != hb


def q(t, ans, tol=0.0, choices=None):
    return Question("x", {}, "?", ans, t, tol, "", choices)


@pytest.mark.parametrize("reply,ok", [
    ("42", True), ("The answer is 42.", True), ("Answer: 42", True), ("forty-two", False),
    ("41", False), ("1,042", False), ("**42**", True),
])
def test_numeric(reply, ok):
    assert grade(q("numeric", 42), reply)["correct"] is ok


def test_numeric_tolerance():
    assert grade(q("numeric", 50, 5), "54")["correct"]
    assert not grade(q("numeric", 50, 5), "56")["correct"]
    assert grade(q("numeric", 3), "three")["correct"]


@pytest.mark.parametrize("reply,ok", [
    ("7:05", True), ("07:05", True), ("It is 7:05 PM", True), ("19:05", True), ("7:50", False), ("5:35", False),
])
def test_time(reply, ok):
    assert grade(q("time", "7:05"), reply)["correct"] is ok


def test_time_wraps_at_twelve():
    assert grade(q("time", "12:01", 1), "11:59 ... no, 12:00")["correct"] is False  # first time found is used
    assert grade(q("time", "12:00", 1), "0:59")["correct"] is False
    assert grade(q("time", "12:00", 1), "11:59")["correct"]


def test_exact_needs_single_choice():
    c = ["Apples", "Pears", "Plums"]
    assert grade(q("exact", "Pears", choices=c), "Pears")["correct"]
    assert grade(q("exact", "Pears", choices=c), "The tallest bar is Pears.")["correct"]
    assert not grade(q("exact", "Pears", choices=c), "Pears or Plums")["correct"]
    assert not grade(q("exact", "Pears", choices=c), "Apples")["correct"]
    assert grade(q("exact", "Pears", choices=c), "Pears")["mode"] == "correct"
    assert grade(q("exact", "Pears", choices=c), "no idea")["mode"] == "unparseable"


def test_ordering():
    c = ["A1", "B2", "C3", "D4"]
    assert grade(q("ordering", ["B2", "A1", "C3"], choices=c), "B2, A1, C3")["correct"]
    assert not grade(q("ordering", ["B2", "A1", "C3"], choices=c), "A1, B2, C3")["correct"]


def test_sweep_groups_share_content(tmp_path):
    import json
    from vtf.sweep import sweep
    sweep(tmp_path, master=5, bases=1)
    items = [json.loads(l) for l in (tmp_path / "items.jsonl").read_text().splitlines()]
    groups = {}
    for it in items:
        groups.setdefault((it["family"], it["render"]["sweep_base"]), []).append(it)
    for g in groups.values():
        assert len({json.dumps(i["spec"], sort_keys=True) for i in g}) == 1
        assert len({json.dumps(i["question"], sort_keys=True) for i in g}) <= 2  # tolerance may differ
        assert len({json.dumps(i["question"]["answer"]) for i in g}) == 1
        assert len({json.dumps(i["knobs"], sort_keys=True) for i in g}) == len(g)
    res = validate(tmp_path, 5)
    assert res["problems"] == []


def test_month_names():
    c = ["Jan", "Feb", "Mar"]
    assert grade(q("exact", "Feb", choices=c), "February")["correct"]
    assert grade(q("exact", "Feb", choices=c), "It peaks in February.")["correct"]
    assert not grade(q("exact", "Feb", choices=c), "March")["correct"]
