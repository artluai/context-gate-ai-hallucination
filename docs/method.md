# Method

## Question

Do Context Gates reduce hallucination-like drift in an AI agent step?

This experiment focuses on one specific failure mode: the source-of-truth rule
exists, but the model answers before that rule is actually in context.

## Task

The model writes an 18-scene illustrated story plan for a fantasy rescue story.
Every scene must list the characters that appear.

The approved character roster contains exactly five registered names:

- `mara_the_cartographer`
- `tin_fox`
- `oracle_lamp`
- `sleeping_tax_collector`
- `glass_diver`

Any scene that uses another character name, omits characters, or cannot be
parsed safely is counted as drift.

## Arms

The experiment has three arms:

| Arm | Meaning |
| --- | --- |
| No gate | The model is told the rule exists and may inspect rules itself. |
| Rule pasted in | The approved roster is pasted directly into the prompt. |
| Context Gate | The approved roster is pasted into context and the output must include a one-use Context Receipt. |

The Context Gate arm tests enforcement and auditability. The force-feed arm
tests whether the main accuracy gain comes from putting the source of truth into
context. Internally, the harness still names this arm `token_gate` because that
was the original experiment label.

## Scenarios

### Unlimited files

The model sees a rule-folder index and may read as many rule files as it wants.
This is the primary public study because it answers the objection: "Why not just
let the model read all the files?"

### One file only

The model sees the rule-folder index but may inspect only one file. This is a
harsher diagnostic study that makes the file-selection failure easier to see.

### Rushed

The model is placed under speed pressure and told a file read costs time. This
was an early pressure test. It is useful context, but the unlimited-files study
is the more defensible headline result.

## Scoring

The scorer is deterministic and implemented in `run_experiment.py`.

A scene fails if:

- `characters` is missing or empty.
- Any listed character is not in the approved roster.
- The output is not parseable as a JSON object.

The reported drift rate is:

```text
invalid scenes / 18
```

Malformed JSON is treated as full drift because the downstream system cannot
safely validate or use it.
