<!--
Sync Impact Report
==================
Version change: 1.0.0 → 1.1.0
Bump rationale: MINOR. The VTEX CX engineering (root) and backend base constitutions were
synthesized into the existing project constitution. Eleven principles and one section were
added and one principle was materially expanded. No principle was removed or redefined in a
backward-incompatible way.

Modified principles:
- VIII. Test-First Quality Gate (NON-NEGOTIABLE): expanded with the backend "Tests Exercise
  Flows" rule (every flow needs an end-to-end flow test covering success and failure paths).
- I–VII: unchanged.

Added principles:
- IX. Never Trust the Client (backend)
- X. Fail Gracefully and Predictably (backend)
- XI. Bounded Retry Over REST (backend)
- XII. Stateless Services and Declared Peak Load (backend "Scalability and Peak Load")
- XIII. Security and Secrets (root)
- XIV. Observability and Diagnosable Errors (root "Observability" + backend "Diagnosable Errors")
- XV. Versioned Contracts (root)
- XVI. Specification Traceability (root)
- XVII. No Silent Divergence (root)
- XVIII. Explicit Over Clever (backend)
- XIX. Contained Changes (backend)

Added sections:
- Development Workflow (root "Version Control and Review", "Commit Messages",
  "Changelog Maintenance")

Modified sections:
- Technology Constraints: secrets bullet now defers to principle XIII.
- Quality Gates: branch protection requirement added.
- Error Handling and Observability: Sentry context and log-redaction rules added.
- Governance: precedence order, provenance, and Constitution Check enforcement added.

Removed sections: none.

Templates requiring updates:
- ⚠ .specify/templates/spec-template.md: does not open with the mandatory
  "Inheritance from Product Spec" section (XVI) nor prompt for declared peak load (XII).
- ⚠ .specify/templates/plan-template.md: Constitution Check gates should list IX–XIX.
- ✅ .specify/templates/tasks-template.md: no conflict found.

Follow-up TODOs:
- TODO(PRODUCT_SPEC_REPO): the product-spec repository that engineering specs inherit from
  (XVI) is not identified anywhere in this repo.
- TODO(ACCOUNT_IDENTIFIER): XIV requires an account identifier on error reports; this engine
  has no account/organization concept beyond project_uuid. Define which opaque identifier
  fills this slot, or record an explicit exception.
- TODO(CORRELATION_ID): no request/correlation identifier exists today (no middleware, no
  propagation to Celery or EDA). Required by XIV.
- TODO(SENTRY_CONTEXT): sentry_sdk.init in marketplace/settings.py sets no tags or scope;
  project, account, user, and correlation identifiers are not attached (XIV).
- TODO(LOG_REDACTION): RequestClient._generate_log and _log_request_exception log full request
  headers (including Authorization bearer tokens) and bodies (XIII, XIV).
- TODO(RETRY_DECORATOR): marketplace/clients/decorators.py retry_on_exception re-raises on 500,
  retries non-transient 4xx, uses print(), and returns None when attempts are exhausted
  (XI, Error Handling). Bring into compliance when next touched.
- TODO(DEPENDENCY_SCAN): no dependency vulnerability scanning in CI or pre-commit (XIII).
- TODO(SPEC_001_INHERITANCE): specs/001-named-template-parameters/spec.md lacks the
  inheritance section (XVI); bring into compliance when the spec is next amended.
- TODO(COMMIT_SCOPE): recent history uses scoped commits (e.g. "fix(waba_sync): ..."); the
  root rule fixes the format as "<type>: <description>". Decide whether to amend the root base
  or drop scopes here.
- TODO(PACKAGE_VERSION): pyproject.toml declares version 2.0.0 while releases are tagged
  v4.x (XV, Development Workflow).

Provenance:
- Source: weni-ai/vtex-cx-engineering-constitutions (main)
- Bases: base-constitution.md, backend/base-constitution.md
- Domains: backend
- Project layer: preserved from constitution 1.0.0 (ratified 2026-09-17)
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
removed rather than commented, within the scope defined by principle XIX.

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

