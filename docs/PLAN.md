# Plan: Visual Task Factory

## Goal
Generate synthetic images with questions whose answers are known by construction, grade any vision model against them, and show where models fail by task family and difficulty.

## Core rule
The answer comes from the seeded spec, never from a model. Every item is checked three ways before it enters a dataset:
1. **Generator answer**: computed while building the spec.
2. **Independent re-derivation**: a separate verifier module recomputes the answer from the spec with different code.
3. **Render self-check**: pixel probes on the saved image confirm the picture shows what the spec says (bar tops where expected, hand angles, cell colours, shape centres). Items that are ambiguous at the rendered resolution (near-ties under one pixel, overlapping labels) are rejected and regenerated.

## Task families and difficulty knobs
| Family | Questions | Knobs |
|---|---|---|
| bar_chart | tallest/shortest bar, value of a bar, count above a threshold, difference | bar count, near-tie gap, label rotation, horizontal, similar colours, gridlines |
| line_chart | highest series at x, value at x, number of crossings | series count, noise, markers on/off, legend placement |
| pie_chart | largest slice, share of a slice | slice count, near-equal slices, labels inside/legend only |
| shapes | count by colour/shape, relative position, which shape is largest | object count, overlap, distractor colours, size spread |
| clock | read the time | numerals on/off, second hand, hand length similarity, rotation of dial |
| table | cell lookup, column sum, row with max | rows/cols, font size, zebra stripes, noise |
| receipt | total, item count, price of an item | items, font size, skew, blur, discount lines |
| grid_path | shortest path length, count of obstacles | grid size, obstacle density |

## Checkers
exact (normalised text), numeric (absolute or relative tolerance), set (order-free), ordering (sequence), time (minutes with tolerance).

## Pipeline
`vtf generate` -> `vtf verify` -> `vtf run` (OpenAI-compatible endpoint, e.g. llama.cpp server) -> `vtf grade` -> `vtf report` (HTML + Markdown, failure maps by family x difficulty, knob effects, sample failures).

## Models (free only)
llama.cpp CPU server on a 16-core CPU with small vision GGUFs: Qwen2.5-VL 3B, SmolVLM2 2.2B, Gemma 3 4B. Baselines: oracle (reads spec, must score 100%) and random-guess (lower bound), which test the grader itself.
