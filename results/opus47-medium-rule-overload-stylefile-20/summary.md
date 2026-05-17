# Context Gate Experiment Results

| Arm | Runs | Mean drift | Stddev | Variance | Invalid JSON | Scene count errors | Receipt errors | Tool reads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| control | 20 | 1.000 | 0.000 | 0.000 | 0 | 0 | 0 | 20 |
| force_feed | 20 | 0.156 | 0.355 | 0.126 | 3 | 0 | 0 | 0 |
| Context Gate | 20 | 0.108 | 0.298 | 0.089 | 2 | 0 | 0 | 0 |

Drift means: a scene listed a character outside the rulebook, or omitted characters entirely.
Suspicious fantasy words in descriptions are tracked in summary.json but not counted as character drift.