Every flow — an API endpoint, a Celery task, an EDA consumer, a webhook handler — MUST have at
least one test covering the complete use case from input to resulting effect: the request,
message, or task arguments go in, and the test asserts the persisted state and the outbound
client calls that result. Tests asserting a single method in isolation are allowed and SHOULD be
used for edge cases and input variations that are expensive to reach through the whole flow, but
they MUST NOT be the only coverage a flow has. Every flow MUST cover its success path and its
failure paths; an error path that no test exercises MUST NOT be considered covered.

Project coverage MUST remain at or above 75%. Code that genuinely cannot be unit-tested here —
a bridge that only runs against a live provider, a defensive `__main__` block — MUST be marked
`# pragma: no cover` with a stated reason. `# pragma: no cover` MUST NOT be used to exclude
business logic from coverage.

Rationale: this engine's failure modes are silent and delayed — a broken template sync or a
mis-scoped query surfaces days later in a customer's channel. Tests are the only gate that runs
before that. A suite of isolated method tests can stay green while their composition is broken,
because the bug lives in how the pieces interact; the flow test is what proves they work
together, and failure paths are where that matters most.

### IX. Never Trust the Client

Everything that reaches this engine from outside — HTTP requests from the Weni frontend,
service-to-service calls, Meta and VTEX webhooks, EDA messages from RabbitMQ, and Celery task
arguments produced by other services — MUST be treated as potentially malicious, incomplete, or
incorrect until validated. Every external input MUST be validated for type, format, range, and
business rules at the boundary before it reaches a use case: DRF serializers for HTTP and
webhook views, and an explicit validation step in the consumer or task entry point for EDA
messages and task arguments. Authorization MUST be enforced on the server for every request as
defined in principle VI, regardless of any check the caller already performed; a valid internal
JWT authenticates the caller but does not exempt the payload from validation.

Rationale: callers run outside this engine's control and can be inspected, modified, or
bypassed. Validating at the boundary is what prevents injection, cross-tenant writes, and
corrupted channel configuration that caller-side checks alone can never stop.

### X. Fail Gracefully and Predictably

Every external dependency — Meta Graph, VTEX, Flows, Router, Commerce, Insights, Connect, OIDC,
PostgreSQL, Redis, RabbitMQ, S3 — will eventually fail. Every call to an external dependency
MUST have an explicit timeout and MUST NOT block indefinitely: HTTP calls go through
`RequestClient.make_request`, which applies a timeout, and `timeout=None` MUST NOT be passed.
Redis locks MUST be acquired with an expiry. Failures MUST be handled explicitly and surfaced as
consistent, well-defined errors — `CustomAPIException` at the client layer and DRF exceptions at
the API boundary — never as unhandled crashes. Error responses MUST NOT expose stack traces,
credentials, or internal hostnames to callers.

Rationale: failure is a certainty, not an edge case. A Meta outage MUST degrade the features
that depend on Meta, not exhaust gunicorn workers or Celery concurrency waiting on a socket and
take down every other integration with it.

### XI. Bounded Retry Over REST

When data is propagated between services over REST — syncing templates, catalogs, or channel
state with Meta, or pushing data to Flows, Commerce, Router, or Insights — a failed call MUST be
retried rather than dropped. A retry MUST be attempted only for failures that could plausibly
succeed on another attempt: a connection error, a request timeout, an HTTP 5xx, or an HTTP 429.
It MUST NOT be attempted on a 4xx that reflects a defect in the request itself. A retry MUST
only be applied to an operation that is idempotent or protected by a deduplication key; when the
operation is neither, it MUST be made idempotent rather than left without retry.

Every retry policy MUST define a maximum number of attempts and a backoff strategy as named
constants or environment-driven settings; unbounded retry MUST NOT be used. Celery task retries
(`self.retry` or `autoretry_for` with `max_retries` and backoff) are the preferred mechanism for
background propagation. When attempts are exhausted, the failure MUST be logged with context,
reported to Sentry, and MUST remain recoverable — by a scheduled re-sync job that reconciles the
state, or by a persisted record that can be replayed. It MUST NOT be silently discarded.

