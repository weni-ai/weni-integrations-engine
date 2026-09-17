<!--
Sync Impact Report
==================
Version change: (none) → 1.0.0
Bump rationale: Initial ratification of the project constitution. No prior version existed;
the document moves from an unfilled scaffold to a governing artifact.

Modified principles:
- [PRINCIPLE_1_NAME] → I. Separation of Concerns
- [PRINCIPLE_2_NAME] → II. Simplicity (KISS + YAGNI)
- [PRINCIPLE_3_NAME] → III. DRY With Evidence
- [PRINCIPLE_4_NAME] → IV. SOLID Adapted for Django
- [PRINCIPLE_5_NAME] → V. Multi-Tenancy by project_uuid

Added sections:
- VI. Authorization at the Edge (principle)
- VII. External I/O Through Clients (principle)
- VIII. Test-First Quality Gate (NON-NEGOTIABLE) (principle)
- Technology Constraints (replaces [SECTION_2_NAME])
- Quality Gates (replaces [SECTION_3_NAME])
- Error Handling and Observability (new section)

Removed sections: none.

Follow-up TODOs: none. All placeholders resolved.

Note: this report is scratch material for reviewing the amendment and is expected to be
removed before the amended file is committed.
-->

# Weni Integrations Engine Constitution

## Core Principles

### I. Separation of Concerns

Each layer has one exclusive set of responsibilities and MUST NOT absorb another's.

- Views handle HTTP concerns only: authorization via `permission_classes`, input validation
  via serializers, DTO construction, delegation to a use case, and response formatting.
- Use cases own business logic, ORM access, orchestration, and domain exceptions.
- Services wrap clients, catch infrastructure errors, and shield callers from transport
  failures.
- Clients own all external HTTP communication.
- Models own persistence and model-level validation.

Business logic MUST NOT live in views or serializers. Views MUST NOT call `Model.objects.*`.
Use cases MUST be framework-agnostic and MUST NOT import from `rest_framework` — no `Request`,
no `Response`, no `status`, no permission classes.

Rationale: strict layer boundaries are what make use cases testable without HTTP, clients
swappable without touching business rules, and provider changes containable to one module.

### II. Simplicity (KISS + YAGNI)

The simplest solution that satisfies the current requirement MUST be preferred. An abstraction
MUST NOT be introduced until at least two concrete uses exist. Parameters, layers, hooks, and
configuration flags MUST NOT be added for hypothetical future needs. If a function suffices, a
class MUST NOT be created.

Dead branches, redundant truthiness checks, and indirection that adds no behavior MUST be
removed rather than commented.

Rationale: speculative structure is the most expensive kind of code in this repo — it is
carried by every integration type and every future contributor, and it is rarely the shape the
future actually needs.

### III. DRY With Evidence

Shared logic MUST be extracted into a service, use case, or utility only when duplication is
real and observed. Two occurrences constitute a pattern; one does not. Premature consolidation
of superficially similar code is a violation of this principle, not compliance with it.

Rationale: extracting from a single occurrence couples unrelated call sites to a shape that was
never validated, and the resulting abstraction is harder to unwind than the duplication it
prevented.

### IV. SOLID Adapted for Django

- Single Responsibility: one class changes for one reason. A use case class handles one
  workflow; a client wraps one external service.
- Open/Closed: new integration behavior MUST be added by registering an AppType class under
  `marketplace/core/types/<category>/<name>/` and adding its dotted path to `APPTYPES_CLASSES`,
  or by composing mixins — not by modifying base contracts.
- Liskov Substitution: AppType implementations MUST honor the base `AppType` contract;
  interface implementations MUST be interchangeable.
- Interface Segregation: contracts MUST be expressed as narrow `typing.Protocol` classes under
  `marketplace/interfaces/`.
- Dependency Inversion: use cases MUST receive services and clients through constructor
  injection typed against protocols, never by importing concrete clients internally. Views are
  the composition root: they instantiate dependencies and inject them.

Naming is part of the contract: `*UseCase`, `*Service`, `*Client`, `*DTO` (a `dataclass`),
`*Serializer`, `*Interface`, `*Error`. Celery tasks use `@shared_task(name="explicit_name")`
with JSON-serializable arguments.

Rationale: the AppType registry is the extension point that lets integration types be added or
disabled without touching shared code; constructor injection is what allows every use case to
be tested against fakes instead of live providers.

### V. Multi-Tenancy by project_uuid

`project_uuid` is the tenant boundary. Every query returning tenant-scoped data MUST filter by
`project_uuid`. The `Project-Uuid` header or the request body `project_uuid` field establishes
tenant context. Apps, authorizations, and any project-scoped record MUST NOT be readable or
writable across project boundaries.

Rationale: this engine holds provider credentials and channel configuration for every project on
the platform; a missing tenant filter is a cross-customer data leak, not a bug.

### VI. Authorization at the Edge

Every view MUST declare `permission_classes` explicitly. The global default is `AllowAny`, so
omission silently publishes the endpoint. Permission logic MUST NOT appear in view method bodies
or inside use cases; compose permission classes with `&` and `|` instead of writing conditional
access checks.

The authorization model is fixed: viewers read, contributors write, admins write and destroy.
Service-to-service calls authenticate by JWT and are authorized through the
`can_communicate_internally` permission rather than project authorization.

