# Spec-to-Test Traceability

## Tagging tests

A tag is `NNN:REQ-NN`: the spec ID (`k3f9x2a`, or a legacy `001`) and the requirement ID. Put it where the test framework keeps it visible: a marker or attribute, the test title, or a comment directly above the test. Examples:

```python
# pytest: register the marker once in pytest config
# markers = ["spec(*tags): links a test to spec requirements"]
@pytest.mark.spec("001:REQ-01", "001:REQ-02")
def test_retry_requeues_failed_job() -> None: ...
```

```ts
// Vitest, Jest, Playwright, Mocha: tag in the title
it("[001:REQ-03] disables Retry while the request is in flight", async () => { ... });
```

```go
// 001:REQ-01
func TestRetryRequeuesFailedJob(t *testing.T) { ... }
```

Tag the tests that prove the requirement, not every helper test. If the project already has a tagging convention, use it as long as the literal `NNN:REQ-NN` text appears in the test file.

## The checker

```bash
python3 .agents/skills/spec-driven-development/scripts/check_spec_traceability.py
```

Run it from the repository root (or pass `--root`). It uses only the Python standard library, so CI can run it without installing the project. The Bitbucket pull-request pipeline runs it on every pull request and fails the pull request on errors (spec 028).

By default it scans the whole repository for test files. A file counts as a test when it has a common source extension and either its name follows a test convention (`test_*`, `*_test.*`, `*.test.*`, `*.spec.*`, `*_spec.*`, `*Test.*`, `*Tests.*`) or it sits under a `test`, `tests`, `__tests__`, `spec`, `e2e`, or `integration_tests` directory. It skips `specs/`, hidden directories (except `.agents/skills/verify-allkons/drive/`, whose runtime-evidence tests carry tags), and dependency/build directories (`node_modules`, `venv`, `dist`, `build`, `target`, `vendor`, ...). To limit the scan, pass one or more `--test-root` directories:

```bash
python3 .agents/skills/spec-driven-development/scripts/check_spec_traceability.py --test-root tests --test-root web/src
```

Source extensions include `.sh`, `.bash`, `.bats` and `.hcl` alongside Python, JavaScript/TypeScript and the other supported languages. `*.tftest.hcl` also counts as a test outside conventional test directories. Comment tags such as `# spec: 001:REQ-01, 001:REQ-02` and `// spec: 001:REQ-01` are accepted alongside marker and title tags.

A nested directory containing its own `specs/README.md` owns a separate catalog. The parent scan prunes that whole subtree, even when `--test-root` points into it. Run the checker with `--root` set to that nested project to validate its tests against its own spec IDs. Ordinary nested directories remain part of the parent scan, and unknown or removed requirements in the active catalog still fail. Explicit test roots also preserve hidden/dependency exclusions and must be inside the active root.

It fails when:

| Check | Applies to |
| --- | --- |
| Missing or unknown `format`, or missing required sections | All spec artifacts |
| `kind` not `feature` or `component`; folder name does not match the kind (`NNN-component-...` only for components); `summary` longer than 120 characters | `spec/v2` |
| A Verification matrix table lacks `REQ` and `Case` columns, a row has a case other than `happy`, `edge`, `error`, or names an unknown or removed REQ | `spec/v2` |
| An active REQ has no `happy` row or no `error` row | `spec/v2`, Approved or later |
| `Components used` names a missing, non-component, or `Superseded` spec, or an unknown or removed REQ of it | `spec/v2` |
| The `specs/README.md` index is missing or out of date | When any `spec/v2` exists |
| Open questions, `TBD`, or `TODO` remain | `SPEC.md` / `UI.md` with status Approved or later |
| An active REQ is not covered by any task | Approved or later |
| `TASKS.json` has duplicate IDs, unknown dependencies, unknown or removed REQs, invalid status, or a cycle | All |
| A `done` task lacks `completed_at`, red/green evidence, or `changed_files`, or depends on an unfinished task | All |
| A `blocked` task lacks `blocked_reason` | All |
| A REQ covered by a `done` task has no tagged test | All |
| Any active REQ has no tagged test, or any task is not `done` | Implemented |
| A test tag names an unknown spec or an unknown/removed REQ | Always |
| A `SPEC_REVIEW.md` finding has an unknown severity or resolution, a non-nit is `declined`, or the verdict is `pass` while a `blocker` or `major` is `open` | All |
| A `blocker` or `major` finding is `open`, or the spec review verdict is `fail` | Approved or later |
| A `UI.md` value is not a `DESIGN.md` token, quoted literal, `null`, boolean, or note | All |

Regenerate the index after adding or renaming a spec or changing a `summary` or `Components used`:

```bash
python3 .agents/skills/spec-driven-development/scripts/check_spec_traceability.py --write-index
```

It rewrites only the block between `<!-- spec-index:start -->` and `<!-- spec-index:end -->` in `specs/README.md` (adding an `## Index` section if the markers are missing), then runs the checks.

It only proves that tagged tests exist; the test jobs prove they pass. Warnings (older format versions, plan or spec review written against an older spec version, an Approved or later spec without `SPEC_REVIEW.md`) do not fail the build. Add it to CI next to the project's other checks.
