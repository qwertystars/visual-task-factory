# Results

Full reports for both sets, copied from the generated reports. Every number below comes from the bench; nothing is rounded by hand.

## Main set


Dataset: 360 items, 8 families x 3 difficulties, master seed 7.
Validation: 360 items re-checked; answer re-derivation 360/360 agree; render probes 360/360 pass; byte-identical regeneration 360/360.

### Accuracy by model

| model | overall | easy | medium | hard | unparseable | median latency |
|---|---|---|---|---|---|---|
| oracle | 100% | 100% | 100% | 100% | 0 | 0.0s |
| random | 10% | 11% | 10% | 8% | 0 | 0.0s |
| qwen2.5-vl-3b | 61% | 71% | 57% | 55% | 0 | 8.97s |
| gemma3-4b | 47% | 57% | 44% | 41% | 1 | 18.49s |
| smolvlm2-2.2b | 45% | 58% | 43% | 32% | 2 | 6.14s |

### Accuracy by family

| family | oracle | random | qwen2.5-vl-3b | gemma3-4b | smolvlm2-2.2b |
|---|---|---|---|---|---|
| bar_chart | 100% | 9% | 78% | 62% | 56% |
| clock | 100% | 0% | 7% | 0% | 7% |
| grid_path | 100% | 13% | 27% | 22% | 38% |
| line_chart | 100% | 18% | 91% | 49% | 47% |
| pie_chart | 100% | 27% | 87% | 64% | 62% |
| receipt | 100% | 2% | 84% | 80% | 60% |
| shapes | 100% | 2% | 64% | 49% | 56% |
| table | 100% | 7% | 51% | 51% | 33% |

### Question types (real models)

| family/question | qwen2.5-vl-3b | gemma3-4b | smolvlm2-2.2b | n |
|---|---|---|---|---|
| bar_chart/count_above | 56% | 67% | 67% | 9 |
| bar_chart/diff | 100% | 25% | 12% | 8 |
| bar_chart/shortest | 100% | 86% | 71% | 7 |
| bar_chart/tallest | 71% | 71% | 86% | 7 |
| bar_chart/top3 | 50% | 0% | 0% | 4 |
| bar_chart/value_of | 80% | 90% | 70% | 10 |
| clock/minutes_to_hour | 22% | 0% | 0% | 9 |
| clock/time | 3% | 0% | 8% | 36 |
| grid_path/path_len | 12% | 12% | 17% | 24 |
| grid_path/reachable | 88% | 62% | 88% | 8 |
| grid_path/walls | 15% | 15% | 46% | 13 |
| line_chart/crossings | 57% | 0% | 0% | 7 |
| line_chart/highest_at | 100% | 85% | 85% | 13 |
| line_chart/peak_month | 100% | 22% | 44% | 9 |
| line_chart/value_at | 94% | 56% | 38% | 16 |
| pie_chart/largest | 82% | 71% | 71% | 17 |
| pie_chart/share_of | 89% | 53% | 53% | 19 |
| pie_chart/smallest | 89% | 78% | 67% | 9 |
| receipt/line_total | 100% | 88% | 82% | 17 |
| receipt/priciest | 62% | 75% | 25% | 8 |
| receipt/total | 100% | 100% | 100% | 11 |
| receipt/units | 56% | 44% | 0% | 9 |
| shapes/count_color | 100% | 33% | 33% | 3 |
| shapes/count_combo | 91% | 73% | 82% | 11 |
| shapes/count_kind | 11% | 22% | 33% | 9 |
| shapes/largest_color | 100% | 33% | 67% | 3 |
| shapes/leftmost_kind | 62% | 62% | 69% | 13 |
| shapes/total | 67% | 33% | 17% | 6 |
| table/col_sum | 20% | 0% | 0% | 10 |
| table/count_gt | 17% | 17% | 33% | 12 |
| table/lookup | 100% | 100% | 77% | 13 |
| table/row_max | 60% | 80% | 10% | 10 |

### Knobs that hurt most

Accuracy for each value of a difficulty knob, within one family (largest spread first; groups of 3 or more items).

**qwen2.5-vl-3b**

