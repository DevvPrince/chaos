---
name: spec-driven-development
description: Turn a feature request into an approved, versioned specification, then drive it through Locate → Specify → zero-context spec review → Plan → Test (Red) → Build (Green) → Audit → Full verification → Reconcile with traceable REQ IDs, happy/edge/error test cases, and one-run mini-batch tasks pipelined through parallel subagents (one test writer, builder, and auditor per task). Apply before new features, behavioral bug fixes, API/UI/event contract changes, feature migrations, authorization changes, and runtime-configuration behavior changes.
---

# Spec-Driven Development

The written specification is the contract; code is its compiled artifact. `specs/` holds one spec per feature and one per shared component; a change edits the spec that owns the behavior instead of adding a new one. Every spec lives in `specs/NNN-name/` and moves through the stages below. No agent grades its own work: the agent that writes implementation code never writes or edits the tests that judge it.

The skill is stack-agnostic. Each repository supplies its own rules: long-lived engineering laws (for example a root `CONSTITUTION.md`), operational and verification commands (`AGENTS.md`, `CLAUDE.md`, or the README), and stack skills for architecture, code, and test conventions. Read whichever exist before Stage 1; they override this skill's defaults and stay authoritative in their areas.

## The loop

| # | Stage | Role | Produces | Gate |
| --- | --- | --- | --- | --- |
| 0 | Locate | Spec writer | Owning spec(s) and the classification: edit feature, edit component, new feature, new component | Ask the user when the owner is unclear |
| 1 | Specify | Spec writer | `SPEC.md` (+ `UI.md`, contracts) | **Human Gate 1** (after stages 1.5 and 2): user approves spec, plan, and all batches |
| 1.5 | Review | One fresh read-only reviewer subagent; the spec writer triages | `SPEC_REVIEW.md` | No `blocker` or `major` finding `open` |
| 2 | Plan | Architect | `PLAN.md`, `TASKS.json` | Checker: schema, no cycles, every REQ covered |
| 3 | Test (Red) | Test-writer subagent, one per task | Failing tests tagged with REQ IDs | Each test fails for the missing behavior |
| 4 | Build (Green) | Builder subagent, one per task | Source code only | The task's red tests pass |
| 5 | Audit | Auditor subagent, one per task | Task section, appended to `AUDIT_REPORT.md` by the orchestrator | No spec drift, no weakened tests |
| 6 | Full verification | Orchestrator | `Full verification` section in `AUDIT_REPORT.md` | Full suite and project checks pass |
| 7 | Reconcile | Reconciler | Updated `SPEC.md` + PR summary | **Human Gate 2**: user reviews spec diff and code diff together |

Stages 3–5 run per task as an independent pipeline inside the development loop (workflow step 6); tasks in the same batch run in parallel. Roles, writable paths, and gate evidence are in [references/stages.md](references/stages.md).

## Required rules

