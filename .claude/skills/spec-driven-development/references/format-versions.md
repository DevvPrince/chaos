# Format Versions and Change Control

Two kinds of change are tracked separately:

| Change | Field | How |
| --- | --- | --- |
| The content of one spec changes | `version` (semver) + `Changelog` | Edit in place, bump `version`, add a Changelog line |
| A template's structure changes | `format` (`<name>/vN`) | Add a new format version here and in the checker |

## Current formats

| Artifact | Current | Supported | Required sections / fields |
| --- | --- | --- | --- |
| `SPEC.md` | `spec/v2` | v1, v2 | v2: frontmatter `id`, `title`, `kind`, `summary`, `status`, `version`; sections Problem and outcome, Observable behavior, Non-goals, Interface contracts, Components used, Verification matrix (with a `Case` column), Operational constraints, Open questions, Approval record, Changelog. v1: the same without `kind`, `summary`, Components used, and the `Case` column |
| `UI.md` | `ui/v1` | v1 | Frontmatter `spec`, `version`; section Changelog |
| `PLAN.md` | `plan/v1` | v1 | Frontmatter `spec`, `version`; sections Approach, Tasks, Changelog |
| `TASKS.json` | `tasks/v1` | v1 | `format`, `spec`, `tasks` |
| `SPEC_REVIEW.md` | `spec-review/v1` | v1 | Frontmatter `spec`, `spec_version`, `verdict` |
| `AUDIT_REPORT.md` | `audit/v1` | v1 | Frontmatter `spec`, `verdict` |
| `DESIGN.md` | `design/v1` | v1 | Frontmatter `version`; section Changelog |

## Adding a format version

1. Add `vN+1` to the table with what changed and a migration note below.
2. Update `SUPPORTED_FORMATS` (and required sections) in `scripts/check_spec_traceability.py`, keeping older versions supported. The last version listed is current; files on older ones produce a warning, unknown ones fail.
3. Update the template in the matching reference file.
4. Migrate existing specs when convenient: change `format`, apply the migration note, and bump the file's `version` with a Changelog line.

Prefer additive changes (new optional sections) so older files stay valid. Never change the meaning of an existing field within the same format version.

## Migration notes

### `spec/v1` → `spec/v2`

1. Set `format: spec/v2`; add `kind` (`feature` or `component`) and a one-line `summary` (at most 120 characters).
2. Rename a component's folder to `NNN-component-<capability>`; give a feature a capability name, not a change name ([spec-catalog.md](spec-catalog.md#naming)). Tags use only the number, so renaming does not touch tests.
3. Add `## Components used` after Interface contracts (`None.` when there are none).
4. Add a `Case` column after `REQ` in the Verification matrix, classify each row, and add the happy and error rows each active REQ is missing ([spec-format.md](spec-format.md#test-cases)).
5. Bump the spec's `version` (patch: no behavior changes) with a Changelog line, then run the checker with `--write-index`.

v1 specs keep passing with a warning, are listed in the index with kind `—` and their title as summary, and have no case coverage check.
