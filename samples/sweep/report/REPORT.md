# Visual Task Factory: results

Dataset: 184 items, 6 families x 3 difficulties, master seed 99.
Validation: 184 items re-checked; answer re-derivation 184/184 agree; render probes 184/184 pass; byte-identical regeneration 184/184.

## Accuracy by model

| model | overall | easy | medium | hard | unparseable | median latency |
|---|---|---|---|---|---|---|
| oracle | 100% | n/a | 100% | n/a | 0 | 0.0s |
| random | 7% | n/a | 7% | n/a | 0 | 0.0s |
| qwen2.5-vl-3b | 55% | n/a | 55% | n/a | 0 | 9.71s |
| gemma3-4b | 40% | n/a | 40% | n/a | 0 | 21.47s |
| smolvlm2-2.2b | 28% | n/a | 28% | n/a | 3 | 6.83s |

## Accuracy by family

| family | oracle | random | qwen2.5-vl-3b | gemma3-4b | smolvlm2-2.2b |
|---|---|---|---|---|---|
| bar_chart | 100% | 15% | 90% | 60% | 45% |
| clock | 100% | 0% | 0% | 0% | 0% |
| pie_chart | 100% | 33% | 78% | 61% | 44% |
| receipt | 100% | 0% | 81% | 69% | 53% |
| shapes | 100% | 0% | 42% | 0% | 8% |
| table | 100% | 0% | 50% | 39% | 14% |

## Question types (real models)

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

## Knobs that hurt most

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


## Controlled sweeps (same content, one knob changed)

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

