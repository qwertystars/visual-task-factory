"""Frame builder for the demo video: size, scene list, duration, no dash characters, determinism."""

import importlib.util
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("render_demo_video", ROOT / "scripts" / "render_demo_video.py")
rdv = importlib.util.module_from_spec(_spec)
sys.modules["render_demo_video"] = rdv
_spec.loader.exec_module(rdv)

SCENES = ["title", "pipeline", "families", "showcase", "determinism", "verifier", "benchmark", "end"]


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    # A real run: generate twice, hash, validate and grade, on a small dataset.
    return rdv.collect(tmp_path_factory.mktemp("video"), seed=42, per_cell=1)


def test_collect_is_real(data):
    a, b = data["runs"]["a"], data["runs"]["b"]
    assert data["identical"] and a == b and len(a["digest"]) == 64
    assert data["n_families"] == 9 and data["n_items"] == 27
    assert {g["family"] for g in data["grid"]} >= {"receipt", "chart_table"}
    assert data["verifier"]["agree"]
    for g in data["grading"]:
        assert g["true_ok"] and not g["corrupt_ok"]
    assert data["results"]["by_model"][0][0] == "model"


def test_scene_list_and_duration(data):
    scenes = rdv.build_scenes(data)
    assert [s.name for s in scenes] == SCENES
    assert 60 <= rdv.total_seconds(scenes) <= 90


def test_frame_size(data):
    for sc in rdv.build_scenes(data):
        for st in sc.steps:
            assert rdv.render_step(st).size == (1920, 1080)


def test_no_dash_characters(data):
    texts = rdv.all_text(rdv.build_scenes(data))
    assert texts
    for t in texts:
        assert not any(c in t for c in "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), t


def test_benchmark_labelled_v1(data):
    texts = rdv.all_text(rdv.build_scenes(data))
    assert any("measured on v1 renderers" in t for t in texts)


def test_two_builds_give_identical_png_bytes(data):
    def build():
        return [rdv.png_bytes(rdv.render_step(st)) for sc in rdv.build_scenes(data) for st in sc.steps]
    assert build() == build()


def test_frame_count_matches_duration(data):
    scenes = rdv.build_scenes(data)[:2]
    n = sum(1 for _ in rdv.frames(scenes))
    assert n == round(rdv.total_seconds(scenes) * rdv.FPS)


def test_crossfade_is_between_steps(data):
    scenes = rdv.build_scenes(data)[:2]
    first = rdv.render_step(scenes[0].steps[0]).tobytes()
    second = rdv.render_step(scenes[1].steps[0]).tobytes()
    fr = list(rdv.frames(scenes))
    n0 = round(scenes[0].steps[0].seconds * rdv.FPS)
    assert fr[0] == first and fr[n0 - 1] == first
    assert fr[n0] not in (first, second) and fr[n0 + rdv.FADE] == second
    assert Image.frombytes("RGB", (1920, 1080), fr[n0]).size == (1920, 1080)