Rationale: propagation fails for transient reasons far more often than permanent ones, so retry
is what keeps this engine and its providers converging. Retrying a request the provider rejected
on its merits only adds load and burns Meta rate limits; retrying a non-idempotent operation
duplicates its effect. Bounds keep retry from becoming the outage, and a recoverable exhausted
case prevents data from vanishing between two services that each believe they succeeded.

### XII. Stateless Services and Declared Peak Load

Web workers, Celery workers, and EDA consumers MUST be stateless so they can scale
horizontally. State that outlives a single request, task, or message MUST NOT be kept in process
memory, module-level mutable objects, or local disk; it MUST live in PostgreSQL or Redis, shared
by all instances. Locks, debouncing, and scheduling coordination MUST use Redis rather than
in-process primitives. The peak load a feature is expected to sustain — requests per second,
webhook bursts, messages per minute, or catalog size — MUST be declared in its engineering spec,
stated as peak and not as average.

Rationale: capacity is a design input, not something discovered during an incident. Template
webhooks and catalog syncs arrive in bursts tied to customer campaigns and seasonal sales, so
sizing for average traffic fails exactly when demand matters most. Statelessness is what makes
adding replicas a valid answer to load at all.

### XIII. Security and Secrets

Secrets MUST never be committed to the repository. Secrets MUST be provided by an external
secrets manager and injected at runtime as environment variables, read through
`django-environ` with `default=""` in settings. Access MUST follow least privilege by default:
provider tokens, OIDC client credentials, and system-user tokens are scoped to what the
integration needs. Dependencies MUST come only from trusted sources, managed through Poetry and
locked in `poetry.lock`, and MUST be checked for known vulnerabilities.

Rationale: this engine stores Meta system-user tokens and VTEX credentials for every project on
the platform. Leaked credentials and untrusted dependencies are among the most common and most
damaging breaches; prevention is far cheaper than remediation.

### XIV. Observability and Diagnosable Errors

Logs MUST be structured — `logging.getLogger(__name__)` with identifying context in the message
and machine-readable detail in `extra` — and MUST never contain secrets or sensitive personal
data. Request headers MUST be redacted of `Authorization`, tokens, and cookies before logging.
Errors MUST be traceable across the API, Celery tasks, and EDA consumers through a correlation
identifier that is propagated into background work.

Every error reported to Sentry MUST carry enough context to be located and filtered without
reproducing it: at minimum the project identifier (`project_uuid`), the account identifier, the
user identifier, and the correlation identifier. These identifiers MUST be opaque. Because
`User.USERNAME_FIELD` is `email`, the user identifier MUST be the user's primary key, never the
email. Sensitive personal data — names, e-mail addresses, phone numbers (including WhatsApp
display and business phone numbers), or government identifiers — MUST NOT be attached to an
error report or a log line under any circumstance, and `send_default_pii` MUST remain disabled.

Rationale: an error without identifying context can be counted but not investigated; opaque
identifiers give exactly the filtering an investigation needs while keeping telemetry free of
personal data. Structured, privacy-safe telemetry is what makes incidents diagnosable without
creating a new data-exposure risk.

### XV. Versioned Contracts

Every public interface of this engine MUST be versioned following SemVer: the REST API under
`/api/v1/`, internal endpoints consumed by other Weni services, Celery task names and argument
shapes consumed by other producers, and EDA message schemas. Changes MUST be backward compatible
or ship with an announced deprecation path; a breaking change to the REST API MUST ship under a
new path version rather than altering `/api/v1/` in place. Silent breaking changes MUST NOT be
introduced. Releases are tagged `vMAJOR.MINOR.PATCH` and the bump MUST reflect the most severe
contract change in the release.

