# UI.md Component Spec (`ui/v1`)

`UI.md` sits next to `SPEC.md` and specifies every user-interface component the feature adds or changes. It turns visual intent into values a test can check. Every visual value comes from the root `DESIGN.md` ([design-md-format.md](design-md-format.md)); if a needed token does not exist, add it to `DESIGN.md` in Stage 1 so Gate 1 reviews it.

## Allowed values

Every value cell (and every value inside a state change) is one or more of:

| Kind | Example | Meaning |
| --- | --- | --- |
| Token | `color.primary`, `radius.md`, `space.2 space.4` | Defined in `DESIGN.md` |
| Quoted literal | `"Retry"` | User-visible copy, exactly as shown |
| `null` | `null` | Explicitly none (no shadow, no icon) |
| Boolean | `true`, `false` | Flags such as `full-width` |
| Note | `(leading)` | A trailing qualifier in parentheses |

Raw colors (`#2563eb`, `rgb(...)`), raw sizes (`16px`, `1rem`, `50%`), and free words (`blue`, `rounded`) are rejected by the checker. Unspecified properties inherit from the base component's defaults in `DESIGN.md`; write `null` when "none" is intended.

## Template

````markdown
---
format: ui/v1
spec: "NNN"
version: 0.1.0
---

# NNN Feature name — UI

### UI-01 RetryButton

Implements: REQ-03 · Base: `Button` · Location: `src/features/jobs/components/`

| Property | Value |
| --- | --- |
| background | color.primary |
| text-color | color.primary-foreground |
| corners | radius.md |
| text | "Retry" |
| typography | type.label-md |
| padding | space.2 space.4 |
| shadow | null |
| icon | icon.refresh (leading) |

| State | Changes |
| --- | --- |
| hover | background: color.primary-hover |
| disabled | opacity: opacity.disabled |
| loading | text: "Retrying…"; icon: icon.spinner |
| focus | ring: color.ring |

Behavior: clicking sends the retry request; the button is disabled while the request is in flight (REQ-03).

Accessibility: role `button`, accessible name "Retry".

## Changelog

- 0.1.0 (YYYY-MM-DD): Initial UI spec.
````

## Rules

- Heading: `### UI-NN ComponentName`. UI IDs are permanent like REQ IDs.
- `Implements:` names the REQ IDs whose tests cover this component. Visual properties are tested at component level (rendered text, role, and the classes, variables, or style values the tokens map to); journeys in an end-to-end test.
- The property table header is `| Property | Value |`; the state table header is `| State | Changes |` with `property: value` pairs separated by `;`.
- Describe behavior and accessibility in prose under the tables; tie each to a REQ ID.
- Version and Changelog follow the same rules as `SPEC.md`.
