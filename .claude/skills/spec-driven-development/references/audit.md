# AUDIT_REPORT.md (`audit/v1`)

One auditor subagent per task, running in parallel with other tasks' audits, reads that task's diff, the spec, and the task's tests, and returns the task's section; the orchestrator appends each section as it arrives (the heading names the task, so order does not matter) and writes the `Full verification` section. It is adversarial: look for ways the code satisfies the tests but not the spec.

## What to check

- **Spec drift**: behavior in the diff that no REQ asks for, or a REQ whose behavior is only partly implemented.
- **Non-goals**: anything the spec's Non-goals forbid.
- **Contracts**: types, endpoints, status codes, migrations, and events match `Interface contracts` exactly.
- **Case coverage**: every Verification matrix row of the task's REQs (happy, edge, error) has a test that checks its `Then`; a REQ with an obvious boundary has an edge row.
- **Components**: the task does not re-implement or restate behavior owned by a component in `Components used`; a change to a component's behavior is only made through that component's spec.
- **UI**: components use exactly the `UI.md` tokens and copy.
- **Test integrity**: tests changed after their red evidence, weakened assertions, skipped or deleted tests, over-mocking that hides the behavior.
- **Project rules**: violations of the repository's engineering laws (`CONSTITUTION.md` or equivalent, when present) and the stack skills or `AGENTS.md` rules that apply (secrets, architecture, side effects).
- **Verification**: rerun the task's red tests and the traceability checker; the full suite and project checks run once, in `Full verification`.
- Where the feature runs, exercise it (API call, browser) and record what you observed.

## Template

````markdown
---
format: audit/v1
spec: "NNN"
spec_version: 0.1.0
date: YYYY-MM-DD
verdict: pass
---

# NNN Audit

## T01 (batch 1) — pass

| REQ | Verdict | Evidence |
| --- | --- | --- |
| REQ-01 | pass | test_retry_requeues_failed_job; manual POST returned 202 |

Findings: none.

Task tests: `<command running the task's red tests>` — pass.

## Full verification — pass

| Command | Result |
| --- | --- |
| <project test command with coverage> | pass, 92% branch |
| check_spec_traceability.py | pass |
````

Frontmatter `verdict` (`pass` or `fail`) is the latest overall result. Any finding fails the section: the builder fixes source, the test writer fixes a wrong test, or the spec escalates. Append a new section for each re-audit or rerun instead of rewriting history.