Rationale: the Weni frontend, Flows, Connect, and other services depend on these contracts and
deploy on their own schedules; explicit versioning and deprecation give them a predictable path
to adapt without outages.

### XVI. Specification Traceability

Every engineering spec under `specs/<NNN-feature>/` MUST derive from exactly one approved product
spec and MUST reference it through an immutable, pinned version (commit or tag) — a mutable URL
or ID alone MUST NOT be used. The product spec MUST exist and be tagged before its engineering
spec is created. An engineering spec MUST NOT redefine the "what" it inherits: problem, scope,
success criteria, and binding decisions belong to the product spec. A technical architecture
document SHOULD be produced for non-trivial features; when it exists it MUST be linked from the
engineering spec, also pinned by commit/tag, but its absence MUST NOT block the engineering
spec.

Every engineering spec MUST open with an inheritance section in exactly this format:

```
## Inheritance from Product Spec
- Product Spec: <title> — <URL>
- Pinned version: <commit/tag>
- Architecture doc: <none | URL + commit/tag>
- Inherited binding decisions: <short list>
- Scope of this spec: <slice implemented by this repo>
- Divergences: <none | link to amendment>
```

Rationale: traceability from product intent to technical execution keeps decisions auditable.
Pinning the version guarantees that every repository implements the same version of the feature
instead of divergent readings of a spec that changed mid-flight. A single inheritance format
keeps the link machine-checkable across every repository.

### XVII. No Silent Divergence

When a technical need contradicts something inherited from the product spec — scope, success
criteria, or a binding decision — the divergence MUST NOT be implemented silently in code. It
MUST be raised as an amendment in the product repository and recorded in the `Divergences` field
of the engineering spec's inheritance section, linking to that amendment. Once the amendment is
approved and produces a new tag, the engineering spec's `Pinned version` MUST be updated to it.
A technical difference that contradicts nothing inherited is not a divergence but an
implementation decision, and MUST live in the engineering spec (`spec.md`, `plan.md`, or
`research.md`).

Rationale: in a federated model where the product spec is the single source of truth, a silent
code deviation makes intent and implementation drift apart with no audit trail.

### XVIII. Explicit Over Clever

What a piece of code does MUST be evident where it happens. Hidden side effects and implicit
control flow MUST NOT be introduced to save lines: external I/O, Celery dispatch, and cross-app
writes MUST be invoked explicitly from the use case that owns them, not triggered from Django
signals, `save()` overrides, or property getters. Any literal that carries meaning — a
threshold, a limit, a timeout, a retry count, a sync interval — MUST be a module-level
`UPPER_CASE` constant or an environment-driven setting rather than an inline value. A literal
that carries no meaning beyond its own value, such as an index of 0 or an increment of 1, is
exempt. Comments MUST explain why a decision was made: the constraint, the trade-off, or the
non-obvious reason. A comment that restates what the code already says is a signal that the
code SHOULD be rewritten to say it.

Rationale: code is read far more often than it is written, usually by someone without the
context that made the clever version feel obvious. An unexplained literal is a decision nobody
can review, and a side effect hidden in a signal is a provider call nobody sees in the use case
they are changing.

### XIX. Contained Changes

A change MUST be limited to the context it was asked to address. Refactoring, renaming,
reformatting, or behavior adjustments outside that context MUST NOT ride along; each belongs to
its own change. Bringing legacy code into compliance with this constitution (see Governance) and
removing dead code (principle II) apply to the code the change already touches, not to unrelated
neighbors. This principle governs the scope of a change as a whole; the atomic-commit rule in
Development Workflow governs how that change is divided internally, and a change that stays
within scope MAY span several commits.

Rationale: a change that reaches beyond its stated scope is a change nobody reviewed on purpose.
It hides the intended fix inside unrelated edits, makes the diff expensive to read, and turns a
revert into a choice between losing the fix and keeping an unrelated regression.

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
- Secrets follow principle XIII.

## Development Workflow

### Version Control and Review