- bar_chart / label_rotation: 0: 86% (n=22), 30: 100% (n=8), 45: 100% (n=3), 60: 40% (n=5), 90: 43% (n=7)
- pie_chart / n_slices: 3: 100% (n=9), 4: 100% (n=13), 5: 100% (n=4), 6: 80% (n=10), 7: 50% (n=8), 8: 100% (n=1)
- pie_chart / colors: "distinct": 97% (n=35), "shades": 50% (n=10)
- pie_chart / labels: "legend": 60% (n=15), "name": 100% (n=15), "pct": 100% (n=15)
- pie_chart / start_angle: 0: 62% (n=8), 135: 100% (n=6), 45: 71% (n=7), 90: 96% (n=24)
- bar_chart / gridlines: false: 53% (n=15), true: 90% (n=30)
- bar_chart / near_tie: false: 90% (n=30), true: 53% (n=15)
- bar_chart / size: [5.6, 4.2]: 53% (n=15), [6.4, 4.8]: 90% (n=30)

**gemma3-4b**

- pie_chart / start_angle: 0: 12% (n=8), 135: 83% (n=6), 45: 29% (n=7), 90: 88% (n=24)
- pie_chart / labels: "legend": 33% (n=15), "name": 60% (n=15), "pct": 100% (n=15)
- pie_chart / n_slices: 3: 100% (n=9), 4: 77% (n=13), 5: 50% (n=4), 6: 40% (n=10), 7: 50% (n=8), 8: 0% (n=1)
- shapes / n_colors: 3: 73% (n=15), 5: 53% (n=15), 8: 20% (n=15)
- pie_chart / colors: "distinct": 74% (n=35), "shades": 30% (n=10)
- shapes / background: "noise": 20% (n=15), "plain": 63% (n=30)
- shapes / overlap: false: 63% (n=30), true: 20% (n=15)
- bar_chart / colors: "distinct": 70% (n=23), "shades": 29% (n=7), "single": 67% (n=15)

**smolvlm2-2.2b**

- pie_chart / n_slices: 3: 100% (n=9), 4: 92% (n=13), 5: 75% (n=4), 6: 20% (n=10), 7: 25% (n=8), 8: 0% (n=1)
- pie_chart / labels: "legend": 20% (n=15), "name": 73% (n=15), "pct": 93% (n=15)
- pie_chart / colors: "distinct": 77% (n=35), "shades": 10% (n=10)
- bar_chart / label_rotation: 0: 59% (n=22), 30: 62% (n=8), 45: 0% (n=3), 60: 60% (n=5), 90: 57% (n=7)
- line_chart / n_series: 2: 59% (n=22), 3: 53% (n=15), 4: 0% (n=8)
- bar_chart / colors: "distinct": 61% (n=23), "shades": 14% (n=7), "single": 67% (n=15)
- pie_chart / start_angle: 0: 38% (n=8), 135: 67% (n=6), 45: 29% (n=7), 90: 79% (n=24)
- grid_path / n: 10: 27% (n=15), 5: 67% (n=15), 7: 20% (n=15)


## Sweep set


Dataset: 184 items, 6 families x 3 difficulties, master seed 99.
Validation: 184 items re-checked; answer re-derivation 184/184 agree; render probes 184/184 pass; byte-identical regeneration 184/184.

### Accuracy by model

| model | overall | easy | medium | hard | unparseable | median latency |
|---|---|---|---|---|---|---|
| oracle | 100% | n/a | 100% | n/a | 0 | 0.0s |
| random | 7% | n/a | 7% | n/a | 0 | 0.0s |
| qwen2.5-vl-3b | 55% | n/a | 55% | n/a | 0 | 9.71s |
| gemma3-4b | 40% | n/a | 40% | n/a | 0 | 21.47s |
| smolvlm2-2.2b | 28% | n/a | 28% | n/a | 3 | 6.83s |

### Accuracy by family

| family | oracle | random | qwen2.5-vl-3b | gemma3-4b | smolvlm2-2.2b |
|---|---|---|---|---|---|
| bar_chart | 100% | 15% | 90% | 60% | 45% |
| clock | 100% | 0% | 0% | 0% | 0% |
| pie_chart | 100% | 33% | 78% | 61% | 44% |
| receipt | 100% | 0% | 81% | 69% | 53% |
| shapes | 100% | 0% | 42% | 0% | 8% |
| table | 100% | 0% | 50% | 39% | 14% |

### Question types (real models)

