# Blog Outline

## Working Title

Rule Gates: A Small Experiment in Reducing AI Agent Hallucinations

## Thesis

Many AI hallucinations start before the answer: the model skips the source of
truth, then fills in the blank. Rule-gating reduces that failure by forcing the
relevant rule into context before the model acts.

## Narrative

1. Real production problem: an AI pipeline had long rules and protocols, but the
   agent sometimes skipped the source-of-truth file and invented plausible
   details.
2. Why more rules were not enough: adding rules does not help if the model does
   not load or attend to them.
3. Candidate solutions:
   - More explicit instructions.
   - Louder prompts.
   - Post-hoc validation.
   - Rule-gating.
4. Rule-gating design:
   - Force the right authority file into context.
   - Issue a one-use token.
   - Downstream validation refuses to continue without the token.
5. Experiment:
   - Three arms.
   - 20 runs per arm.
   - Deterministic scorer.
   - Raw outputs saved.
6. Results:
   - Pressure study.
   - Unlimited-files study.
   - One-file study.
7. Honest conclusion:
   - Rule-gating does not make models perfect.
   - It reduces missed-rule hallucinations.
   - The token is enforcement and audit, not intelligence.