Rationale: authorization expressed declaratively at the edge is auditable in one place; the same
rule scattered through method bodies is not reviewable and is the failure mode that produces
open endpoints.

### VII. External I/O Through Clients

All HTTP communication with Flows, Facebook/Meta Graph, VTEX, Router, Commerce, Insights,
Rapidpro, and Connect MUST go through a client under `marketplace/clients/<provider>/`
extending `RequestClient`. Raw `requests` usage in views, serializers, or use cases is
prohibited.

Rationale: the client layer is where request logging, error wrapping, and authentication live —
bypassing it produces calls that are invisible in incident investigation and untestable without
network access.

### VIII. Test-First Quality Gate (NON-NEGOTIABLE)

New or changed behavior MUST ship with tests in the same pull request, covering the happy path,
error paths, and edge cases. Tests MUST mock external services at the client boundary: no test
may reach real Redis, RabbitMQ, S3, OIDC, or provider APIs. Framework-level dependencies MUST be
isolated in tests — override `CACHES` to `LocMemCache`, inject fakes for services, and exercise
consumers through their use case rather than through a broker.

Project coverage MUST remain at or above 75%. Code that genuinely cannot be unit-tested here —
a bridge that only runs against a live provider, a defensive `__main__` block — MUST be marked
`# pragma: no cover` with a stated reason. `# pragma: no cover` MUST NOT be used to exclude
business logic from coverage.

Rationale: this engine's failure modes are silent and delayed — a broken template sync or a
mis-scoped query surfaces days later in a customer's channel. Tests are the only gate that runs
before that.

## Technology Constraints

- Language and framework: Python 3.9+, Django 3.2, Django REST Framework. Dependencies are
  managed exclusively through Poetry and `pyproject.toml`.
- Persistence: PostgreSQL 14, configured by `DATABASE_URL`. Cache and Celery broker: Redis.
  Optional event-driven consumers run over RabbitMQ, gated by `USE_EDA`.
- Async work: Celery with JSON serialization only. Task arguments MUST be JSON-serializable;
  model instances and other non-serializable objects MUST NOT be passed to tasks.
- Models: new domain models extend `BaseModel`; AppType-aware models extend
  `AppTypeBaseModel`. Multi-column and conditional constraints MUST be enforced at the database
  level via `UniqueConstraint` or `unique_together`.
- Configuration: every setting is environment-driven through `django-environ` (`env.str`,
  `env.bool`, `env.int`, `env.json`). Feature flags use `env.bool`. Hardcoded URLs are
  prohibited.
- Secrets MUST NOT be committed. Credentials and keys declare `default=""` in settings and are
  supplied by the environment.

## Quality Gates

The following MUST pass before a change is considered complete, and they run in GitHub Actions
on every push and pull request:

- `python manage.py makemigrations` produces no changes — missing migrations block the build.
- `flake8 marketplace/` passes, with a maximum line length of 119 and migrations excluded.
- `black` formatting passes.
- `coverage run manage.py test` passes and `coverage report` stays at or above the 75% floor;
  coverage is uploaded to Codecov and compared against `main`.

Pre-commit hooks enforce merge-conflict detection, end-of-file newlines, Black, Flake8, and the
test suite locally. Contributors SHOULD run the full check (`contrib/code_check.py`) before
opening a pull request rather than relying on CI to discover failures.

## Error Handling and Observability

- At the API boundary, raise DRF exceptions (`ValidationError`, `PermissionDenied`,
  `AuthenticationFailed`). Use cases raise domain or DRF exceptions; they never return HTTP
  responses.
- Client-layer failures MUST be surfaced as `CustomAPIException` with an appropriate status
  code.
- Services catch infrastructure exceptions, log them with context, and degrade rather than
  propagating transport errors upward.
- Background work — Celery tasks and EDA consumers — MUST report failures to Sentry via
  `sentry_sdk.capture_exception` and MUST use `try/finally` for lock cleanup.
- Exceptions MUST NOT be swallowed silently. Every caught exception is either logged with
  context or re-raised.
- Logging uses `logging.getLogger(__name__)` with f-string messages that include identifying
  context (project UUID, app UUID, external identifiers). `print()` is prohibited.

## Governance

This constitution supersedes informal practice, undocumented convention, and precedent found in
existing code. Where existing code conflicts with these principles, the constitution governs new
and modified code; legacy code is brought into compliance when it is touched, not rewritten
wholesale.

Amendments require:

1. A semantic version bump — MAJOR for removing or redefining a principle in a backward
   incompatible way, MINOR for adding a principle or materially expanding guidance, PATCH for
   clarifications and wording.
2. An updated `Last Amended` date in ISO `YYYY-MM-DD` format.
3. A short rationale for the change, recorded in the Sync Impact Report at the top of this file
   for the reviewer of the amendment.

Every pull request MUST be reviewed against these principles. A reviewer who finds a violation
MUST either request the change or require an explicit, written justification for the exception
in the pull request description. Added complexity carries the burden of proof: the author
justifies it, the reviewer does not justify rejecting it.

**Version**: 1.0.0 | **Ratified**: 2026-09-17 | **Last Amended**: 2026-09-17
