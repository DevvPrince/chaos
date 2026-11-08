# Spec Catalog: Naming, Locate, and Components

`specs/` is a catalog of what the system does: one spec per **feature** and one per **component**. A change is never its own spec; it edits the spec that owns the behavior. That keeps one statement of truth per capability, so an agent can find it by skimming.

## Kinds

| Kind | What it specifies | Folder name |
| --- | --- | --- |
| `feature` | A user-facing capability: its flows, contracts, and rules | `NNN-<feature>` (e.g. `001-dev-workflow`) |
| `component` | A shared capability that two or more features rely on: a backend module (notification sender, auth guard), a UI component, or an integration | `NNN-component-<capability>` (e.g. `009-component-notification-sender`) |

## Naming

- The slug names the capability, not the change: a noun phrase of 2–4 lowercase words joined by `-` (`dev-workflow`, `component-otp-verification`). Never `fix-...`, `retry-loop`, `v2`, or a ticket number.
- `NNN` is the spec ID. New specs get a random 7-character ID from `[a-z0-9]` (e.g. `k3f9x2a-dev-workflow`), never a sequential number, so parallel sessions and branches cannot pick the same one. Existing 3-digit IDs stay valid and are never renamed. IDs are never reused, including retired ones listed in `specs/README.md`.
- `SPEC.md` frontmatter carries `kind` and `summary`: one line (at most 120 characters) saying what the spec owns, written so a reader can decide from it alone whether to open the spec.
- `specs/README.md` holds the index the checker generates from the folders and frontmatter (`check_spec_traceability.py --write-index`). The checker fails when it is out of date, so update it in the same change that adds or renames a spec or edits a `summary` or `Components used`.

## Stage 0: Locate

Before writing anything, decide which spec owns the request.

1. Read the index in `specs/README.md`. For each candidate whose summary could own the request, read only its `Observable behavior` and `Components used`; open more only when that is not enough.
2. Classify the request as one or more of:
   - **Edit feature**: the behavior belongs to an existing feature spec (new rule, changed flow, bug fix, extra case).
   - **Edit component**: the behavior belongs to a shared capability that already has a component spec.
   - **New feature**: no feature spec owns it.
   - **New component**: a capability a feature needs already exists inside another feature, or is needed by a second feature now (see Components).
   A request can be several at once: for example a new feature that needs a change to a component. All of them go through the same Gate 1.
3. If the owner is unclear, or two specs could plausibly own it, ask the user before writing. Never guess. Use the clarification shape from [spec-format.md](spec-format.md):

```text
Q1. Should "limit Retry to 3 attempts per batch" change 001-dev-workflow, or be a new feature?
Recommendation: edit 001-dev-workflow, because Retry and attempt limits are already its REQ-17.
Alternatives: (a) new feature spec; (b) a new component if other features will retry too.
```

4. State the classification and the target spec(s) in your first message of Stage 1.

## Editing an existing spec

- Work in the owning spec's folder. Add new REQs with the next free number, mark changed ones `[changed X.Y.Z]` and removed ones `[removed X.Y.Z]`; never renumber ([spec-format.md](spec-format.md#requirement-ids)).
- Bump `version` (minor for added or changed behavior, major for removed behavior or broken contracts), add a Changelog line, and set `status` back to `Draft` until Gate 1 approves the change.
- Add Verification matrix rows for every new or changed REQ, with happy and error cases ([spec-format.md](spec-format.md#test-cases)).
- `PLAN.md` gets a new subsection for the change. New tasks continue the existing ID sequence (`T41`, `T42`, ...) in a new batch after the highest one; `done` tasks stay as they are. If the change breaks behavior an old task delivered, add a new task for it; do not reopen the old one.
- Review passes are appended to the existing `SPEC_REVIEW.md` and cover only the changed REQs.
- Audit sections are appended to the existing `AUDIT_REPORT.md`.
- Tests keep citing the owning spec: `NNN:REQ-NN`.

## Components

- A component spec is the only place its behavior is defined. A feature that relies on it lists it under `## Components used`, one line per component, naming the REQs it relies on:

  ```markdown
  ## Components used

  - 009 component-notification-sender — relies on 009:REQ-01, 009:REQ-03
  ```

  Write `None.` when there are none. The feature does not restate the component's behavior; its own REQs cover only how it uses the component (when it sends, with what content, what it does on failure).
- If a feature needs the component to behave differently, that is an **Edit component** in the same request: change the component spec and get it approved in the same Gate 1.
- Create a component spec only when a second feature needs a capability (extract it then, moving the REQs out of the first feature: mark them `[removed X.Y.Z]` with "moved to NNN:REQ-MM" and retag their tests) or when the user asks for one. Do not create one speculatively for a single feature.
- Component tests are tagged with the component's ID; feature tests tag only the feature's REQs.
- The checker fails when `Components used` names a spec that is missing, is not a component, is `Superseded`, or names a REQ that is unknown or removed.
- Before changing a component, check the index's `Components used` column for every feature that relies on it, and include their affected behavior in the spec change.