| family/question | qwen2.5-vl-3b | gemma3-4b | smolvlm2-2.2b | n |
|---|---|---|---|---|
| bar_chart/count_above | 100% | 43% | 86% | 7 |
| bar_chart/diff | 67% | 50% | 0% | 6 |
| bar_chart/tallest | 100% | 86% | 57% | 7 |
| bar_chart/top3 | 67% | 0% | 0% | 6 |
| bar_chart/value_of | 100% | 86% | 57% | 14 |
| clock/time | 0% | 0% | 0% | 42 |
| pie_chart/largest | 100% | 100% | 67% | 3 |
| pie_chart/share_of | 67% | 67% | 50% | 12 |
| pie_chart/smallest | 100% | 0% | 0% | 3 |
| receipt/line_total | 100% | 75% | 92% | 12 |
| receipt/priciest | 83% | 67% | 17% | 12 |
| receipt/total | 100% | 100% | 100% | 6 |
| receipt/units | 17% | 33% | 0% | 6 |
| shapes/count_color | 38% | 0% | 12% | 8 |
| shapes/count_kind | 0% | 0% | 0% | 2 |
| shapes/total | 100% | 0% | 0% | 2 |
| table/col_sum | 0% | 0% | 0% | 18 |
| table/count_gt | 100% | 33% | 0% | 6 |
| table/lookup | 100% | 100% | 42% | 12 |

### Knobs that hurt most

Accuracy for each value of a difficulty knob, within one family (largest spread first; groups of 3 or more items).

**qwen2.5-vl-3b**

- bar_chart / n_bars: 6: 100% (n=14), 7: 90% (n=20), 8: 67% (n=6)
- pie_chart / labels: "legend": 67% (n=6), "name": 67% (n=6), "pct": 100% (n=6)
- pie_chart / n_slices: 4: 78% (n=9), 5: 67% (n=6), 6: 100% (n=3)
- pie_chart / start_angle: 0: 67% (n=6), 135: 67% (n=6), 45: 100% (n=6)
- receipt / items: 5: 67% (n=6), 6: 100% (n=6), 7: 79% (n=24)
- table / rows: 6: 67% (n=18), 8: 33% (n=18)
- bar_chart / label_rotation: 0: 75% (n=12), 30: 100% (n=16), 45: 83% (n=6), 90: 100% (n=6)
- receipt / blur: 0.0: 75% (n=24), 0.8: 100% (n=6), 1.5: 83% (n=6)

**gemma3-4b**

- table / rows: 6: 67% (n=18), 8: 11% (n=18)
- pie_chart / n_slices: 4: 56% (n=9), 5: 50% (n=6), 6: 100% (n=3)
- bar_chart / label_rotation: 0: 33% (n=12), 30: 81% (n=16), 45: 67% (n=6), 90: 50% (n=6)
- receipt / skew_deg: -3.0: 67% (n=6), 0.0: 79% (n=24), 3.0: 33% (n=6)
- receipt / items: 5: 83% (n=6), 6: 100% (n=6), 7: 58% (n=24)
- pie_chart / labels: "legend": 50% (n=6), "name": 50% (n=6), "pct": 83% (n=6)
- pie_chart / start_angle: 0: 83% (n=6), 135: 50% (n=6), 45: 50% (n=6)
- receipt / blur: 0.0: 67% (n=24), 0.8: 67% (n=6), 1.5: 83% (n=6)

**smolvlm2-2.2b**

- pie_chart / labels: "legend": 0% (n=6), "name": 50% (n=6), "pct": 83% (n=6)
- receipt / items: 5: 33% (n=6), 6: 100% (n=6), 7: 46% (n=24)
- bar_chart / n_bars: 6: 50% (n=14), 7: 55% (n=20), 8: 0% (n=6)
- bar_chart / label_rotation: 0: 25% (n=12), 30: 69% (n=16), 45: 33% (n=6), 90: 33% (n=6)
- pie_chart / n_slices: 4: 44% (n=9), 5: 33% (n=6), 6: 67% (n=3)
- pie_chart / start_angle: 0: 67% (n=6), 135: 33% (n=6), 45: 33% (n=6)
- table / rows: 6: 28% (n=18), 8: 0% (n=18)
- table / font_px: 10: 17% (n=6), 12: 17% (n=6), 15: 17% (n=18), 20: 0% (n=6)


### Controlled sweeps (same content, one knob changed)

Accuracy for each knob value; *flips* = groups where changing only this knob turned a right answer wrong or the reverse.

**qwen2.5-vl-3b**

