# Method

SkillBoost models a task skill as a structured state \(s_t\) whose coordinates include metadata, workflow, constraints, and references. A targeted edit \(a_t\) produces the next candidate through the deterministic transition

\[
s_{t+1}=P(s_t,a_t).
\]

Each evolution round contains a forward rollout and a backward optimization phase.

## Forward rollout

For task \((q_i,y_i)\), a frozen LLM agent conditioned on \(s_t\) produces a step-level trajectory \(\tau_i\) and final answer \(\hat z_i\). Both successful and failed trajectories are retained so later edits can be evaluated against previously stable behavior.

## Structured exploitation

Failed trajectories are converted into an evidence-grounded diagnosis \(g_t\):

\[
g_t=\{(\operatorname{cause}_k,\operatorname{target}_k)\}_{k=1}^{K}.
\]

The analyzer performs three operations:

1. workflow-compliance checking;
2. backward reconstruction of the reasoning chain to the first causal deviation;
3. root-cause clustering by shared defect and editable target.

Strategy defects are routed to skill edits. Repeated capability gaps are routed to decomposition or sub-skills rather than additional prose.

## Prior-guided exploration

All candidates share diagnosis \(g_t\) but use different repair strategies \(\pi^{(n)}\):

\[
a_t^{(n)}=\operatorname{Generate}(s_t,g_t,\pi^{(n)}),\qquad n=1,\ldots,N.
\]

Strategies vary edit scope and repair priority. Conservative candidates change only directly supported defects; balanced candidates cover related failures; prior-extended candidates use the LLM's prior knowledge to generalize beyond the observed batch.

## Verified acceptance

For binary task outcomes,

\[
r(s')\propto \operatorname{Fix}(s')-\operatorname{Regress}(s').
\]

The selected candidate is

\[
n^*=\arg\max_n r(s_{t+1}^{(n)})
\quad\text{s.t.}\quad
r(s_{t+1}^{(n)})>0,\;
\operatorname{Regress}(s_{t+1}^{(n)})<\epsilon.
\]

If the feasible set is empty, the incumbent is retained.

## Best-of-N search

The paper's idealized analysis gives expected directional progress

\[
\mathbb E[\delta_t]\approx \epsilon\sqrt{\frac{2\ln N}{d}},
\]

showing logarithmically diminishing gains as the pool grows. The default experiment uses \(N=4\), screens all candidates on previous failures plus guard samples, and fully evaluates the top two candidates.

For the complete formulation, theorem, proofs, and experimental evidence, refer to the [paper](https://arxiv.org/abs/2607.26643).

