# Spec Review (Stage 1.5) and SPEC_REVIEW.md (`spec-review/v1`)

The spec writer cannot review its own spec: it holds the whole clarification conversation, so it reads into the text what the text does not say. Before the plan is written, a fresh reviewer that sees only the written artifacts and the codebase try to break the spec. A test writer and a builder will later see exactly what this reviewer sees, so a gap it finds is a gap those subagents would have hit.

## Reviewer

Spawn one read-only subagent with a fresh context: never fork the spec writer's conversation into it. It reviews the spec through each of the four lenses below in turn and tags every finding with the lens that raised it. One reviewer instead of four keeps token cost down; working the lenses as separate passes keeps each one from being skipped.

| Lens | Looks for |
| --- | --- |
| **Naive reader** | Terms, IDs, acronyms, and data names used without definition; anything that only makes sense with the clarification conversation; a Verification matrix row a test writer could not turn into a test without asking |
| **Critic** | Contradictions between REQs, contracts, Non-goals, and project rules; a REQ with an obvious boundary and no `edge` row; a failure path with no `error` row; a `Then` that is not one observable result; missing authorization or information-exposure rules; REQs written as tasks instead of outcomes |
| **Simplicity** | REQs that `Problem and outcome` does not need; non-functional targets or configuration the user never asked for; behavior that restates a component in `Components used` or rebuilds something the codebase already has (search before saying it does not exist) |
| **Codebase checker** | Every path, symbol, endpoint, table, field, `DESIGN.md` token, and component REQ the spec names exists, or the spec marks it as new; claims about current behavior are true; new contracts follow the conventions of the existing ones |

### Brief

The brief is the reviewer's only context. It names:

- the spec folder and the files to read: `SPEC.md`, `UI.md` and contract files when present, the specs listed under `Components used`, the root `DESIGN.md` when `UI.md` exists, and the project rules (`CONSTITUTION.md`, `AGENTS.md`/`CLAUDE.md`, stack skills, whichever exist);
- the whole lens table above, with the instruction to work through every lens;
- on a second pass, the sections that changed and the findings already resolved, which it must not raise again;
- this closing line: "Write nothing. Return the verdict first (`pass` when you have no blocker or major finding, otherwise `fail`), then one entry per finding: lens, severity, scope (section and REQ or matrix row), the finding, evidence (a quote or `path:line`), and a suggested fix."

Never put the clarification conversation, the user's answers, your summary of the request, or your opinion of the spec in the brief. Decisions the user made are already written into the spec; if a reviewer cannot find one there, that is a finding.

### Severity

| Severity | Meaning |
| --- | --- |
| `blocker` | A test writer or builder would build the wrong thing or must guess: a contradiction, a false claim about the code, a missing contract, an undefined term a REQ depends on |
| `major` | A missing `edge` or `error` row, an ambiguity a reasonable reader could resolve either way, scope the problem does not need |
| `nit` | Wording or clarity that does not change what gets built |

## Triage

The spec writer copies the reviewer's findings into `SPEC_REVIEW.md`, removing duplicates and keeping the lens names in the Reviewer column, then resolves each one:

| Resolution | When | Notes column |
| --- | --- | --- |
| `fixed` | The finding is right; the spec was edited | What changed |
| `contested` | The finding is wrong | Evidence that the spec is right: a quote from the spec or `path:line` in the code. "Not needed" is not evidence |
| `declined` | A `nit` that is not worth changing (nits only) | Why |
| `open` | Not resolved yet | — |

When a fix needs a product decision, ask the user in the next clarification round ([spec-format.md](spec-format.md#clarification-rules)); the finding stays `open` until the answer is written into the spec. Never drop a finding silently and never fix one by adding an assumption.

## Second pass

If any `blocker` or `major` was `fixed`, spawn one fresh reviewer on the edited spec with only the naive reader and simplicity lenses. Its brief lists the changed sections and the resolved findings. It checks that the fixes are clear and did not add defensive scope the problem does not need. Run at most two extra passes; anything still `open` after that goes to the user at Gate 1 as an open question.

## Gate

The review passes when no `blocker` or `major` is `open`. Then write the plan. At Gate 1, report the counts per severity and list every `contested` finding with its evidence, so the user can overrule it.

A spec edited after Gate 1 is reviewed again before reapproval, on the changed REQs only, unless the change is a patch.

## Template

Append one `## Pass N` section per pass; never rewrite an earlier pass.

````markdown
---
format: spec-review/v1
spec: "NNN"
spec_version: 0.1.0
date: YYYY-MM-DD
verdict: pass
---

# NNN Spec review

## Pass 1 (spec 0.1.0)

Reviewer lenses: naive reader, critic, simplicity, codebase checker.

| ID | Reviewer | Severity | Scope | Finding | Resolution | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| F01 | naive reader | blocker | REQ-03 | "MaxDate" is never defined | fixed | Defined in Problem and outcome |
| F02 | simplicity | major | REQ-07 | CSV export is not needed by the stated problem | contested | User asked for it: Problem and outcome, paragraph 2 |
| F03 | critic | nit | Matrix REQ-02 edge | "Then" says "shows correctly" | fixed | Now names the rendered text |
````

Frontmatter `spec_version` is the `SPEC.md` version the latest pass reviewed. `verdict` is `pass` only when no `blocker` or `major` is `open`. Finding IDs (`F` + two or more digits) continue across passes and are never reused.
