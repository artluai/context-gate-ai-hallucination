# Rule Gate MVP Results

| Arm | Runs | Mean drift | Stddev | Variance | Invalid JSON | Scene count errors | Token errors | Tool reads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| control | 20 | 0.900 | 0.300 | 0.090 | 0 | 0 | 0 | 19 |
| force_feed | 20 | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 |
| token_gate | 20 | 0.003 | 0.012 | 0.000 | 0 | 0 | 0 | 0 |

Drift means: a scene listed a character outside the rulebook, or omitted characters entirely.
Suspicious fantasy words in descriptions are tracked in summary.json but not counted as character drift.
