# Context Gate Experiment Results

| Arm | Runs | Mean drift | Stddev | Variance | Invalid JSON | Scene count errors | Receipt errors | Tool reads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| control | 20 | 0.900 | 0.300 | 0.090 | 0 | 0 | 0 | 20 |
| force_feed | 20 | 0.153 | 0.356 | 0.127 | 3 | 0 | 0 | 0 |
| Context Gate | 20 | 0.150 | 0.357 | 0.128 | 3 | 0 | 0 | 0 |

Drift means: a scene listed a character outside the rulebook, or omitted characters entirely.
Suspicious fantasy words in descriptions are tracked in summary.json but not counted as character drift.
