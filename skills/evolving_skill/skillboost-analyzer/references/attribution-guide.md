# Attribution guide

## Find the causal decision

Start at the final outcome and walk backward until finding the earliest decision that made the failure likely. Then test whether the skill could reasonably control that decision.

Evidence strength, from strongest to weakest:

1. an explicit trace statement or tool result;
2. a missing mandatory action visible in the trace;
3. repeated behavior across cases with the same instruction path;
4. inference from the final output alone.

Use weaker evidence only with lower confidence and preserve competing hypotheses.

## Defect-class tests

- **Missing strategy:** no incumbent instruction applies, and a reusable procedure can be stated without encoding answers.
- **Ambiguous strategy:** the trace follows a plausible reading of existing text that permits the wrong action.
- **Overbroad strategy:** an instruction is applied in a case satisfying its wording but outside its intended scope.
- **Broken control flow:** the right rule exists but a required check is unreachable, unordered, or optional in practice.
- **Knowledge gap:** a stable fact or formal method is absent; merely failing to retrieve available information is not a knowledge gap.
- **Output contract:** the internal conclusion is correct but parsing or serialization fails.
- **Capability gap:** targeted instruction changes repeatedly fail at the same causal step, or the step requires decomposition/tooling beyond declarative guidance.

## Confounders

Before blaming the skill, rule out truncation, timeouts, unavailable tools, stochastic evaluator behavior, prompt-template changes, dataset drift, and unsupported labels. Do not merge these into a strategy cluster.

## Cluster rule

Cases belong in one repair item only if a single skill edit could plausibly fix all of them. Shared topic, answer type, or benchmark category is insufficient.

