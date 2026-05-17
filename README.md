# Rule-Gating AI Hallucination Experiment

This repository contains a small controlled experiment testing whether
rule-gating reduces a common AI-agent failure: answering before the source of
truth is actually in context.

The experiment asks a model to write an 18-scene story plan using only an
approved character roster. In the control condition, the roster is available
somewhere in the rules, but the model must choose to read or use it. In the
gated conditions, the roster is placed directly into context before the model
answers.

## Headline Result

In the main "unlimited files" study, the model was allowed to read as many rule
files as it wanted before answering.

| Study | Model | No gate | Rule pasted in | Token gate |
| --- | --- | ---: | ---: | ---: |
| Unlimited files | DeepSeek V4 Flash | 90.0% drift | 0.0% | 0.3% |
| Unlimited files | Claude Opus 4.7 Medium | 90.0% drift | 15.3% | 15.0% |

Rule-gating does not make models hallucination-proof. It reduces one common
cause of hallucination: answering before the source-of-truth rule is in the
model's context.

## What's Included

- `run_experiment.py` - the experiment harness.
- `demo/index.html` - self-contained public HTML demo.
- `results/` - raw outputs, summaries, configs, rule files, and authority files.
- `docs/method.md` - experiment design.
- `docs/results.md` - readable results and interpretation.
- `docs/reproduce.md` - how to rerun the tests.

## Quickstart

The harness uses only Python standard-library modules.

```bash
cp .env.example .env
# Add DEEPSEEK_API_KEY or OPENROUTER_API_KEY to .env.

python3 run_experiment.py --help
```

Run a small smoke test:

```bash
python3 run_experiment.py \
  --provider deepseek \
  --model deepseek-v4-flash \
  --scenario rule_overload_unlimited \
  --runs 1 \
  --out-dir results/my-smoke-test
```

Run the main DeepSeek study:

```bash
python3 run_experiment.py \
  --provider deepseek \
  --model deepseek-v4-flash \
  --scenario rule_overload_unlimited \
  --runs 20 \
  --out-dir results/my-deepseek-unlimited-20
```

Run the Opus study through OpenRouter:

```bash
python3 run_experiment.py \
  --provider openrouter \
  --model anthropic/claude-opus-4.7 \
  --reasoning-effort medium \
  --scenario rule_overload_unlimited \
  --runs 20 \
  --out-dir results/my-opus-unlimited-20
```

## Integrity Notes

- Every published run has its raw model output saved under `results/*/raw/`.
- Scoring is deterministic.
- Drift means a scene used a character outside the approved roster, omitted
  characters, or produced unusable output.
- Malformed JSON is counted as drift because a downstream pipeline could not
  safely validate or use it.
- The token is enforcement/audit proof, not model intelligence. The accuracy
  gain mostly comes from forcing the source-of-truth rule into context.

