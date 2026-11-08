# Stages, Roles, and Write Permissions

Privilege separation is the core rule: each role writes only its own artifacts. A role that needs a change outside its paths stops and hands back to the role that owns them.

## Writable paths per role

| Stage | Role | Reads | May write | Must not write |
| --- | --- | --- | --- | --- |
| 0 Locate | Spec writer | Request, `specs/README.md` index, candidate specs | Nothing until the owner is settled (asks the user when unclear) | Everything |
| 1 Specify | Spec writer | Request, project rules (`CONSTITUTION.md`, `AGENTS.md`/`CLAUDE.md`, applicable skills, when present), `DESIGN.md`, codebase | `specs/NNN-name/SPEC.md` of every spec the request touches (feature and component), `UI.md`, contract files (`*.openapi.yaml`, `*.schema.json`); the `specs/README.md` index; `DESIGN.md` token additions | Source, tests |
| 1.5 Review | One reviewer subagent covering four lenses (naive reader, critic, simplicity, codebase checker), fresh context | `SPEC.md`, `UI.md`, contracts, specs in `Components used`, `DESIGN.md`, project rules, codebase; never the clarification conversation | Nothing: return findings to the spec writer | Everything |
| 1.5 Triage | Spec writer | Reviewer findings | `SPEC_REVIEW.md`; the stage 1 files to fix findings | Source, tests |
| 2 Plan | Architect | Approved spec, codebase | `specs/NNN-name/PLAN.md`, `TASKS.json` | Source, tests, `SPEC.md` |
| 3 Test (Red) | Test-writer subagent, fresh context | Spec, plan, its task | Test files, fixtures, and test helpers (wherever the project keeps them); empty interface stubs that only raise/throw "not implemented" | Real implementation, specs, `TASKS.json` |
| 4 Build (Green) | Builder subagent, fresh context | Spec, plan, its task, its failing tests | Source, migrations, and config needed by the task | Tests, specs, `TASKS.json`, `PLAN.md` |
| 5 Audit | Auditor subagent, fresh context | Task diff, spec, tests, runtime | Nothing: returns its task section to the orchestrator | Everything |
| 3–6 | Orchestrator (main agent) | Everything | `TASKS.json` status and evidence, `PLAN.md` checklist, `AUDIT_REPORT.md` (auditors' task sections appended verbatim, and the `Full verification` section); fix tasks after a failed full verification | Source, tests |
| 7 Reconcile | Reconciler | Diff, spec, audit report | `specs/NNN-name/SPEC.md`, `UI.md` (version bump + Changelog), the `specs/README.md` index | Source, tests |

Test fixtures, factories, and shared test setup (for example `conftest.py`, `setupTests.ts`) belong to the test writer.

## Subagents

- Every task gets its own test-writer, builder, and auditor run; the orchestrator never does a task's red, green, or audit work itself, even for a small task.
- Pipeline, not waves: a task starts when its dependencies are `done` and its `files` are free, and each step starts as soon as that task's previous step returns. No task waits for a sibling. Whenever several steps become ready at once, the orchestrator spawns them in one message.
- File holding: a task holds every file in its `files` from test-writer spawn until it is `done` or `blocked`, so subagents running at the same time never share a source or test file.
- Every red, green, and audit run starts with a fresh context: its brief is its only context. Never fork the orchestrator's conversation into one; it would see more than its role's Reads column. A follow-up to the same step (a wrong test back to its test writer) goes to the run that already holds that step's context.
- Test writer and builder are always separate subagent runs. The builder gets the test paths as read-only inputs; the auditor checks the diff for any test change made after the red evidence was recorded.
- Subagents return their evidence (commands, results, changed files, audit sections) to the orchestrator, which alone writes `TASKS.json`, `PLAN.md`, and `AUDIT_REPORT.md`, so parallel runs never write the same file.
- Concurrent subagents share one working tree. A run whose tests fail because of a file outside its own task (an import or collection error from another in-flight task's half-edited file) reports that instead of working around it; the orchestrator reruns it once the other task is done.
- Run tasks one at a time only when the host cannot run subagents concurrently; record that in `PLAN.md`.

### Sessions on hosts that support them

When the host can start separate sessions that report back to the chat that started them (for example the Claude desktop app), run every red, green, and audit step as its own session automatically. The user does not need to ask for sessions; "Run spec NNN" is enough. On other hosts, use subagents as above.

- One session per pipeline step, never one per task. Red, green, and audit stay separate runs, so a session that wrote a task's tests never builds it. File holding works as it does for subagents. Start all ready steps in one message, as for subagents.
- The brief is the session's only context. Name the spec folder, the task ID, the files it may write (the role's row in the table above), the exact test command, and `done_when`. End it with this line: "Report back with the verdict first (`red`, `green`, `pass`, `fail`, or `blocked`), then the commands, results, and changed files. Do not edit `TASKS.json`, `PLAN.md`, or `AUDIT_REPORT.md`."
- When a session ends its turn, its report reaches the orchestrator and the orchestrator continues on its own. That report is cut short, often to the first few hundred characters. Read the verdict from it, then read the session's full final message, or check its diff, before recording evidence. A report is a claim, not evidence; rerun the task's test command when in doubt.
- Then apply the start rule and start the next steps at once, without waiting for the user. Send follow-ups (a wrong test back to the test writer, for example) to the session that holds the context instead of starting a new one.
- A session that shares this working tree must touch only its task's files, commit nothing, and switch no branch. Use worktree sessions only in a git repository. A worktree session commits to its own branch; before the next step or full verification needs that work, ask the user whether to merge it, and never merge or push it unprompted.
- Cloud sessions never report back. Do not use them for pipeline steps.
- If the host stops continuing the orchestrator (for example after many automatic turns in a row with no user message), the run pauses. On the user's next message ("continue"), read `TASKS.json` and the sessions' reports and resume with the start rule.
- Record in `PLAN.md` which batches ran as sessions.

## Quality gates

| Stage | Gate | Evidence |
| --- | --- | --- |
| 0 | The owning spec(s) and the classification (edit feature, edit component, new feature, new component) are settled; the user answered when it was unclear | Stated in the Stage 1 message |
| 1 | Human Gate 1 (after 1.5 and 2): spec has no open questions, every active REQ has happy and error rows (edge rows for its boundaries), contracts are exact | Approval record entry |
| 1.5 | The fresh reviewer found no `blocker` or `major` that is still `open`; every `contested` finding cites evidence | `SPEC_REVIEW.md` verdict `pass` |
| 2 | Checker passes: formats valid, every active REQ covered by a task, no dependency cycle | Checker output |
| 3 | Every Verification matrix row of the task's REQs has a test; each new test fails because the behavior is missing, not because of imports, syntax, setup, or selectors | `evidence.red` in the task |
| 4 | The task's red tests pass (only those tests run) | `evidence.green` in the task |
| 5 | No spec drift, non-goal violations, or weakened tests in the task | Task section verdict `pass` in `AUDIT_REPORT.md` |
| 6 | After every task is `done`: full suite, project verification commands (see `AGENTS.md` or the stack skills), and checker pass | `Full verification` section in `AUDIT_REPORT.md` |
| 7 | Human Gate 2: spec diff and code diff reviewed together | PR / approval record |

Characterization tests that pin existing behavior may pass immediately; label them as such in `evidence.red`.

If a check cannot run, record the gap in the task evidence and report it. Never weaken thresholds or claim completion.
