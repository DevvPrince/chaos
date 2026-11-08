"""Tests for check_spec_traceability.py. Run: python3 -m unittest discover <this directory>."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_spec_traceability import check_repository, is_skipped, write_index

SPEC = """---
format: spec/v2
id: "001"
title: Retry failed jobs
kind: feature
summary: {summary}
status: {status}
version: 1.0.0
created: 2026-10-14
updated: 2026-10-14
---

# 001 Retry failed jobs

## Problem and outcome

Users can retry a failed job.

## Observable behavior

- **REQ-01**: Retrying a failed job queues it again.
- **REQ-02**: The Retry button is disabled while the request is in flight.
- **REQ-03** [removed 1.0.0]: Replaced by REQ-02.

## Non-goals

- Bulk retry.

## Interface contracts

POST /jobs/{{id}}/retry returns 202.

## Components used

{components}

## Verification matrix

| REQ | Case | Given | When | Then | Level |
| --- | --- | --- | --- | --- | --- |
{matrix}

## Operational constraints

- N/A: rate limits — single user.

## Open questions

{open_questions}

## Approval record

- 2026-10-14: approved.

## Changelog

- 1.0.0 (2026-10-14): Approved.
"""

PLAN = """---
format: plan/v1
spec: "001"
version: 1.0.0
---

## Approach

Add an endpoint and a button.

## Tasks

- [x] T01 (batch 1) Retry endpoint — REQ-01
- [ ] T02 (batch 1) Retry button — REQ-02

## Changelog

- 1.0.0 (2026-10-14): Initial plan.
"""

MATRIX = """| REQ-01 | happy | a failed job | retry | queued | API |
| REQ-01 | error | a running job | retry | 409 | API |
| REQ-02 | happy | a pending request | render | disabled | component |
| REQ-02 | edge | a request that fails | render | enabled again | component |
| REQ-02 | error | — | — | N/A: the button has no failure path of its own | — |"""

COMPONENT = """---
format: spec/v2
id: "{number}"
title: Notification sender
kind: component
summary: Sends one notification through the configured provider.
status: {status}
version: 1.0.0
---

# {number} Notification sender

## Problem and outcome

Features need to notify users.

## Observable behavior

- **REQ-01**: A notification is sent once per request.
- **REQ-02** [removed 1.0.0]: Replaced.

## Non-goals

- Templates.

## Interface contracts

send(message) -> None

## Components used

None.

## Verification matrix

| REQ | Case | Given | When | Then | Level |
| --- | --- | --- | --- | --- | --- |
| REQ-01 | happy | a message | send | delivered | unit |
| REQ-01 | error | a provider error | send | raises | unit |

## Operational constraints

- N/A: rate limits — single user.

## Open questions

None.

## Approval record

- 2026-10-14: approved.

## Changelog

- 1.0.0 (2026-10-14): Approved.
"""

V1_SPEC = """---
format: spec/v1
id: "001"
title: Retry failed jobs
status: Draft
version: 0.1.0
---

## Problem and outcome

x

## Observable behavior

- **REQ-01**: Retrying a failed job queues it again.

## Non-goals

x

## Interface contracts

x

## Verification matrix

| REQ | Given | When | Then | Level |
| --- | --- | --- | --- | --- |
| REQ-01 | a failed job | retry | queued | API |

## Operational constraints

x

## Open questions

None.

## Approval record

x

## Changelog

x
"""

REVIEW = """---
format: spec-review/v1
spec: "001"
spec_version: 1.0.0
date: 2026-10-14
verdict: {verdict}
---

# 001 Spec review

## Pass 1 (spec 1.0.0)

| ID | Reviewer | Severity | Scope | Finding | Resolution | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| F01 | naive reader | {severity} | REQ-01 | "queued" is undefined | {resolution} | Defined |
| F02 | critic | nit | REQ-02 | wording | declined | Clear enough |
"""

DESIGN = """---
format: design/v1
version: 0.1.0
---

## Color

| Token | Value | CSS variable |
| --- | --- | --- |
| `color.primary` | oklch(0.5 0.2 260) | --primary |
| color.primary-foreground | oklch(1 0 0) | --primary-foreground |

