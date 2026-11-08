# SPEC.md Format (`spec/v2`)

Which spec to write or edit, folder naming, `kind`, and components are in [spec-catalog.md](spec-catalog.md).

## Clarification rules

Inspect the repository before asking about current behavior, architecture, or conventions. Ask the user only about decisions, not facts you can read.

A question is material when its answer could change behavior, scope, business rules, edge cases, failure handling, data ownership or migration, contracts, authorization or information exposure, acceptance criteria, tests, or non-functional behavior.

Ask in rounds. Ask every question whose prerequisites are already settled at once, each in this shape:

```text
Q3. What happens when the retry fails again?
Recommendation: show the error inline and keep the button enabled, because the user can act immediately and no new state is needed.
Alternatives: (a) disable after 3 attempts; (b) navigate to a failure page.
```

Write the user's decisions into the spec as you go. Never turn an example into a rule, pick product behavior by convention, or hide uncertainty in an assumption. Keep asking until `Open questions` is empty. Minor internal choices that every reasonable option satisfies stay with the builder.

Do not invent non-functional targets (latency, load, accessibility audits) unless the user sets them. Consider only categories that apply: authorization and information exposure, data integrity and rollback, idempotency and duplicates, error recovery, runtime configuration, and compatibility the user explicitly requires. Mark a considered category `N/A` with a reason when its absence would be ambiguous.

## Requirement IDs

- Every observable outcome and every applicable operational constraint gets a `REQ-NN` ID, numbered in order across the whole spec.
- Define each on its own list line: `- **REQ-01**: <testable outcome>`.
- State outcomes, never tasks: "An interrupted upload resumes from the last committed chunk", not "Add resume logic".
- IDs are permanent. Never renumber or reuse one. Mark changes in place:
  - `- **REQ-02** [changed 1.1.0]: <new outcome>`
  - `- **REQ-03** [removed 1.1.0]: <reason>` (removed REQs need no tests, and tests may no longer cite them)

## Test cases

The Verification matrix is the test plan. Each row is one case the test writer turns into at least one test, and its `Case` column says what kind:

| Case | Meaning | Examples |
| --- | --- | --- |
| `happy` | The intended path succeeds | A failed job is retried and queued |
| `edge` | A boundary or unusual condition that must still behave correctly | Empty input, the exact limit, duplicates, concurrent requests, restart or recovery mid-flow |
| `error` | Input or conditions the REQ must reject or survive, and what the user or caller sees | Invalid input, unauthorized caller, provider failure, limit exceeded, stale state |

- Every active REQ has at least one `happy` row and at least one `error` row. When a REQ truly has no failure path of its own, its error row says why: `Then` = `N/A: <reason>` (for example `N/A: rejection is REQ-07's`). The checker enforces both once the spec is `Approved`.
- Add an `edge` row for every boundary the REQ has: limits and off-by-one, empty or missing values, duplicates and idempotency, concurrency, retries, restart and recovery. The auditor fails a task whose REQ has an obvious boundary with no edge row.
- Each row has one observable `Then` (a status code, a stored value, a rendered message), not "works" or "handles it".
- Tests name their case: a test for an error row says what it rejects (`test_retry_of_running_job_returns_409`), not just `test_retry_2`.

## Template

````markdown
---
format: spec/v2
id: "NNN"
title: Feature name
kind: feature
summary: <one line, at most 120 characters: what this spec owns>
status: Draft
version: 0.1.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# NNN Feature name

## Problem and outcome

Who has the problem, what changes for them, and how we will know.

## Observable behavior

- **REQ-01**: <testable system outcome>
- **REQ-02**: <testable system outcome>

## Non-goals

- <what must not be built, changed, or refactored>

## Interface contracts

Exact types and schemas in the project's languages, endpoints (method, path, status codes, bodies), migrations, events, and file formats. Link machine-readable files in this directory (for example `contracts.openapi.yaml`). User-interface components are specified in `UI.md`.

## Components used

- NNN component-<capability> — relies on NNN:REQ-01, NNN:REQ-03

(or `None.`)

## Verification matrix

| REQ | Case | Given | When | Then | Level |
| --- | --- | --- | --- | --- | --- |
| REQ-01 | happy | ... | ... | ... | API |
| REQ-01 | edge | ... | ... | ... | API |
| REQ-01 | error | ... | ... | ... | API |

Rules are in [Test cases](#test-cases). Levels: unit, integration, migration, API, component, journey (end-to-end). Use the project's existing test frameworks for each level.

## Operational constraints

- **REQ-0N**: <measurable constraint: auth scope, idempotency, rate limit, latency budget set by the user>
- N/A: <category> — <reason>

## Open questions

None.

## Approval record

- YYYY-MM-DD: <who> approved spec v<version>, plan, and batch 1.

## Changelog

- 0.1.0 (YYYY-MM-DD): Draft.
````

## Status

| Status | Meaning |
| --- | --- |
| Draft | Being clarified or changed (including an approved or implemented spec being edited); open questions allowed |
| Approved | Gate 1 passed; no open questions, `TBD`, or `TODO` |
| In progress | At least one task started |
| Implemented | Every task `done`, every active REQ has a tagged test, Gate 2 passed |
| Superseded | Replaced; name the replacing spec in the Changelog |

## Versioning

Use semver for `version`: patch for wording that keeps meaning, minor for added or changed REQs, major for removed behavior or broken contracts. Every bump adds a Changelog line and updates `updated`. A change to an approved spec after Gate 1 returns it to `Draft` until re-approved, unless it is a patch. Adding a Verification matrix row that pins already-approved behavior (after a failed full verification) is a patch.
