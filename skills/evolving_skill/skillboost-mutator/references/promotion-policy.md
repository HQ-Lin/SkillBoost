# Promotion policy

Declare the policy before candidate evaluation.

## Phase A: directed screen

Use the incumbent's complete failed and undecided set for the entire version cycle. Optionally add a deterministic sample of incumbent-correct cases. Rank all candidates with the same metric direction and advance a fixed top `K`.

Phase A answers only: “Which hypotheses deserve full evaluation?” It cannot establish general improvement.

## Phase B: full-set gates

A candidate is eligible only if:

- primary improvement meets `min_improvement`;
- completion meets `min_completion`;
- case-level regression remains below `max_case_regression`;
- every protected slice stays within `max_slice_regression`;
- structural validation passes;
- configured token, latency, and skill-growth budgets pass.

When the primary metric is minimized, all improvement and regression calculations must reverse direction consistently.

## Tie-breaking

Choose a tie-breaker before evaluation. Recommended lexicographic order:

1. larger full-set primary improvement;
2. smaller worst-slice regression;
3. lower execution cost;
4. smaller skill growth;
5. fewer changed lines.

## Rejection

Retain the incumbent when no candidate passes. Store all candidate reports and explicit gate failures. Do not relabel the best rejected candidate as a promotion.