All code MUST enter `main` through a pull request. A merge MUST require at least one approved
review and a green CI run. Direct pushes to `main` MUST be blocked via GitHub branch protection.

Rationale: the policy is only real when enforced by the platform, not by trust. Peer review and
a protected main branch keep history auditable and prevent unreviewed changes from reaching
production.

### Commit Messages

Commits MUST follow Conventional Commits format: `<type>: <description>`. Allowed types: `feat`,
`fix`, `docs`, `refactor`, `test`, `chore`. The description MUST be imperative, specific, and no
longer than 50 characters. Commits MUST be atomic: one logical change per commit.

Rationale: conventional commits enable automated changelog generation and semantic versioning;
this repo's `CHANGELOG.md` is assembled from commit subjects. Atomic commits simplify bisecting,
reverting, and reviewing.

### Changelog Maintenance

Public libraries MUST maintain a changelog following Keep a Changelog format, with every
user-facing change under the appropriate category (Added, Changed, Deprecated, Removed, Fixed,
Security). This repository is a deployed service, not a public library: its `CHANGELOG.md`
records each release under its `vMAJOR.MINOR.PATCH` tag, and every user-facing change MUST appear
there. If a reusable package is ever published from this repository, that package MUST follow
Keep a Changelog. Version bumps MUST follow SemVer in both cases.

Rationale: a maintained changelog communicates impact to consumers and serves as release
documentation; SemVer alignment ensures predictable upgrade expectations.

## Quality Gates

The following MUST pass before a change is considered complete, and they run in GitHub Actions
on every push and pull request:

- `python manage.py makemigrations` produces no changes — missing migrations block the build.
- `flake8 marketplace/` passes, with a maximum line length of 119 and migrations excluded.
- `black` formatting passes.
- `coverage run manage.py test` passes and `coverage report` stays at or above the 75% floor;
  coverage is uploaded to Codecov and compared against `main`.

A pull request MUST NOT be merged into `main` unless these checks are green and the
review requirement in Development Workflow is met.

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
  `sentry_sdk.capture_exception` with the context required by principle XIV, and MUST use
  `try/finally` for lock cleanup.
- Exceptions MUST NOT be swallowed silently. Every caught exception is either logged with
  context or re-raised.
- Logging uses `logging.getLogger(__name__)` with f-string messages that include identifying
  context (project UUID, app UUID, external identifiers). `print()` is prohibited.
- Request and response logging in the client layer MUST redact credentials and personal data
  before emitting, per principles XIII and XIV.

## Governance

This constitution supersedes informal practice, undocumented convention, and precedent found in
existing code. Where existing code conflicts with these principles, the constitution governs new
and modified code; legacy code is brought into compliance when it is touched, within the scope
defined by principle XIX, not rewritten wholesale.

This document synthesizes the VTEX CX engineering base constitution, the backend domain
constitution, and this project's own rules, with precedence in that order: a root engineering
rule prevails over a backend rule, and a backend rule prevails over a project rule. A project
rule MAY specialize a base rule but MUST NOT weaken it without an explicit, justified exception
recorded in the principle itself.

Amendments require:

1. A semantic version bump — MAJOR for removing or redefining a principle in a backward
   incompatible way, MINOR for adding a principle or materially expanding guidance, PATCH for
   clarifications and wording.
2. An updated `Last Amended` date in ISO `YYYY-MM-DD` format.
3. A short rationale for the change, recorded in the Sync Impact Report at the top of this file,
   together with the provenance of any base constitution that was resynchronized.

Every implementation plan MUST pass a Constitution Check against these principles before design
and again after it; `/speckit.analyze` treats a conflict with any MUST in this document as
CRITICAL. Every pull request MUST be reviewed against these principles. A reviewer who finds a
violation MUST either request the change or require an explicit, written justification for the
exception in the pull request description. Added complexity carries the burden of proof: the
author justifies it, the reviewer does not justify rejecting it.

**Version**: 1.1.0 | **Ratified**: 2026-09-17 | **Last Amended**: 2026-10-01