## Radius

| Token | Value |
| --- | --- |
| radius.md | rounded-md |

## Changelog

- 0.1.0 (2026-10-14): Initial.
"""

UI = """---
format: ui/v1
spec: "001"
version: 1.0.0
---

### UI-01 RetryButton

Implements: REQ-02

| Property | Value |
| --- | --- |
| background | {background} |
| text-color | color.primary-foreground |
| corners | radius.md |
| text | "Retry" |
| shadow | null |

| State | Changes |
| --- | --- |
| loading | text: "Retrying…"; background: color.primary |

## Changelog

- 1.0.0 (2026-10-14): Initial.
"""


def task(
    task_id: str, reqs: list[str], status: str = "todo", depends_on: list[str] | None = None
) -> dict[str, object]:
    done = status == "done"
    return {
        "id": task_id,
        "batch": 1,
        "title": f"Task {task_id}",
        "reqs": reqs,
        "depends_on": depends_on or [],
        "files": ["src/app/x.py"],
        "done_when": "tests pass",
        "status": status,
        "completed_at": "2026-10-14" if done else None,
        "evidence": {
            "red": "pytest: 1 failed" if done else None,
            "green": "pytest: 1 passed" if done else None,
        },
        "changed_files": ["src/app/x.py"] if done else [],
        "blocked_reason": None,
    }


class CheckerTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.spec_dir = self.root / "specs" / "001-retry-failed-jobs"
        self.spec_dir.mkdir(parents=True)
        self.write_spec()
        self.write("PLAN.md", PLAN)
        self.write_tasks(
            [task("T01", ["REQ-01"], "done"), task("T02", ["REQ-02"], depends_on=["T01"])]
        )
        self.write_test(
            "tests/test_retry.py",
            '@pytest.mark.spec("001:REQ-01")\ndef test_retry(): ...\n',
        )
        write_index(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, name: str, text: str) -> None:
        (self.spec_dir / name).write_text(text, encoding="utf-8")

    def write_spec(
        self,
        status: str = "In progress",
        open_questions: str = "None.",
        matrix: str = MATRIX,
        components: str = "None.",
        summary: str = "Users retry a failed job from the job page.",
    ) -> None:
        self.write(
            "SPEC.md",
            SPEC.format(
                status=status,
                open_questions=open_questions,
                matrix=matrix,
                components=components,
                summary=summary,
            ),
        )

    def write_component(
        self,
        number: str = "002",
        name: str = "component-notification-sender",
        status: str = "Draft",
    ) -> Path:
        directory = self.root / "specs" / f"{number}-{name}"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "SPEC.md").write_text(
            COMPONENT.format(number=number, status=status), encoding="utf-8"
        )
        return directory

    def write_tasks(self, tasks: list[dict[str, object]], **overrides: object) -> None:
        data: dict[str, object] = {
            "format": "tasks/v1",
            "spec": "001",
            "spec_version": "1.0.0",
            "tasks": tasks,
        }
        data.update(overrides)
        self.write("TASKS.json", json.dumps(data))

    def write_test(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_ui(self, background: str = "color.primary") -> None:
        (self.root / "DESIGN.md").write_text(DESIGN, encoding="utf-8")
        self.write("UI.md", UI.format(background=background))

    def errors(self) -> list[str]:
        return check_repository(self.root).errors

    def assert_error(self, fragment: str) -> None:
        errors = self.errors()
        self.assertTrue(any(fragment in error for error in errors), f"{fragment!r} not in {errors}")

    def test_clean_repository_passes(self) -> None:
        self.write_ui()
        self.assertEqual(self.errors(), [])

    def test_no_specs_directory_passes(self) -> None:
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        self.assertEqual(check_repository(Path(empty.name)).errors, [])

    def test_done_task_requirement_without_test_fails(self) -> None:
        (self.root / "tests/test_retry.py").unlink()
        self.assert_error("REQ-01 has no test tagged 001:REQ-01")

    def test_implemented_spec_requires_every_requirement_tested_and_done(self) -> None:
        self.write_spec(status="Implemented")
        self.assert_error("REQ-02 has no test tagged 001:REQ-02")
        self.assert_error("spec is Implemented but task is todo")

    def test_title_tag_in_js_test_counts(self) -> None:
        self.write_spec(status="Implemented")
        self.write_tasks([task("T01", ["REQ-01"], "done"), task("T02", ["REQ-02"], "done")])
        self.write_test(
            "web/src/retry-button.test.tsx", 'it("[001:REQ-02] disables Retry", () => {});\n'
        )
        self.assertEqual(self.errors(), [])

    def test_stale_tags_fail(self) -> None:
        self.write_test(
            "tests/test_old.py",
            '@pytest.mark.spec("001:REQ-03", "001:REQ-09", "002:REQ-01")\n',
        )
        self.assert_error("001:REQ-03 names a removed requirement")
        self.assert_error("001:REQ-09 names an unknown requirement")
        self.assert_error("002:REQ-01 names an unknown spec")

    def test_unknown_design_token_fails(self) -> None:
        self.write_ui(background="color.brand")
        self.assert_error("unknown DESIGN.md token 'color.brand'")

    def test_raw_values_fail(self) -> None:
        for raw in ("#2563eb", "16px", "blue"):
            with self.subTest(raw=raw):
                self.write_ui(background=raw)
                self.assert_error(f"raw value {raw!r}")

    def test_ui_without_design_md_fails(self) -> None:
        self.write("UI.md", UI.format(background="color.primary"))
        self.assert_error("UI.md requires a root DESIGN.md")

    def test_task_cycle_fails(self) -> None:
        self.write_tasks(
            [
                task("T01", ["REQ-01"], depends_on=["T02"]),
                task("T02", ["REQ-02"], depends_on=["T01"]),
            ]
        )
        self.assert_error("dependency cycle")

    def test_uncovered_requirement_fails_once_approved(self) -> None:
        self.write_tasks([task("T01", ["REQ-01"], "done")])
        self.assert_error("REQ-02 is not covered by any task")

    def test_open_question_in_approved_spec_fails(self) -> None:
        self.write_spec(status="Approved", open_questions="- Should retries be limited?")
        self.assert_error("'Open questions' is not empty")

    def test_open_question_in_draft_spec_is_allowed(self) -> None:
        self.write_spec(status="Draft", open_questions="- Should retries be limited? TBD")
        self.assertEqual(self.errors(), [])

    def test_done_task_without_evidence_fails(self) -> None:
        incomplete = task("T01", ["REQ-01"], "done")
        incomplete["evidence"] = {"red": None, "green": "pytest: 1 passed"}
        incomplete["completed_at"] = None
        self.write_tasks([incomplete, task("T02", ["REQ-02"])])
        self.assert_error("done but missing evidence.red")
        self.assert_error("done but missing 'completed_at'")

    def test_done_task_with_unfinished_dependency_fails(self) -> None:
        self.write_tasks(
            [task("T01", ["REQ-01"]), task("T02", ["REQ-02"], "done", depends_on=["T01"])]
        )
        self.write_test("tests/test_button.py", '@pytest.mark.spec("001:REQ-02")\n')
        self.assert_error("done but depends on unfinished T01")

    def test_unknown_format_version_fails(self) -> None:
        self.write_tasks(
            [task("T01", ["REQ-01"], "done"), task("T02", ["REQ-02"])], format="tasks/v9"
        )
        self.assert_error("unknown format 'tasks/v9'")

    def test_missing_required_section_fails(self) -> None:
        self.write("PLAN.md", PLAN.replace("## Approach", "## Design"))
        self.assert_error("missing section '## Approach'")

    def test_task_referencing_removed_requirement_fails(self) -> None:
        self.write_tasks([task("T01", ["REQ-01"], "done"), task("T02", ["REQ-02", "REQ-03"])])
        self.assert_error("references removed REQ-03")

    def test_go_test_file_counts(self) -> None:
        self.write_spec(status="Implemented")
        self.write_tasks([task("T01", ["REQ-01"], "done"), task("T02", ["REQ-02"], "done")])
        self.write_test(
            "pkg/retry/retry_test.go", "// 001:REQ-02\nfunc TestRetry(t *testing.T) {}\n"
        )
        self.assertEqual(self.errors(), [])

    def test_tags_outside_tests_hidden_dirs_and_specs_are_ignored(self) -> None:
        self.write_test("src/app/retry.py", "# 001:REQ-09\n")
        self.write_test(".agents/skills/x/tests/test_x.py", "# 999:REQ-01\n")
        self.write_test("node_modules/pkg/tests/a.test.js", "// 999:REQ-01\n")
        self.write("notes.test.ts", "// 999:REQ-01\n")
        self.assertEqual(self.errors(), [])

    def test_verify_allkons_drive_tests_are_scanned(self) -> None:
        self.write_test(
            ".agents/skills/verify-allkons/drive/retry.spec.ts", 'test("[001:REQ-09] retries", () => {});\n'
        )
        self.write_test(".agents/skills/verify-allkons/tests/test_x.py", "# 001:REQ-08\n")
        self.write_test(".agents/skills/verify-allkons/drive/.cache/a.spec.ts", "// 001:REQ-08\n")
        self.write_test(".agents/skills/other/drive/a.spec.ts", "// 001:REQ-08\n")
        self.assertEqual([e for e in self.errors() if "REQ-08" in e], [])
        self.assert_error("tag 001:REQ-09 names an unknown requirement")

    def test_root_level_files_are_not_skipped(self) -> None:
        self.assertFalse(is_skipped(self.root / "test_root.py", self.root))
        self.assertTrue(is_skipped(self.root / ".agents" / "skills" / "x.py", self.root))

    def test_test_roots_limit_the_scan(self) -> None:
        self.write_test("other/tests/test_stale.py", '@pytest.mark.spec("001:REQ-09")\n')
        self.assert_error("tag 001:REQ-09 names an unknown requirement")
        report = check_repository(self.root, [self.root / "tests"])
        self.assertEqual(report.errors, [])

    def test_v1_spec_still_passes_with_a_warning(self) -> None:
        shutil.rmtree(self.spec_dir)
        self.spec_dir.mkdir()
        self.write("SPEC.md", V1_SPEC)
        (self.root / "specs/README.md").unlink()
        report = check_repository(self.root)
        self.assertEqual(report.errors, [])
        self.assertTrue(any("older than spec/v2" in warning for warning in report.warnings))

    def test_v2_spec_requires_kind_and_summary(self) -> None:
        text = SPEC.format(
            status="Draft", open_questions="None.", matrix=MATRIX, components="None.", summary=""
        )
        self.write("SPEC.md", text.replace("kind: feature\n", ""))
        self.assert_error("missing field 'kind'")
        self.assert_error("missing field 'summary'")

    def test_unknown_kind_fails(self) -> None:
        self.write(
            "SPEC.md",
            SPEC.format(
                status="Draft",
                open_questions="None.",
                matrix=MATRIX,
                components="None.",
                summary="x",
            ).replace("kind: feature", "kind: library"),
        )
        self.assert_error("unknown kind 'library'")

    def test_long_summary_fails(self) -> None:
        self.write_spec(summary="x" * 121)
        self.assert_error("summary is longer than 120 characters")

    def test_component_directory_must_match_kind(self) -> None:
        self.write_component(name="notification-sender")
        self.assert_error("component specs must be named NNN-component-<capability>")
        self.write_spec()
        renamed = self.root / "specs" / "001-component-retry"
        self.spec_dir.rename(renamed)
        self.spec_dir = renamed
        self.assert_error("only component specs may be named NNN-component-")

    def test_missing_happy_or_error_case_fails_once_approved(self) -> None:
        self.write_spec(matrix="| REQ-01 | edge | a | b | c | API |")
        self.assert_error("REQ-01 has no happy case in the Verification matrix")
        self.assert_error("REQ-01 has no error case in the Verification matrix")
        self.assert_error("REQ-02 has no happy case in the Verification matrix")

    def test_missing_cases_are_allowed_in_draft(self) -> None:
        self.write_spec(status="Draft", matrix="| REQ-01 | happy | a | b | c | API |")
        self.assertEqual(self.errors(), [])

    def test_unknown_case_and_matrix_req_fail(self) -> None:
        self.write_spec(
            matrix=MATRIX
            + "\n| REQ-01 | sad | a | b | c | API |\n| REQ-09 | happy | a | b | c | API |"
        )
        self.assert_error("unknown case 'sad'")
        self.assert_error("Verification matrix names unknown or removed REQ-09")

    def test_matrix_without_case_column_fails(self) -> None:
        text = SPEC.format(
            status="Draft",
            open_questions="None.",
            matrix="| REQ-01 | a | b |",
            components="None.",
            summary="Users retry a failed job from the job page.",
        ).replace(
            "| REQ | Case | Given | When | Then | Level |\n| --- | --- | --- | --- | --- | --- |",
            "| REQ | Given | When |\n| --- | --- | --- |",
        )
        self.write("SPEC.md", text)
        self.assert_error("Verification matrix table needs REQ and Case columns")

    def test_components_used_must_name_active_component_requirements(self) -> None:
        self.write_component(status="Approved")
        self.write_spec(
            components="- 002 component-notification-sender — relies on "
            "002:REQ-01, 002:REQ-02, 002:REQ-07"
        )
        write_index(self.root)
        self.assert_error("Components used names removed 002:REQ-02")
        self.assert_error("Components used names unknown 002:REQ-07")

    def test_components_used_must_name_a_component(self) -> None:
        self.write_spec(components="- 003 something — relies on 003:REQ-01")
        self.assert_error("Components used names unknown spec 003")
        other = self.root / "specs" / "003-billing"
        other.mkdir()
        (other / "SPEC.md").write_text(
            SPEC.replace('id: "001"', 'id: "003"').format(
                status="Draft",
                open_questions="None.",
                matrix=MATRIX,
                components="None.",
                summary="Billing.",
            ),
            encoding="utf-8",
        )
        self.assert_error("Components used names 003, which is not a component")

    def test_components_used_rejects_superseded_component(self) -> None:
        self.write_component(status="Superseded")
        self.write_spec(components="- 002 component-notification-sender — relies on 002:REQ-01")
        self.assert_error("Components used names superseded spec 002")

    def test_valid_component_reference_passes(self) -> None:
        self.write_component(status="Approved")
        (self.root / "specs/002-component-notification-sender/TASKS.json").write_text(
            json.dumps(
                {
                    "format": "tasks/v1",
                    "spec": "002",
                    "tasks": [{**task("T01", ["REQ-01"]), "batch": 1}],
                }
            ),
            encoding="utf-8",
        )
        (self.root / "specs/002-component-notification-sender/PLAN.md").write_text(
            PLAN.replace('spec: "001"', 'spec: "002"'), encoding="utf-8"
        )
        self.write_spec(components="- 002 component-notification-sender — relies on 002:REQ-01")
        write_index(self.root)
        self.assertEqual(self.errors(), [])

    def test_random_id_component_reference_passes(self) -> None:
        directory = self.write_component(number="k3f9x2a", status="Approved")
        (directory / "TASKS.json").write_text(
            json.dumps(
                {
                    "format": "tasks/v1",
                    "spec": "k3f9x2a",
                    "tasks": [{**task("T01", ["REQ-01"]), "batch": 1}],
                }
            ),
            encoding="utf-8",
        )
        (directory / "PLAN.md").write_text(
            PLAN.replace('spec: "001"', 'spec: "k3f9x2a"'), encoding="utf-8"
        )
        self.write_spec(
            components="- k3f9x2a component-notification-sender — relies on k3f9x2a:REQ-01"
        )
        write_index(self.root)
        self.assertEqual(self.errors(), [])

    def test_invalid_spec_id_fails(self) -> None:
        for name in ("k3f9x2-short", "K3F9X2A-upper", "01-short"):
            (self.root / "specs" / name).mkdir()
        errors = [e for e in self.errors() if "must be named <id>-short-name" in e]
        self.assertEqual(len(errors), 3, errors)

    def test_stale_index_fails_and_write_index_fixes_it(self) -> None:
        self.write_spec(summary="Retry a failed job.")
        self.assert_error("specs/README.md index is out of date")
        write_index(self.root)
        self.assertEqual(self.errors(), [])

    def test_missing_index_fails_when_a_v2_spec_exists(self) -> None:
        (self.root / "specs/README.md").unlink()
        self.assert_error("specs/README.md index is missing")

    def test_index_lists_kind_summary_and_components(self) -> None:
        self.write_component(status="Approved")
        self.write_spec(components="- 002 component-notification-sender — relies on 002:REQ-01")
        write_index(self.root)
        readme = (self.root / "specs/README.md").read_text(encoding="utf-8")
        self.assertIn(
            "| [001-retry-failed-jobs](001-retry-failed-jobs/SPEC.md) | feature | "
            "Users retry a failed job from the job page. | 002 |",
            readme,
        )
        self.assertIn(
            "| [002-component-notification-sender](002-component-notification-sender/SPEC.md) "
            "| component | Sends one notification through the configured provider. | — |",
            readme,
        )

    def test_write_index_keeps_text_outside_markers(self) -> None:
        readme = self.root / "specs/README.md"
        readme.write_text(
            "# Specs\n\nIntro.\n\n"
            "<!-- spec-index:start -->\nold\n<!-- spec-index:end -->\n\nTail.\n",
            encoding="utf-8",
        )
        write_index(self.root)
        text = readme.read_text(encoding="utf-8")
        self.assertIn("Intro.", text)
        self.assertIn("Tail.", text)
        self.assertNotIn("old", text)
        self.assertEqual(self.errors(), [])

    def write_review(
        self, verdict: str = "pass", severity: str = "blocker", resolution: str = "fixed"
    ) -> None:
        self.write(
            "SPEC_REVIEW.md",
            REVIEW.format(verdict=verdict, severity=severity, resolution=resolution),
        )

    def test_resolved_spec_review_passes(self) -> None:
        self.write_review()
        self.assertEqual(self.errors(), [])

    def test_missing_spec_review_only_warns(self) -> None:
        report = check_repository(self.root)
        self.assertEqual(report.errors, [])
        self.assertTrue(any("no SPEC_REVIEW.md" in w for w in report.warnings))

    def test_open_blocker_fails_once_approved(self) -> None:
        self.write_review(verdict="fail", resolution="open")
        self.assert_error("F01 is an open blocker or major")
        self.assert_error("spec review verdict is fail")

    def test_open_blocker_is_allowed_in_draft(self) -> None:
        self.write_spec(status="Draft")
        self.write_review(verdict="fail", resolution="open")
        self.assertEqual(self.errors(), [])

    def test_pass_verdict_with_open_major_fails(self) -> None:
        self.write_spec(status="Draft")
        self.write_review(severity="major", resolution="open")
        self.assert_error("verdict pass but F01 still open")

    def test_open_nit_does_not_block(self) -> None:
        self.write_review(severity="nit", resolution="open")
        self.assertEqual(self.errors(), [])

    def test_only_a_nit_may_be_declined(self) -> None:
        self.write_review(severity="major", resolution="declined")
        self.assert_error("F01: only a nit may be declined")

    def test_unknown_severity_and_resolution_fail(self) -> None:
        self.write_review(severity="critical", resolution="ignored")
        self.assert_error("F01: unknown severity 'critical'")
        self.assert_error("F01: unknown resolution 'ignored'")

    def test_spec_review_of_older_version_warns(self) -> None:
        self.write_review()
        self.write(
            "SPEC_REVIEW.md",
            (self.spec_dir / "SPEC_REVIEW.md").read_text().replace("1.0.0", "0.9.0", 1),
        )
        report = check_repository(self.root)
        self.assertEqual(report.errors, [])
        self.assertTrue(any("reviewed spec 0.9.0" in w for w in report.warnings))


if __name__ == "__main__":
    unittest.main()
