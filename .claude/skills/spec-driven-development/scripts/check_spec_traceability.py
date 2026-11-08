#!/usr/bin/env python3
"""Check specs/ artifacts, task state, spec reviews, UI tokens, case coverage, the index, and REQ-to-test tags.

Rules are documented in ../references/traceability.md. Standard library only so CI can
run it without installing a project.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# The last version listed for each artifact is current; older ones only warn.
SUPPORTED_FORMATS: dict[str, tuple[str, ...]] = {
    "spec": ("v1", "v2"),
    "ui": ("v1",),
    "plan": ("v1",),
    "tasks": ("v1",),
    "audit": ("v1",),
    "spec-review": ("v1",),
    "design": ("v1",),
}
REQUIRED_FIELDS: dict[tuple[str, str], tuple[str, ...]] = {
    ("spec", "v1"): ("id", "title", "status", "version"),
    ("spec", "v2"): ("id", "title", "kind", "summary", "status", "version"),
    ("ui", "v1"): ("spec", "version"),
    ("plan", "v1"): ("spec", "version"),
    ("tasks", "v1"): ("spec", "tasks"),
    ("audit", "v1"): ("spec", "verdict"),
    ("spec-review", "v1"): ("spec", "spec_version", "verdict"),
    ("design", "v1"): ("version",),
}
REQUIRED_SECTIONS: dict[tuple[str, str], tuple[str, ...]] = {
    ("spec", "v1"): (
        "Problem and outcome",
        "Observable behavior",
        "Non-goals",
        "Interface contracts",
        "Verification matrix",
        "Operational constraints",
        "Open questions",
        "Approval record",
        "Changelog",
    ),
    ("spec", "v2"): (
        "Problem and outcome",
        "Observable behavior",
        "Non-goals",
        "Interface contracts",
        "Components used",
        "Verification matrix",
        "Operational constraints",
        "Open questions",
        "Approval record",
        "Changelog",
    ),
    ("ui", "v1"): ("Changelog",),
    ("plan", "v1"): ("Approach", "Tasks", "Changelog"),
    ("audit", "v1"): (),
    ("spec-review", "v1"): (),
    ("design", "v1"): ("Changelog",),
}

SPEC_STATUSES = ("Draft", "Approved", "In progress", "Implemented", "Superseded")
GATED_STATUSES = frozenset({"Approved", "In progress", "Implemented"})
TASK_STATUSES = frozenset({"todo", "in_progress", "done", "blocked"})
SPEC_KINDS = frozenset({"feature", "component"})
CASES = frozenset({"happy", "edge", "error"})
REQUIRED_CASES = ("happy", "error")
SEVERITIES = frozenset({"blocker", "major", "nit"})
RESOLUTIONS = frozenset({"open", "fixed", "contested", "declined"})
GATING_SEVERITIES = frozenset({"blocker", "major"})
SUMMARY_MAX = 120
COMPONENT_PREFIX = "component-"
INDEX_START = "<!-- spec-index:start -->"
INDEX_END = "<!-- spec-index:end -->"

# Legacy specs use a 3-digit number; new specs use a random 7-character id.
SPEC_ID = r"(?:\d{3}|[a-z0-9]{7})"
SPEC_DIR_RE = re.compile(rf"^({SPEC_ID})-[a-z0-9-]+$")
REQ_DEF_RE = re.compile(
    r"^\s*[-*]\s+\*\*(REQ-\d{2,})\*\*\s*(?:\[(changed|removed)\b[^\]]*\])?", re.MULTILINE
)
REQ_RE = re.compile(r"\bREQ-\d{2,}\b")
TAG_RE = re.compile(rf"\b({SPEC_ID}):(REQ-\d{{2,}})\b")
COMPONENT_LINE_RE = re.compile(rf"^\s*[-*]\s+({SPEC_ID})\b", re.MULTILINE)
TASK_ID_RE = re.compile(r"^T\d{2,}$")
PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO)\b")
TOKEN_RE = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z0-9-]+)+$")
VALUE_PART_RE = re.compile(r'"[^"]*"|“[^”]*”|\([^)]*\)|\S+')
NONE_TEXT = frozenset({"", "none", "none."})

# Language-agnostic test discovery: a source file counts as a test when its name follows a
# common test convention or it sits in a conventional test directory.
SOURCE_SUFFIXES = frozenset(
    ".py .ts .tsx .js .jsx .mts .mjs .cjs .go .rs .java .kt .kts .scala .rb .cs .fs .swift "
    ".php .ex .exs .dart .sh .bash .bats .hcl".split()
)
TEST_NAME_RE = re.compile(r"(^test_|_test\.|\.test\.|\.spec\.|_spec\.|Tests?\.|\.tftest\.hcl$)")
TEST_DIRS = frozenset({"test", "tests", "__tests__", "spec", "e2e", "integration_tests"})
# Hidden directories (".git", ".venv", ".agents", ...) are skipped as well.
SKIPPED_DIRS = frozenset(
    {"node_modules", "venv", "__pycache__", "dist", "build", "target", "vendor", "coverage"}
)
# Hidden directories that hold runtime-evidence tests and are scanned anyway, with every
# directory on the way down to them.
SCANNED_HIDDEN_DIRS: tuple[tuple[str, ...], ...] = ((".agents", "skills", "verify-allkons", "drive"),)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, where: Path | str, message: str) -> None:
        self.errors.append(f"{where}: {message}")

    def warn(self, where: Path | str, message: str) -> None:
        self.warnings.append(f"{where}: {message}")


@dataclass
class Spec:
    number: str
    directory: Path
    status: str
    version: str
    active_reqs: set[str]
    removed_reqs: set[str]
    format_version: str = "v1"
    kind: str = "feature"
    summary: str = ""
    components_used: str = ""


def parse_frontmatter(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip().strip("\"'")
    return None


def parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = sections.setdefault(line[3:].strip(), [])
        elif current is not None:
            current.append(line)
    return {name: "\n".join(body).strip() for name, body in sections.items()}


def check_format(
    report: Report, path: Path, declared: object, kind: str, fields: dict[str, object]
) -> str | None:
    """Validate `format: <kind>/vN` and required fields; return the version if usable."""
    supported = SUPPORTED_FORMATS[kind]
    if not isinstance(declared, str) or "/" not in declared:
        report.error(path, f"missing format (expected {kind}/{supported[-1]})")
        return None
    name, _, version = declared.partition("/")
    if name != kind or version not in supported:
        report.error(
            path, f"unknown format {declared!r} (supported: {kind}/{', '.join(supported)})"
        )
        return None
    if version != supported[-1]:
        report.warn(path, f"format {declared} is older than {kind}/{supported[-1]}")
    for required in REQUIRED_FIELDS[(kind, version)]:
        if fields.get(required) in (None, ""):
            report.error(path, f"missing field {required!r}")
    return version


def check_markdown(
    report: Report, path: Path, kind: str
) -> tuple[str, dict[str, str], dict[str, str]] | None:
    text = path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)
    if frontmatter is None:
        report.error(path, "missing frontmatter")
        return None
    version = check_format(report, path, frontmatter.get("format"), kind, dict(frontmatter))
    if version is None:
        return None
    sections = parse_sections(text)
    for section in REQUIRED_SECTIONS[(kind, version)]:
        if section not in sections:
            report.error(path, f"missing section '## {section}'")
    return text, frontmatter, sections


def load_spec(report: Report, directory: Path, number: str) -> Spec | None:
    path = directory / "SPEC.md"
    if not path.is_file():
        report.error(directory, "missing SPEC.md")
        return None
    checked = check_markdown(report, path, "spec")
    if checked is None:
        return None
    text, frontmatter, sections = checked

    if frontmatter.get("id") != number:
        report.error(
            path, f"id {frontmatter.get('id')!r} does not match directory number {number!r}"
        )
    status = frontmatter.get("status", "")
    if status not in SPEC_STATUSES:
        report.error(
            path, f"unknown status {status!r} (expected one of {', '.join(SPEC_STATUSES)})"
        )

    active: set[str] = set()
    removed: set[str] = set()
    for match in REQ_DEF_RE.finditer(text):
        req, marker = match.group(1), match.group(2)
        if req in active or req in removed:
            report.error(path, f"{req} is defined more than once")
        (removed if marker == "removed" else active).add(req)

    if status in GATED_STATUSES:
        if not active:
            report.error(path, "no REQ definitions ('- **REQ-01**: ...')")
        if sections.get("Open questions", "").strip().lower() not in NONE_TEXT:
            report.error(path, f"status {status} but 'Open questions' is not empty")
        for placeholder in sorted(set(PLACEHOLDER_RE.findall(text))):
            report.error(path, f"status {status} but contains {placeholder}")

    spec = Spec(number, directory, status, frontmatter.get("version", ""), active, removed)
    spec.summary = frontmatter.get("title", "")
    if frontmatter.get("format") == "spec/v2":
        spec.format_version = "v2"
        spec.kind = frontmatter.get("kind", "")
        spec.summary = frontmatter.get("summary", "")
        spec.components_used = sections.get("Components used", "")
        check_v2_spec(report, path, spec, sections.get("Verification matrix", ""))
    return spec


def check_v2_spec(report: Report, path: Path, spec: Spec, matrix: str) -> None:
    """Kind, folder name, summary, and happy/edge/error rows of the Verification matrix."""
    if spec.kind and spec.kind not in SPEC_KINDS:
        report.error(path, f"unknown kind {spec.kind!r} (expected feature or component)")
    is_component_dir = spec.directory.name.startswith(f"{spec.number}-{COMPONENT_PREFIX}")
    if spec.kind == "component" and not is_component_dir:
        report.error(spec.directory, "component specs must be named NNN-component-<capability>")
    if spec.kind == "feature" and is_component_dir:
        report.error(spec.directory, "only component specs may be named NNN-component-...")
    if len(spec.summary) > SUMMARY_MAX:
        report.error(path, f"summary is longer than {SUMMARY_MAX} characters")

    cases: dict[str, set[str]] = {}
    for header, rows in iter_tables(matrix):
        names = [cell.lower() for cell in header]
        if "req" not in names or "case" not in names:
            report.error(path, "Verification matrix table needs REQ and Case columns")
            continue
        req_column, case_column = names.index("req"), names.index("case")
        for row in rows:
            if len(row) <= max(req_column, case_column):
                continue
            case = row[case_column].strip("` ").lower()
            if case not in CASES:
                report.error(
                    path, f"Verification matrix row {row[req_column]}: unknown case {case!r}"
                )
            for req in REQ_RE.findall(row[req_column]):
                if req not in spec.active_reqs:
                    report.error(path, f"Verification matrix names unknown or removed {req}")
                cases.setdefault(req, set()).add(case)
    if spec.status in GATED_STATUSES:
        for req in sorted(spec.active_reqs):
            for case in REQUIRED_CASES:
                if case not in cases.get(req, set()):
                    report.error(path, f"{req} has no {case} case in the Verification matrix")


def check_components_used(report: Report, spec: Spec, specs: dict[str, Spec]) -> None:
    where = spec.directory / "SPEC.md"
    referenced = set(COMPONENT_LINE_RE.findall(spec.components_used))
    referenced.update(number for number, _ in TAG_RE.findall(spec.components_used))
    for number in sorted(referenced):
        component = specs.get(number)
        if component is None:
            report.error(where, f"Components used names unknown spec {number}")
        elif component.kind != "component":
            report.error(where, f"Components used names {number}, which is not a component")
        elif component.status == "Superseded":
            report.error(where, f"Components used names superseded spec {number}")
    for number, req in TAG_RE.findall(spec.components_used):
        component = specs.get(number)
        if component is None or component.kind != "component":
            continue
        if req in component.removed_reqs:
            report.error(where, f"Components used names removed {number}:{req}")
        elif req not in component.active_reqs:
            report.error(where, f"Components used names unknown {number}:{req}")


def render_index(specs: dict[str, Spec]) -> str:
    lines = ["| Spec | Kind | Summary | Components used |", "| --- | --- | --- | --- |"]
    for number in sorted(specs):
        spec = specs[number]
        name = spec.directory.name
        used = sorted(
            set(COMPONENT_LINE_RE.findall(spec.components_used))
            | {n for n, _ in TAG_RE.findall(spec.components_used)}
        )
        kind = spec.kind if spec.format_version != "v1" else "—"
        summary = spec.summary.replace("|", "\\|")
        lines.append(
            f"| [{name}]({name}/SPEC.md) | {kind} | {summary} | {', '.join(used) or '—'} |"
        )
    return "\n".join(lines)


def index_block(specs: dict[str, Spec]) -> str:
    return f"{INDEX_START}\n{render_index(specs)}\n{INDEX_END}"


def check_index(report: Report, root: Path, specs: dict[str, Spec]) -> None:
    if not any(spec.format_version != "v1" for spec in specs.values()):
        return
    path = root / "specs" / "README.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if INDEX_START not in text or INDEX_END not in text:
        report.error(path, "specs/README.md index is missing; run with --write-index")
    elif index_block(specs) not in text:
        report.error(path, "specs/README.md index is out of date; run with --write-index")


def write_index(root: Path) -> None:
    """Rewrite the index between the markers in specs/README.md, creating them if absent."""
    specs = load_specs(Report(), root)
    path = root / "specs" / "README.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else "# Specs\n"
    block = index_block(specs)
    if INDEX_START in text and INDEX_END in text:
        head, _, rest = text.partition(INDEX_START)
        _, _, tail = rest.partition(INDEX_END)
        text = f"{head}{block}{tail}"
    else:
        text = f"{text.rstrip()}\n\n## Index\n\n{block}\n"
    path.write_text(text, encoding="utf-8")


def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    visiting: list[str] = []
    done: set[str] = set()

    def visit(node: str) -> list[str] | None:
        if node in visiting:
            return [*visiting[visiting.index(node) :], node]
        if node in done:
            return None
        visiting.append(node)
        for dependency in graph.get(node, []):
            cycle = visit(dependency)
            if cycle:
                return cycle
        visiting.pop()
        done.add(node)
        return None

    for node in graph:
        cycle = visit(node)
        if cycle:
            return cycle
    return None


def check_tasks(report: Report, spec: Spec) -> set[str]:
    """Validate TASKS.json and return the REQs covered by done tasks."""
    path = spec.directory / "TASKS.json"
    gated = spec.status in GATED_STATUSES
    if not path.is_file():
        if gated:
            report.error(spec.directory, f"status {spec.status} requires TASKS.json")
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        report.error(path, f"invalid JSON: {error}")
        return set()
    if not isinstance(data, dict):
        report.error(path, "top level must be an object")
        return set()
    if check_format(report, path, data.get("format"), "tasks", data) is None:
        return set()
    if data.get("spec") != spec.number:
        report.error(path, f"spec {data.get('spec')!r} does not match {spec.number!r}")
    spec_version = data.get("spec_version")
    if spec_version and spec_version != spec.version:
        report.warn(path, f"planned against spec {spec_version}, spec is now {spec.version}")

    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        report.error(path, "'tasks' must be a list")
        return set()

    by_id: dict[str, dict[str, object]] = {}
    for index, task in enumerate(tasks):
        if not isinstance(task, dict) or not isinstance(task.get("id"), str):
            report.error(path, f"task #{index + 1} must be an object with a string 'id'")
            continue
        task_id = task["id"]
        if not TASK_ID_RE.match(task_id):
            report.error(path, f"task id {task_id!r} must look like T01")
        if task_id in by_id:
            report.error(path, f"duplicate task id {task_id}")
        by_id[task_id] = task

    covered: set[str] = set()
    done_reqs: set[str] = set()
    graph: dict[str, list[str]] = {}
    for task_id, task in by_id.items():
        where = f"{path} {task_id}"
        reqs = task.get("reqs")
        depends_on = task.get("depends_on", [])
        status = task.get("status")
        if not isinstance(reqs, list) or not reqs:
            report.error(where, "'reqs' must be a non-empty list")
            reqs = []
        if not isinstance(depends_on, list):
            report.error(where, "'depends_on' must be a list")
            depends_on = []
        if not isinstance(task.get("batch"), int):
            report.error(where, "'batch' must be an integer")
        if status not in TASK_STATUSES:
            report.error(
                where, f"unknown status {status!r} (expected {', '.join(sorted(TASK_STATUSES))})"
            )

        for req in reqs:
            if req in spec.removed_reqs:
                report.error(where, f"references removed {req}")
            elif req not in spec.active_reqs:
                report.error(where, f"references unknown {req}")
            else:
                covered.add(req)
        graph[task_id] = [str(dependency) for dependency in depends_on]
        for dependency in graph[task_id]:
            if dependency not in by_id:
                report.error(where, f"depends on unknown task {dependency}")

        if status == "done":
            evidence = task.get("evidence")
            evidence = evidence if isinstance(evidence, dict) else {}
            if not task.get("completed_at"):
                report.error(where, "done but missing 'completed_at'")
            for phase in ("red", "green"):
                if not evidence.get(phase):
                    report.error(where, f"done but missing evidence.{phase}")
            if not task.get("changed_files"):
                report.error(where, "done but missing 'changed_files'")
            for dependency in graph[task_id]:
                if dependency in by_id and by_id[dependency].get("status") != "done":
                    report.error(where, f"done but depends on unfinished {dependency}")
            done_reqs.update(req for req in reqs if req in spec.active_reqs)
        elif status == "blocked" and not task.get("blocked_reason"):
            report.error(where, "blocked but missing 'blocked_reason'")
        if spec.status == "Implemented" and status != "done":
            report.error(where, f"spec is Implemented but task is {status}")

    cycle = find_cycle(graph)
    if cycle:
        report.error(path, f"dependency cycle: {' -> '.join(cycle)}")
    if gated:
        for req in sorted(spec.active_reqs - covered):
            report.error(path, f"{req} is not covered by any task")
    return done_reqs


def collect_design_tokens(report: Report, root: Path) -> set[str] | None:
    path = root / "DESIGN.md"
    if not path.is_file():
        return None
    if check_markdown(report, path, "design") is None:
        return set()
    tokens: set[str] = set()
    for header, rows in iter_tables(path.read_text(encoding="utf-8")):
        if header and header[0].lower() == "token":
            tokens.update(row[0].strip("` ") for row in rows if row)
    return tokens


def iter_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    tables: list[tuple[list[str], list[list[str]]]] = []
    block: list[list[str]] = []
    for line in [*text.splitlines(), ""]:
        stripped = line.strip()
        if stripped.startswith("|"):
            block.append([cell.strip() for cell in stripped.strip("|").split("|")])
            continue
        if block:
            rows = [
                row for row in block[1:] if not all(re.fullmatch(r":?-+:?", cell) for cell in row)
            ]
            tables.append((block[0], rows))
            block = []
    return tables


def check_ui_value(report: Report, where: str, value: str, tokens: set[str]) -> None:
    parts = VALUE_PART_RE.findall(value)
    if not parts:
        report.error(where, "empty value (write null for none)")
    for part in parts:
        bare = part.strip("`")
        if part[0] in '"“(' or bare in ("null", "true", "false"):
            continue
        if TOKEN_RE.match(bare):
            if bare not in tokens:
                report.error(where, f"unknown DESIGN.md token {bare!r}")
            continue
        report.error(where, f"raw value {part!r}; use a DESIGN.md token, a quoted literal, or null")


def check_ui(report: Report, spec: Spec, tokens: set[str] | None) -> None:
    path = spec.directory / "UI.md"
    if not path.is_file():
        return
    checked = check_markdown(report, path, "ui")
    if checked is None:
        return
    text, frontmatter, _ = checked
    if frontmatter.get("spec") != spec.number:
        report.error(path, f"spec {frontmatter.get('spec')!r} does not match {spec.number!r}")
    if spec.status in GATED_STATUSES:
        for placeholder in sorted(set(PLACEHOLDER_RE.findall(text))):
            report.error(path, f"status {spec.status} but contains {placeholder}")
    for line in text.splitlines():
        if line.startswith("Implements:"):
            for req in REQ_RE.findall(line):
                if req not in spec.active_reqs:
                    report.error(path, f"Implements unknown or removed {req}")
    if tokens is None:
        report.error(path, "UI.md requires a root DESIGN.md")
        return

    for header, rows in iter_tables(text):
        names = [cell.lower() for cell in header]
        for row in rows:
            if len(row) < 2:
                continue
            where = f"{path} [{row[0]}]"
            if names[:2] == ["property", "value"]:
                check_ui_value(report, where, row[1], tokens)
            elif names[:2] == ["state", "changes"]:
                for change in filter(None, (part.strip() for part in row[1].split(";"))):
                    prop, sep, value = change.partition(":")
                    if not sep:
                        report.error(where, f"state change {change!r} must be 'property: value'")
                    else:
                        check_ui_value(report, f"{where} {prop.strip()}", value.strip(), tokens)


def check_audit(report: Report, spec: Spec) -> None:
    path = spec.directory / "AUDIT_REPORT.md"
    if not path.is_file():
        return
    checked = check_markdown(report, path, "audit")
    if checked is not None and checked[1].get("verdict") not in ("pass", "fail"):
        report.error(path, "verdict must be pass or fail")


def check_spec_review(report: Report, spec: Spec) -> None:
    path = spec.directory / "SPEC_REVIEW.md"
    if not path.is_file():
        if spec.status in GATED_STATUSES:
            report.warn(spec.directory, f"status {spec.status} but no SPEC_REVIEW.md")
        return
    checked = check_markdown(report, path, "spec-review")
    if checked is None:
        return
    text, frontmatter, _ = checked
    if frontmatter.get("spec") != spec.number:
        report.error(path, f"spec {frontmatter.get('spec')!r} does not match {spec.number!r}")
    verdict = frontmatter.get("verdict")
    if verdict not in ("pass", "fail"):
        report.error(path, "verdict must be pass or fail")
    if frontmatter.get("spec_version") not in (None, "", spec.version):
        report.warn(path, f"reviewed spec {frontmatter.get('spec_version')}, spec is {spec.version}")

    unresolved: list[str] = []
    for header, rows in iter_tables(text):
        columns = [cell.lower() for cell in header]
        if "severity" not in columns or "resolution" not in columns:
            continue
        severity_at, resolution_at = columns.index("severity"), columns.index("resolution")
        for row in rows:
            finding = row[0] if row else "?"
            severity = row[severity_at].lower() if severity_at < len(row) else ""
            resolution = row[resolution_at].lower() if resolution_at < len(row) else ""
            if severity not in SEVERITIES:
                report.error(path, f"{finding}: unknown severity {severity!r}")
            if resolution not in RESOLUTIONS:
                report.error(path, f"{finding}: unknown resolution {resolution!r}")
            elif resolution == "declined" and severity != "nit":
                report.error(path, f"{finding}: only a nit may be declined")
            elif resolution == "open" and severity in GATING_SEVERITIES:
                unresolved.append(finding)

    if unresolved and verdict == "pass":
        report.error(path, f"verdict pass but {', '.join(unresolved)} still open")
    if spec.status in GATED_STATUSES:
        if verdict == "fail":
            report.error(path, f"status {spec.status} but the spec review verdict is fail")
        for finding in unresolved:
            report.error(path, f"status {spec.status} but {finding} is an open blocker or major")


def check_plan(report: Report, spec: Spec) -> None:
    path = spec.directory / "PLAN.md"
    if not path.is_file():
        if spec.status in GATED_STATUSES:
            report.error(spec.directory, f"status {spec.status} requires PLAN.md")
        return
    checked = check_markdown(report, path, "plan")
    if checked is not None and checked[1].get("spec") != spec.number:
        report.error(path, f"spec {checked[1].get('spec')!r} does not match {spec.number!r}")


def is_test_file(path: Path, root: Path) -> bool:
    if path.suffix not in SOURCE_SUFFIXES:
        return False
    directories = path.relative_to(root).parts[:-1]
    return bool(TEST_NAME_RE.search(path.name)) or bool(TEST_DIRS.intersection(directories))


def is_skipped(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts
    if parts[:1] == ("specs",):
        return True
    directories = parts[:-1]
    for allowed in SCANNED_HIDDEN_DIRS:
        depth = min(len(directories), len(allowed))
        # A path at the root has no directories and is not under the allowed directory.
        if directories and directories[:depth] == allowed[:depth]:
            if len(directories) < len(allowed):
                # `_` is the probe name callers use to ask about a directory itself.
                return parts[-1] != "_"  # skip files above it; walk directories down
            directories = directories[len(allowed):]
            break
    return any(part.startswith(".") or part in SKIPPED_DIRS for part in directories)


def collect_tags(
    root: Path, test_roots: list[Path] | None = None
) -> dict[tuple[str, str], list[Path]]:
    tags: dict[tuple[str, str], list[Path]] = {}
    root = root.resolve()
    for test_root in test_roots or [root]:
        test_root = test_root.resolve()
        if not test_root.is_relative_to(root):
            continue
        if not test_root.is_dir():
            continue
        # Explicit roots must obey the same exclusions as a walk from the root,
        # including catalog boundaries above the requested directory.
        if is_skipped(test_root / "_", root) or any(
            (directory / "specs" / "README.md").is_file()
            for directory in (test_root, *test_root.parents)
            if directory != root and directory.is_relative_to(root)
        ):
            continue
        candidates: list[Path] = []
        for directory, subdirs, filenames in os.walk(test_root):
            current = Path(directory)
            # Prune before descending: dependencies and independent projects can
            # be large, and their tests belong to a different catalog.
            subdirs[:] = [
                name for name in subdirs
                if not is_skipped(current / name / "_", root)
                and not (current / name / "specs" / "README.md").is_file()
            ]
            candidates.extend(
                current / name for name in filenames if is_test_file(current / name, root)
            )
        for path in sorted(candidates):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for number, req in TAG_RE.findall(text):
                tags.setdefault((number, req), []).append(path.relative_to(root))
    return tags


def load_specs(report: Report, root: Path) -> dict[str, Spec]:
    specs_root = root / "specs"
    specs: dict[str, Spec] = {}
    spec_dirs = (
        sorted(path for path in specs_root.iterdir() if path.is_dir())
        if specs_root.is_dir()
        else []
    )
    numbers_seen: set[str] = set()
    for directory in spec_dirs:
        match = SPEC_DIR_RE.match(directory.name)
        if not match:
            report.error(directory, "spec directories must be named <id>-short-name (7-character [a-z0-9] id, or legacy NNN)")
            continue
        number = match.group(1)
        if number in numbers_seen:
            report.error(directory, f"spec id {number} is used twice")
        numbers_seen.add(number)
        spec = load_spec(report, directory, number)
        if spec is not None:
            specs[number] = spec
    return specs


def check_repository(root: Path, test_roots: list[Path] | None = None) -> Report:
    report = Report()
    specs = load_specs(report, root)
    check_index(report, root, specs)

    tokens = collect_design_tokens(report, root)
    tags = collect_tags(root, test_roots)

    for spec in specs.values():
        check_plan(report, spec)
        done_reqs = check_tasks(report, spec)
        check_ui(report, spec, tokens)
        check_audit(report, spec)
        check_spec_review(report, spec)
        check_components_used(report, spec, specs)
        required = set(spec.active_reqs) if spec.status == "Implemented" else done_reqs
        for req in sorted(required):
            if (spec.number, req) not in tags:
                report.error(spec.directory, f"{req} has no test tagged {spec.number}:{req}")

    for (number, req), paths in sorted(tags.items()):
        where = ", ".join(str(path) for path in paths)
        spec = specs.get(number)
        if spec is None:
            report.error(where, f"tag {number}:{req} names an unknown spec")
        elif req in spec.removed_reqs:
            report.error(where, f"tag {number}:{req} names a removed requirement")
        elif req not in spec.active_reqs:
            report.error(where, f"tag {number}:{req} names an unknown requirement")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="repository root (default: cwd)"
    )
    parser.add_argument(
        "--test-root",
        type=Path,
        action="append",
        default=[],
        help="directory to scan for tagged tests, relative to --root; repeatable "
        "(default: the whole repository)",
    )
    parser.add_argument(
        "--write-index",
        action="store_true",
        help="rewrite the spec index in specs/README.md before checking",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.write_index:
        write_index(root)
    test_roots = [root / test_root for test_root in args.test_root] or None
    report = check_repository(root, test_roots)
    for warning in report.warnings:
        print(f"warning: {warning}")
    for error in report.errors:
        print(f"error: {error}")
    print(f"spec traceability: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
