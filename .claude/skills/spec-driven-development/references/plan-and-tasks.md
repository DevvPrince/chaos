# PLAN.md and TASKS.json (`plan/v1`, `tasks/v1`)

## Task sizing: one agent, one run

Every task must be finishable by one subagent in a single run without asking a question. A task:

- Delivers one observable outcome tied to one or a few closely related REQ IDs.
- Touches a small set of files (aim for five source files or fewer).
- Has its own red → green tests and an objective `done_when`.
- Leaves its own red tests passing; the full suite runs once, after every task is `done`.
- Depends only on tasks that are earlier or in an earlier batch.
- Lists in `files` every file it creates or edits, including test files and shared fixtures or helpers (for example `conftest.py`); the orchestrator uses `files` to decide which tasks can run at the same time.
- Shares no file with a task it has no dependency relation to, so the two can run in parallel. Put shared fixtures or helpers in their own early task that others depend on.

Split a task when it covers unrelated REQ clusters, crosses migration + API + UI at once without needing to, needs a decision partway through, or its `done_when` needs the word "and" more than once. Do not split purely by layer when neither half is verifiable alone.

## Changing an existing spec

When the request edits an existing spec ([spec-catalog.md](spec-catalog.md#editing-an-existing-spec)), add a `### <change title> (v<new version>)` subsection under `Approach`, append rows to `Files`, and add tasks that continue the ID sequence in new batches after the highest existing batch. Never rewrite or reuse `done` tasks; set `spec_version` to the new spec version.

## Batches

Group tasks into numbered batches (`"batch": 1`, `2`, ...). A batch is one coherent vertical capability that is independently testable and reviewable. Batches run in order, back to back; Gate 1 approves all of them. Fix tasks added after a failed full verification go in a new batch.

## PLAN.md template

````markdown
---
format: plan/v1
spec: "NNN"
version: 0.1.0
---

# NNN Feature name — plan

## Approach

File-level design: modules, boundaries, data flow, and which skills apply.

## Files

| Path | Change | Task |
| --- | --- | --- |
| src/jobs/retry.py | new | T01 |

## Risks

- <risk> — <mitigation>

## Tasks

- [ ] T01 (batch 1) <title> — REQ-01
- [ ] T02 (batch 1) <title> — REQ-02
- [ ] T03 (batch 2) <title> — REQ-03

## Changelog

- 0.1.0 (YYYY-MM-DD): Initial plan.
````

## TASKS.json schema

```json
{
  "format": "tasks/v1",
  "spec": "NNN",
  "spec_version": "0.1.0",
  "tasks": [
    {
      "id": "T01",
      "batch": 1,
      "title": "Retry endpoint re-queues a failed job",
      "reqs": ["REQ-01"],
      "depends_on": [],
      "files": ["src/jobs/retry.py"],
      "done_when": "POST /jobs/{id}/retry on a failed job returns 202 and the job is queued",
      "status": "todo",
      "completed_at": null,
      "evidence": {"red": null, "green": null},
      "changed_files": [],
      "blocked_reason": null
    }
  ]
}
```

| Field | Rule |
| --- | --- |
| `id` | `T` + two or more digits, unique, never reused |
| `reqs` | Active REQ IDs from `SPEC.md`; every active REQ appears in at least one task |
| `depends_on` | Existing task IDs; no cycles |
| `status` | `todo` → `in_progress` (set when its test writer is spawned) → `done`, or `blocked` |
| `spec_version` | The `SPEC.md` version the plan was written against |

## Marking a task done

When the task's `done_when` holds and its audit passes, the orchestrator, from the subagents' returned evidence:

1. Sets `status` to `"done"` and `completed_at` to the ISO date.
2. Fills `evidence.red` (command, and the expected failure it produced) and `evidence.green` (the task's red-test command and its passing result). Summaries, not full logs.
3. Lists `changed_files`.
4. Ticks the task in `PLAN.md` (`- [x] T01 ...`).

A `done` task may depend only on `done` tasks. A task that cannot finish becomes `"blocked"` with `blocked_reason`; if the blocker is a requirement problem, raise a `SPEC_ESCALATION`.