| family / knob | value: accuracy | flips |
|---|---|---|
| bar_chart / gridlines | false: 100%, true: 83% | 1/6 |
| bar_chart / horizontal | false: 83%, true: 83% | 0/6 |
| bar_chart / label_rotation | 0: 83%, 30: 100%, 45: 83%, 90: 100% | 2/6 |
| bar_chart / value_labels | false: 100%, true: 67% | 2/6 |
| clock / minute_ticks | false: 0%, true: 0% | 0/6 |
| clock / numerals | "all": 0%, "none": 0%, "quarters": 0%, "roman": 0% | 0/6 |
| clock / second_hand | false: 0%, true: 0% | 0/6 |
| clock / similar_hands | false: 0%, true: 0% | 0/6 |
| pie_chart / labels | "legend": 67%, "name": 67%, "pct": 100% | 2/6 |
| receipt / blur | 0.0: 83%, 0.8: 100%, 1.5: 83% | 1/6 |
| receipt / ink | "dark": 83%, "faded": 83% | 0/6 |
| receipt / skew_deg | -3.0: 67%, 0.0: 83%, 3.0: 67% | 1/6 |
| shapes / background | "noise": 50%, "plain": 33% | 1/6 |
| table / font_px | 10: 50%, 12: 50%, 15: 50%, 20: 50% | 0/6 |
| table / rules | false: 50%, true: 50% | 0/6 |
| table / zebra | false: 50%, true: 50% | 0/6 |

**gemma3-4b**

| family / knob | value: accuracy | flips |
|---|---|---|
| bar_chart / gridlines | false: 50%, true: 67% | 1/6 |
| bar_chart / horizontal | false: 67%, true: 67% | 2/6 |
| bar_chart / label_rotation | 0: 50%, 30: 75%, 45: 67%, 90: 50% | 4/6 |
| bar_chart / value_labels | false: 67%, true: 67% | 2/6 |
| clock / minute_ticks | false: 0%, true: 0% | 0/6 |
| clock / numerals | "all": 0%, "none": 0%, "quarters": 0%, "roman": 0% | 0/6 |
| clock / second_hand | false: 0%, true: 0% | 0/6 |
| clock / similar_hands | false: 0%, true: 0% | 0/6 |
| pie_chart / labels | "legend": 50%, "name": 50%, "pct": 83% | 3/6 |
| receipt / blur | 0.0: 83%, 0.8: 67%, 1.5: 83% | 2/6 |
| receipt / ink | "dark": 83%, "faded": 83% | 2/6 |
| receipt / skew_deg | -3.0: 67%, 0.0: 83%, 3.0: 33% | 5/6 |
| shapes / background | "noise": 0%, "plain": 0% | 0/6 |
| table / font_px | 10: 50%, 12: 50%, 15: 33%, 20: 33% | 1/6 |
| table / rules | false: 33%, true: 33% | 0/6 |
| table / zebra | false: 33%, true: 33% | 0/6 |

**smolvlm2-2.2b**

| family / knob | value: accuracy | flips |
|---|---|---|
| bar_chart / gridlines | false: 50%, true: 50% | 0/6 |
| bar_chart / horizontal | false: 50%, true: 50% | 0/6 |
| bar_chart / label_rotation | 0: 50%, 30: 75%, 45: 33%, 90: 33% | 1/6 |
| bar_chart / value_labels | false: 33%, true: 50% | 3/6 |
| clock / minute_ticks | false: 0%, true: 0% | 0/6 |
| clock / numerals | "all": 0%, "none": 0%, "quarters": 0%, "roman": 0% | 0/6 |
| clock / second_hand | false: 0%, true: 0% | 0/6 |
| clock / similar_hands | false: 0%, true: 0% | 0/6 |
| pie_chart / labels | "legend": 0%, "name": 50%, "pct": 83% | 5/6 |
| receipt / blur | 0.0: 50%, 0.8: 50%, 1.5: 67% | 1/6 |
| receipt / ink | "dark": 50%, "faded": 50% | 0/6 |
| receipt / skew_deg | -3.0: 50%, 0.0: 50%, 3.0: 50% | 2/6 |
| shapes / background | "noise": 17%, "plain": 0% | 1/6 |
| table / font_px | 10: 17%, 12: 17%, 15: 17%, 20: 0% | 1/6 |
| table / rules | false: 17%, true: 17% | 0/6 |
| table / zebra | false: 17%, true: 17% | 0/6 |

