# Reproduce the Experiment

## 1. Set Up an API Key

Create `.env` from the example:

```bash
cp .env.example .env
```

Open `.env` and add one or both keys:

```text
DEEPSEEK_API_KEY=...
OPENROUTER_API_KEY=...
```

Do not commit `.env`.

## 2. Smoke Test

```bash
python3 run_experiment.py \
  --provider deepseek \
  --model deepseek-v4-flash \
  --scenario rule_overload_unlimited \
  --runs 1 \
  --out-dir results/smoke-test
```

## 3. Rerun the Published Studies

### DeepSeek rushed

```bash
python3 run_experiment.py \
  --provider deepseek \
  --model deepseek-v4-flash \
  --scenario deadline \
  --runs 20 \
  --out-dir results/rerun-deepseek-deadline-20
```

### DeepSeek unlimited files

```bash
python3 run_experiment.py \
  --provider deepseek \
  --model deepseek-v4-flash \
  --scenario rule_overload_unlimited \
  --runs 20 \
  --out-dir results/rerun-deepseek-unlimited-20
```

### DeepSeek one file only

```bash
python3 run_experiment.py \
  --provider deepseek \
  --model deepseek-v4-flash \
  --scenario rule_overload \
  --runs 20 \
  --out-dir results/rerun-deepseek-onefile-20
```

### Opus unlimited files through OpenRouter

```bash
python3 run_experiment.py \
  --provider openrouter \
  --model anthropic/claude-opus-4.7 \
  --reasoning-effort medium \
  --scenario rule_overload_unlimited \
  --runs 20 \
  --out-dir results/rerun-opus-unlimited-20
```

### Opus one file only through OpenRouter

```bash
python3 run_experiment.py \
  --provider openrouter \
  --model anthropic/claude-opus-4.7 \
  --reasoning-effort medium \
  --scenario rule_overload \
  --runs 20 \
  --out-dir results/rerun-opus-onefile-20
```

## 4. Inspect Results

Each output folder contains:

- `summary.md` - readable table.
- `summary.json` - exact metrics.
- `raw/` - raw model outputs and scores for every run.
- `rules/` - rule files shown to the model.
- `authority.json` - approved roster.
- `config.json` - model, scenario, temperature, and run count.

## Cost Note

Costs vary by provider and model. The published Opus runs were more expensive
than DeepSeek. Start with `--runs 1` before running 20 trials per arm.

