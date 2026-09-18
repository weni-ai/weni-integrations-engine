# Specification Quality Checklist: Named WhatsApp Template Parameters — Integrations Engine

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-17
**Last validated**: 2026-09-17 (iteration 3, after the review pass)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [ ] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [ ] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [ ] No implementation details leak into specification

## Notes

### Validation history

- **Iteration 1**: two `[NEEDS CLARIFICATION]` markers on `FR-036` (Graph API version strategy)
  and `FR-028` (reconciliation report destination), both raised in Open Questions with options
  and implications.
- **Iteration 2**: both answered in the 2026-09-17 clarification session and folded into the
  requirements. Open Questions is now empty and the spec carries no markers.
  - Q1 → a template-scoped Graph API version now, with the fleet-wide alignment tracked as a
    separate change (`FR-038`, `FR-039`; the alignment itself moved to Out of Scope, and
    `SC-009` was rewritten to assert that the other Meta surfaces do *not* change version).
  - Q2 → an operator-triggered management command reusing the existing paced queue and
    per-WABA locks, with Redis progress and a report emitted as structured logs plus one
    exportable artifact (`FR-029` to `FR-032`; a persisted report model and read endpoint moved
    to Out of Scope).
  - Requirements were renumbered as a result.
- **Iteration 3**: a review pass raised five findings, **all five upheld and fixed**. Two were
  internal contradictions, two were factual errors about current behaviour, and one was an
  omission. Verified against the code before changing anything.
  - `FR-003` forbade inferring format from body text "on any code path" while `FR-019` required
    authoring to do exactly that. Scoped by time: the prohibition applies to templates that
    already exist at Meta; before creation the author's body is the only declaration available.
  - `GET /project/templates/details/` was wrongly treated as a template read surface. Verified
    in `usecases/template_detail.py`: `WhatsappCloudDTO` is `{app_uuid, templates_uuid}` and
    carries no template content. Removed from Story 5, `FR-035` and `SC-007`; the gap analysis
    now records it as having no gap.
  - The library creation path was asked for data it does not have. Verified in
    `_save_template_in_db()`: it writes `body = ""` and reads only `id`, `status` and `category`
    from Meta, and the request carries `library_template_name` rather than body text. A third
    format state — *not yet known* — was introduced (`FR-014`, `FR-015`, `SC-012`) so those
    rows are not defaulted to positional against the sync that later corrects them.
  - `FR-011` said "report the disagreement, don't guess" without saying what is stored, leaving
    implementers to pick a side. It now specifies the body's names as the declared set, examples
    only where Meta supplied them, and an anomaly marking retaining both sets (`SC-013`).
  - `FR-038` required raising the Graph API version without naming a target. Floor set at
    `v23.0` — the lowest version Meta's documentation demonstrates the capability on — with the
    exact target pinned in planning, since Meta's changelog does not record the introducing
    version and Graph versions expire.
  - Requirements renumbered again: the spec now runs `FR-001` to `FR-044`, with `SC-001` to
    `SC-013` and `NFR-001` to `NFR-009`. Verified contiguous, with no dangling internal
    cross-references and no product-spec (`PS FR-nnn`) or `NFR-nnn` id altered by the renumber.

**Nothing blocking remains. The spec is ready for `/speckit-plan`.**

### Deliberate deviations — audience and technical detail

Four items remain unchecked by design rather than by omission, because this is an **engineering
spec for one service**, derived from an already-ratified product spec whose solution
architecture is decided:

- *No implementation details* / *Written for non-technical stakeholders* / *No implementation
  details leak* — the upstream product spec (`008-named-template-variables`, commit `8bf459d`)
  assigns five named responsibilities to `weni-integrations-engine`, and its governance note
  explicitly permits a spec to define the HOW "when those decisions have already been made".
  The request was to evaluate what needs to change in this repository, so the *Current State &
  Gap Analysis* section names the current models, tasks, use cases, serializers and settings.
  Without those names the scope would be unverifiable and a reviewer could not tell which of the
  five repositories a requirement belongs to. The requirements themselves are written as
  behaviour and avoid prescribing field names, types or module layout — those are left to
  `/speckit-plan`.
- *Success criteria are technology-agnostic* — `SC-009` necessarily references the Meta Graph API
  version, because upstream `FR-050` / `BD-014` make the provider API version a first-class
  requirement rather than an implementation choice.

### Cross-service boundary check

Verified that no requirement in this spec belongs to another repository. In particular, the
product spec's header/footer variable skip, its parameter policy, its broadcast contract
validation, its per-recipient resolution and its `parameter_name` payload assembly are all owned
by `engineering/flows`, `engineering/mailroom`, `weni-ai/goflow` and `engineering/courier`, and
are listed under Out of Scope so they are not built twice.
