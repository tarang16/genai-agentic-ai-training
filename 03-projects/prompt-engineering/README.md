# PromptLab — prompt engineering, measured

A graded prompt-engineering project. Learners build **two prompts for every
task** — a fair control and an engineered version — run both over a **labelled
dataset**, and report the difference as a **number**.

## Why it is built this way

Most prompt-engineering material shows you a good prompt and asks you to admire
it. Nothing sticks, because you never watched the bad prompt lose.

Here every technique has to earn its place against a control:

| Task | Technique | How it is measured |
|---|---|---|
| 1 | Zero-shot | Rubric score (5 criteria × 0–2), LLM judge, rubric written by the learner |
| 2 | Few-shot | Classification accuracy + confusion matrix over 24 labelled tickets |
| 3 | Chain-of-thought | Numeric accuracy against ground truth **computed in Python** |
| 4 | Role prompting | Persona distinctiveness and question specificity, scored |
| 5 | Technique selection | Written, and required to cite the learner's own numbers |
| 6 | Cost | Tokens per approach — CoT is not free |

## Files

| File | Purpose |
|---|---|
| `PromptLab_Problem_Statement.ipynb` | The brief: six deliverables, a 100-mark rubric, six tasks with `TODO` stubs |
| `PromptLab_SOLUTION.ipynb` | Reference solution with working prompts, metrics and analysis |

Both notebooks share the same two datasets, defined in their setup cells — no
files to upload.

## The two datasets

**24 support tickets with gold labels** (8 Bug, 8 Feature Request, 8 Billing).
The company rule is deliberately not inferable from the category names:

| Ticket | Surface reading | Gold label |
|---|---|---|
| "Checkout page freezes when I click Pay Now" | Billing | **Bug** |
| "Change billing from monthly to annual" | Feature Request | **Billing** |
| "We want usage-based pricing instead of per-seat" | Billing | **Feature Request** |

That is the point: few-shot exists for rules that live inside a company rather
than inside the language. Zero-shot cannot guess them, and the confusion matrix
shows exactly where it fails.

**5 unit-economics scenarios** where `truth()` computes the exact answer:

```
LTV   = (price × (1 − discount) × gross_margin) / monthly_churn
ratio = LTV / CAC        healthy if ≥ 3.0
```

The base case scores 3.50 (healthy) and the same business with a 30% discount
scores 2.45 (unhealthy) — so the discount campaign genuinely flips the verdict,
which is the question the scenario asks. Verdicts across the five scenarios split
2 healthy / 3 unhealthy, so a model cannot score well by guessing one answer.

## What the solution demonstrates

- A **fair control** for every technique — the prompt a busy person really types,
  not a strawman
- Output normalisation before scoring, so you measure the prompt and not your parser
- Confusion matrices read by *direction of error*, not just headline accuracy
- A machine-readable `FINAL:` line so free-text answers can be scored at all
- Rubrics built from observable properties, because "is it good?" is not a rubric
- Token cost per approach, projected to weekly volume
- A prompt-injection test: a ticket containing *"ignore previous instructions"*,
  against both a naive and a delimiter-hardened prompt

## An honest note for instructors

`gpt-4o-mini` may well get all five unit-economics scenarios right **without**
chain-of-thought — the arithmetic is not hard. If that happens, the correct
report is *"CoT gave no lift at this difficulty and cost ~5× the output tokens"*,
and the solution notebook says so explicitly.

That is a feature. Students should learn that a technique is a hypothesis to
test, not a spell that always works. To make CoT earn its keep, raise the step
count — add a setup fee amortised over the lifetime, or a churn rate that changes
after month 6 — and watch the gap open.

The same applies to Task 1: the engineered brief prompt improves structure, tone
and **honesty about uncertainty**. It does not make the model's market figures
accurate, and the notebook is explicit that claiming otherwise is the most common
overstatement in prompt-engineering teaching.

## Source

Built on the five business scenarios in *Prompt Engineering: Practical Scenarios*
(zero-shot, few-shot, chain-of-thought, role prompting, technique selection),
extended from written-answer questions into a measurable, runnable project.
