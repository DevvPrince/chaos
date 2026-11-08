# DESIGN.md Format (`design/v1`)

`DESIGN.md` at the repository root is the product's visual design system, readable by people and agents. It is the only source of values for `UI.md`. Create it from this template when the first UI spec needs it; never invent the brand values — ask the user (with a recommendation) like any other spec question.

Tokens are `category.name` in lowercase (`color.primary`, `space.4`, `type.label-md`). Every table whose first header cell is `Token` defines tokens. Each token maps to the concrete value the UI code uses (a CSS variable, utility class, theme key, or platform constant), so a component test can assert it.

## Template

````markdown
---
format: design/v1
version: 0.1.0
---

# Design system

## Color

| Token | Value | CSS variable | Usage |
| --- | --- | --- | --- |
| color.primary | oklch(...) | --primary | Primary actions |
| color.primary-foreground | oklch(...) | --primary-foreground | Text on primary |
| color.primary-hover | oklch(...) | --primary / 90% | Primary hover |
| color.ring | oklch(...) | --ring | Focus ring |

## Typography

| Token | Value | Usage |
| --- | --- | --- |
| type.label-md | 14px / 500 / 20px | Button and form labels |

## Spacing

| Token | Value |
| --- | --- |
| space.2 | 0.5rem (p-2) |
| space.4 | 1rem (p-4) |

## Radius

| Token | Value | CSS variable |
| --- | --- | --- |
| radius.md | calc(var(--radius) - 2px) | rounded-md |

## Shadow

| Token | Value |
| --- | --- |
| shadow.sm | shadow-sm |

## Opacity

| Token | Value |
| --- | --- |
| opacity.disabled | 0.5 |

## Icons

| Token | Value |
| --- | --- |
| icon.refresh | lucide `RefreshCw` |
| icon.spinner | lucide `Loader2` (animate-spin) |

## Component patterns

- Button: base component library `Button`; default `corners: radius.md`, `typography: type.label-md`, `shadow: null`.

## Changelog

- 0.1.0 (YYYY-MM-DD): Initial design system.
````

Raw values belong only here. Changing a token's value is a `DESIGN.md` version bump; renaming or removing one requires updating every `UI.md` that uses it (the checker fails on unknown tokens).