0. **Find the owner before writing.** Read the `specs/README.md` index and classify the request as editing an existing feature or component spec, or creating a new one. If it is unclear, ask the user; never guess ([references/spec-catalog.md](references/spec-catalog.md)).
1. **Clarify until crystal clear.** Never leave Stage 1 with anything ambiguous; ask in rounds with a recommended answer for each question ([references/spec-format.md](references/spec-format.md)). A spec with open questions, `TBD`, or `TODO` cannot be approved.
2. **Split work into one-run mini-batch tasks.** `PLAN.md` breaks the spec into `TASKS.json` tasks that one subagent can finish in a single run: one observable outcome, a few files, its own red → green tests, and an objective `done_when`. Tasks are grouped into numbered batches ([references/plan-and-tasks.md](references/plan-and-tasks.md)).
3. **Mark tasks done** with evidence as described in [references/plan-and-tasks.md](references/plan-and-tasks.md#marking-a-task-done). The spec becomes `Implemented` only when every task is `done`.
4. **Name specs so they can be skimmed.** A folder names a capability (`NNN-<feature>`, `NNN-component-<capability>`), never a change; `NNN` stands for the spec ID throughout this skill: a random 7-character `[a-z0-9]` ID for new specs, or a legacy 3-digit number; `SPEC.md` declares `kind` and a one-line `summary`; the index in `specs/README.md` stays in sync ([references/spec-catalog.md](references/spec-catalog.md#naming)).
5. **Share through components.** Behavior used by more than one feature lives in one component spec; features list it under `Components used` with the REQs they rely on and never restate it ([references/spec-catalog.md](references/spec-catalog.md#components)).
6. **Plan tests as cases.** Every Verification matrix row is a `happy`, `edge`, or `error` case; every active REQ has at least a happy and an error row (or an error row `N/A: <reason>`), plus edge rows for its boundaries. Test writers write a test per row ([references/spec-format.md](references/spec-format.md#test-cases)).
7. **Keep every artifact upgradeable.** Each spec file declares its template `format` and its own semver `version` with a `Changelog`; never reuse or renumber a REQ ID ([references/format-versions.md](references/format-versions.md)).

## Approval boundary

- Gate 1 approves the spec, the plan, and **every batch**. Batches then run back to back without further approval. The run stops before Gate 2 only for a `SPEC_ESCALATION` or a `blocked` task.
- Record approvals in `SPEC.md` under `Approval record` only after the user gives them.
- **Spec escalation.** If building or full verification reveals that approved behavior, scope, or a contract must change, stop. Record a `SPEC_ESCALATION` under `Open questions`, set the spec back to `Draft`, propose the change with a recommendation, and get fresh approval. Never weaken a test or rewrite a requirement to make code look compliant.
- Internal implementation choices that keep the approved behavior, contracts, and tests do not need reapproval; note meaningful ones in `PLAN.md`.

## Running an approved spec

"Run spec NNN" (or "run 001") means: run that spec from where it stands to Gate 2 with no further prompts.

1. Read `SPEC.md`, `SPEC_REVIEW.md`, `PLAN.md`, `TASKS.json`, and `AUDIT_REPORT.md`. Run the checker.
2. If the spec is not `Approved`, or the checker reports an error, stop and say what is missing; Gate 1 is never skipped. If `TASKS.json` was planned against an older spec version, review and replan the changed REQs (steps 3–4) and ask for Gate 1 on that change before building.
3. Otherwise resume the development loop (workflow step 6) at the first task that is not `done`, then full verification and reconcile. Spawn every step automatically (sessions where the host supports them, subagents otherwise). Stop only for a `blocked` task, a `SPEC_ESCALATION`, or Gate 2.

## Activation

Use this skill for new features and externally observable changes, behavioral bug fixes, API/UI/event/integration contract changes, data model or migration changes made for behavior, and authorization, information-exposure, or runtime-configuration changes.

Skip it for formatting, documentation-only edits, proven behavior-preserving refactors, test-only cleanup that keeps coverage requirements, and mechanical dependency maintenance. If such work reveals an observable change, stop and start at Stage 1.

## Workflow

1. **Locate** (rule 0). Editing: work in the owning spec's folder ([references/spec-catalog.md](references/spec-catalog.md#editing-an-existing-spec)). New: generate a random 7-character spec ID from `[a-z0-9]` (`python3 -c "import secrets,string;print(''.join(secrets.choice(string.ascii_lowercase+string.digits) for _ in range(7)))"`), confirm no `specs/<id>-*` folder uses it (create `specs/` at the repository root if it does not exist), create `specs/<id>-<capability>/` from the templates, and regenerate the index with `--write-index`.
2. **Specify.** Research the codebase and context first; when several areas are involved, fan out one read-only research subagent per area, all in one message. Clarify (rule 1), write `SPEC.md`; for user-interface components also write `UI.md` using tokens from the root `DESIGN.md` ([references/ui-spec-format.md](references/ui-spec-format.md), [references/design-md-format.md](references/design-md-format.md)).
3. **Review.** Spawn one zero-context reviewer that covers four lenses (naive reader, critic, simplicity, codebase checker), triage its findings into `SPEC_REVIEW.md`, and run a second pass when a `blocker` or `major` was fixed ([references/spec-review.md](references/spec-review.md)). Do not plan until no `blocker` or `major` is `open`.
4. **Plan.** Write `PLAN.md` and `TASKS.json` (rule 2). Run the checker.
5. Request **Gate 1** approval for spec, plan, and all batches, with the review's counts per severity and every `contested` finding. Set status `Approved`.
6. **Development loop.** You are the orchestrator: a scheduler that reacts to subagent results. You never write tests or source yourself. Each task runs its own pipeline (red → green → audit → record) in separate fresh-context subagents, never forked from your conversation, and never waits for sibling tasks. Batches run in order; inside a batch, everything that can run in parallel does.
   1. **Start rule**: a task of the current batch starts when its `depends_on` are all `done` and none of its `files` is held by an in-flight task. A task holds its files from the moment its test writer is spawned until it is `done` or `blocked`. Start every eligible task at once, spawning all their test writers in one message, and set them `in_progress`.
   2. **Red**: each test writer writes at least one test per Verification matrix row of its task's REQs (happy, edge, and error), tagged with the REQ IDs ([references/traceability.md](references/traceability.md)), runs **only the tests it created**, and returns the command and the expected failure.
   3. **Green**: as soon as a task's test writer returns, spawn its builder, with the task, the spec, and the test paths as read-only inputs. It changes source and reruns **only that task's red tests** until they pass, then refactors while green. It never edits tests: a wrong test goes back to the test writer, a wrong requirement becomes a `SPEC_ESCALATION`. A task that cannot get green becomes `blocked`.
   4. **Audit**: as soon as a task's builder returns green, spawn its auditor ([references/audit.md](references/audit.md)). The auditor returns its task section; you append it to `AUDIT_REPORT.md`. A `fail` sends only that task back to red or green; other tasks keep running.
   5. **Record**: on `pass`, mark the task `done` (rule 3), release its files, and apply the start rule again so newly unblocked tasks start at once. When several subagents return together, spawn all their next steps in one message.
   6. When every task in the batch is `done`, start the next batch. The run stops early only for a `blocked` task or a `SPEC_ESCALATION`. Run tasks one at a time only when the host cannot run subagents concurrently, and record that in `PLAN.md`.
   7. On a host that can start separate sessions that report back (for example the Claude desktop app), run each red, green, and audit step as its own session instead of a subagent, without being asked ([references/stages.md](references/stages.md#sessions-on-hosts-that-support-them)).
7. **Full verification.** When every task in the spec is `done`, run the full test suite, the project verification commands (format, lint, type check, tests with coverage, end-to-end where the project has them), and the checker once, all concurrently (parallel background commands or one subagent per command); record every result in `AUDIT_REPORT.md`. If anything fails:
   - Approved behavior still holds (a bug): add the missed case to the `SPEC.md` Verification matrix (patch bump + Changelog), add fix tasks with new IDs in a new batch, and return to step 6. No reapproval is needed.
   - Behavior, contracts, or scope must change: `SPEC_ESCALATION` and wait for approval.
   Repeat until full verification passes.
8. **Reconcile**: update `SPEC.md` to match reality (bump `version`, log changes), set `Implemented`, and present the spec diff with the code diff (**Gate 2**).

Run the checker ([references/traceability.md](references/traceability.md)) before Gate 1, after each task is recorded, and in full verification.

## References

- [references/spec-catalog.md](references/spec-catalog.md): spec kinds, naming, the index, Locate, editing an existing spec, and components.
- [references/spec-review.md](references/spec-review.md): Stage 1.5 reviewer, triage, and `SPEC_REVIEW.md`.
- [references/stages.md](references/stages.md): stage roles, writable paths, subagents, and quality gates.
- [references/spec-format.md](references/spec-format.md): `SPEC.md` template, clarification rules, and test cases.
- [references/plan-and-tasks.md](references/plan-and-tasks.md): `PLAN.md`, `TASKS.json`, task sizing and status.
- [references/ui-spec-format.md](references/ui-spec-format.md): `UI.md` component spec format.
- [references/design-md-format.md](references/design-md-format.md): root `DESIGN.md` token format.
- [references/traceability.md](references/traceability.md): test tags and the checker.
- [references/audit.md](references/audit.md): `AUDIT_REPORT.md` template.
- [references/format-versions.md](references/format-versions.md): format registry, versioning, and migrations.
