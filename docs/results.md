# Results

All studies used 20 runs per arm.

## Main Study: Unlimited Files

The model could read as many rule files as it wanted before answering.

| Model | Arm | Mean drift | Stddev | Notes |
| --- | --- | ---: | ---: | --- |
| DeepSeek V4 Flash | No gate | 90.0% | 30.0% | Passed 2/20 runs |
| DeepSeek V4 Flash | Rule pasted in | 0.0% | 0.0% | Passed 20/20 |
| DeepSeek V4 Flash | Context Gate | 0.3% | 1.2% | One tiny exact-name typo |
| Claude Opus 4.7 Medium | No gate | 90.0% | 30.0% | Passed 2/20 runs |
| Claude Opus 4.7 Medium | Rule pasted in | 15.3% | 35.6% | 3 malformed JSON runs counted as drift |
| Claude Opus 4.7 Medium | Context Gate | 15.0% | 35.7% | 3 malformed JSON runs counted as drift |

In the no-gate runs, both models opened the source-of-truth file only 2 out of
20 times.

## Secondary Study: One File Only

The model could inspect only one rule file before answering.

| Model | Arm | Mean drift | Stddev | Notes |
| --- | --- | ---: | ---: | --- |
| DeepSeek V4 Flash | No gate | 100.0% | 0.0% | Opened the correct roster file 0/20 times |
| DeepSeek V4 Flash | Rule pasted in | 0.0% | 0.0% | Passed 20/20 |
| DeepSeek V4 Flash | Context Gate | 0.0% | 0.0% | Passed 20/20 |
| Claude Opus 4.7 Medium | No gate | 100.0% | 0.0% | Opened the correct roster file 0/20 times |
| Claude Opus 4.7 Medium | Rule pasted in | 15.6% | 35.5% | 3 malformed JSON runs counted as drift |
| Claude Opus 4.7 Medium | Context Gate | 10.8% | 29.8% | 2 malformed JSON runs counted as drift |

## Pressure Study: Rushed

The model was told this was a timed first draft and that file reads cost time.

| Model | Arm | Mean drift | Stddev |
| --- | --- | ---: | ---: |
| DeepSeek V4 Flash | No gate | 100.0% | 0.0% |
| DeepSeek V4 Flash | Rule pasted in | 0.0% | 0.0% |
| DeepSeek V4 Flash | Context Gate | 0.0% | 0.0% |

## Interpretation

The main pattern is not that Context Gates make models perfect. The main pattern
is that the ungated model often does not get the source-of-truth rule into
context, even when it is allowed to inspect the rule folder.

Force-feeding the source of truth sharply reduces drift. The Context Receipt
adds enforcement and auditability: a downstream step can refuse to continue
unless the gate was passed.

Opus is an important honesty check. It confirms the control failure, but still
has some malformed-output and exact-name failures after the rule is pasted in.
So the defensible claim is:

> Context Gates reduce one common cause of hallucination: answering before the
> source of truth is in context.
