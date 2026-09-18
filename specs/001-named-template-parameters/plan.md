# Implementation Plan: Named WhatsApp Template Parameters — Integrations Engine

**Branch**: `001-named-template-parameters` | **Date**: 2026-09-17 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification from `specs/001-named-template-parameters/spec.md`

---

## Summary

Meta templates can declare `parameter_format: "named"` and carry `{{nome}}`-style placeholders with
`example.body_text_named_params`. This service treats every template as positional, so a named template
syncs in with `variable_count = 0` and no parameter metadata, and every downstream layer then fails.

This plan makes the parameter format and the parameter names **true, complete and durable** in the local
mirror and in what this service pushes to Flows. The technical approach is deliberately narrow:

1. **Three nullable columns on `TemplateTranslation`** (migration `0014`), where `NULL` parameter format
   *is* the "format not yet known" state — no backfill, no table rewrite, existing rows stay readable.
2. **One pure module** (`wpp_templates/parameters.py`) holding the body grammar, Meta's naming rule, and
   the Meta-response → recorded-values mapping. No Django, no DRF, no ORM, no I/O. Both the sync path and
   the reconciliation path call the same function, so they cannot diverge.
3. **A template-scoped Graph API version** pinned at `v25.0`, applied by a `template_api_url` property on
   `TemplatesRequests` methods — **not** a `BASE_URL` override, which `FacebookClient`'s MRO would leak
   onto every mixed-in surface. Catalog, commerce and onboarding calls keep `WHATSAPP_API_URL`.
4. **An operator-triggered management command** for reconciliation that reuses the existing per-WABA TTL
   locks, the existing drain budget as its pace, and the existing Redis progress-map pattern, and emits
   structured logs plus one CSV artifact. No new model, endpoint or permission.
5. **A default-off configuration flag** gating *named authoring only*, so this service can ship before
   Flows, mailroom, goflow and courier without a named template becoming dispatchable into a pipeline
   that would deliver it broken.

`utils.py::extract_template_data`, which rebuilds the Flows payload from the local mirror, still needs the
format and named examples threaded through it — but for a narrower reason than the spec assumed. See
Cross-Repository Alignment below.

---

## Cross-Repository Alignment (Flows)

Verified against [`weni-ai/flows` PR #876](https://github.com/weni-ai/flows/pull/876) — branch
`feat/named-template-variables`, head `6f0b9d9` — plus the surrounding Flows code that PR does not touch
but our payloads reach. Findings that changed this plan are marked.

### Confirmed aligned

| Our contract | Flows implementation | Status |
| --- | --- | --- |
| `parameter_format` at the **template root** of each item | `normalize_parameter_format(template.get("parameter_format"))` in `update_local_templates` | Aligned |
| Uppercase `"NAMED"` on the wire | `value.strip().lower() == "named"` — case-insensitive | Aligned |
| Key omitted ⇒ positional | `normalize_parameter_format(None)` returns `"positional"` | Aligned |
| `example.body_text_named_params` with `param_name` on the **BODY** component | `extract_parameter_names_from_components` reads exactly that, filtering `type.upper() == "BODY"` | Aligned |
| Bulk `PATCH /template/{uuid}/` forwards Meta verbatim (FR-013) | `partial_update` → `update_local_templates(channel, request.data.get("data"))` | Aligned — no contract change needed, as assumed |
| Header/footer variable skip is **not ours** | `has_placeholders()` → `all_supported = False` → `continue`, in Flows | Aligned — do not implement here |
| Our `variable_count` is consumed only by our own read surfaces | Flows computes its own: `len(parameter_names)` when named | Aligned |
| No positional index anywhere (FR-005, SC-006) | Read shape is `parameters=[{"name": name}]`; resolution is keyed by name | Aligned |
| Parameter policy is out of our scope | `Template.parameter_policies` JSONField, resolved in `named_template_broadcast.py` | Aligned |

**The FR-017 gate is closed.** `TemplateSyncSerializer.template_data` is a plain `serializers.DictField`,
so nothing strips our new root key, and both Flows endpoints funnel into the same `update_local_templates`
parser. No further cross-repo confirmation is outstanding.

### Findings that changed this plan

**1. A routine status webhook does not clear anything in Flows.** `_handle_template_sync` calls
`update_local_templates` **only when the template does not already exist** in the org. For an existing
template it calls `update_template_sync`, which routes to `update_template_status` /
`update_template_category` — both touching only `status` and `category`, never re-reading `template_data`.

The spec's framing of this as the highest-risk regression (BD-015) does not hold against the current Flows
implementation. FR-017 is still required, for a narrower reason: when Flows has **not** yet seen the
template — the first webhook after approval, before the next daily bulk sync — `update_local_templates`
*is* called with our rebuilt payload, and without `parameter_format` the template lands positional in Flows
and stays broken until the next bulk sync corrects it. Same code change, materially lower severity.

**2. Our parameter-name rule must require a leading non-digit.** Flows validates names with
`^[A-Za-z_][A-Za-z0-9_]*$` and **silently skips** any name that fails it. A name like `{{2fa_code}}` would
pass a `^[a-z0-9_]+$` rule, plausibly pass Meta, and then be dropped from Flows' `parameter_names` —
yielding a short list and a parameter that never resolves at send time. Our regex is therefore
`^[a-z_][a-z0-9_]*$`, still looser than Meta's literal documented rule and so compliant with FR-024.

**3. Restoring positional `body_example` on the webhook payload is dropped.** Flows'
`TemplateTranslation` has **no** example field, and `update_local_templates` never reads
`example.body_text`. The change was justified on the premise that Flows was losing those values; it never
consumed them. It is removed from this feature and recorded as separate debt.

### Divergences owned by Flows — reported, not fixable here

| Divergence | Detail | Our position |
| --- | --- | --- |
| Name **ordering** source | `extract_parameter_names_from_components` reads `body_text_named_params` first, then appends body names. Meta documents example order as arbitrary, so Flows' order is example order despite their model comment saying "body order" | Cosmetic. Resolution is name-keyed. We keep body order, which FR-004 requires and which is the genuinely correct one |
| FR-011 mismatch handling | Flows produces the **union** of example names and body names. Body `{{nome}} {{cota}}` with examples `nome`/`quota` yields `["nome", "quota", "cota"]` — a phantom `quota` that renders nowhere yet still passes `assert_named_template_ready` | On the webhook path our anomaly handling (omitting the example block) makes Flows fall back to body names and agree with us. On the bulk path FR-013 forbids us reshaping Meta's payload, so this cannot be fixed here |
| Format granularity | Flows stores `parameter_format` on **Template** and `parameter_names` on **TemplateTranslation**, so `get_or_create` lets the last-synced translation overwrite the template-level format. Nothing guards format disagreement, though `declared_parameter_names` does guard name disagreement | Our per-translation model with a derived `"MIXED"` is strictly more correct and matches Meta's granularity. No change here |
| Third format state | Flows' `Template.parameter_format` defaults to `"positional"` with no not-yet-known state, so our omitted key flattens to positional downstream | Acceptable. A library template's format is resolved by our post-creation sync and reaches Flows on the next bulk sync, so both converge |
| On-premises channels | `NAMED_TEMPLATE_CHANNEL_TYPES = {"WAC", "WCD"}` excludes on-premises WhatsApp, which is the `config.waba.id` app population | Reduces the named-specific value of the webhook lookup fix — see Complexity Tracking #3 |

---

## Technical Context

**Language/Version**: Python 3.9+ (no type checker enforced; partial type hints)

**Primary Dependencies**: Django 3.2, Django REST Framework, Celery 5, `django-redis`, `django-environ`,
`psycopg2`

**Storage**: PostgreSQL 14 (`TemplateMessage` / `TemplateTranslation` mirror); Redis for pacing locks and
reconciliation progress

**Testing**: Django `TestCase` / `SimpleTestCase`, `unittest.mock`, `APIBaseTestCase` + `Request` helper
from `marketplace/core/tests/base.py`, `coverage` with `fail_under = 75`

**Target Platform**: Linux server (Docker / Kubernetes), Gunicorn + Celery worker + Celery beat

**Project Type**: Django REST web service (single project, layered: views → use cases → services → clients)

**Performance Goals**: No additional Meta request per template (NFR-001); no measurable sync latency
regression for positional accounts (NFR-003); reconciliation paced at the existing
`META_SYNC_TEMPLATES_DRAIN_BUDGET` (default 30 WABAs/minute)

**Constraints**: Migration must not take a long exclusive lock and existing rows must remain valid and
readable before reconciliation runs (NFR-005); no positional index computed, stored, published or
transmitted for a named parameter (FR-005, SC-006); no test may reach real Redis or provider APIs
(Constitution VIII)

**Scale/Scope**: One `wpp_templates` Django app plus three shared files (`clients/facebook/client.py`,
`services/facebook/service.py`, `interfaces/facebook/interfaces.py`) and `settings.py`. Fleet scale is
every `wpp` / `wpp-cloud` app; reconciliation iterates unique WABAs, not apps.

**Unknowns**: None. Every `NEEDS CLARIFICATION` was resolved in Phase 0 — see [`research.md`](./research.md).

---

## Constitution Check

*GATE: evaluated before Phase 0 and re-evaluated after Phase 1 design. Both passes recorded.*

| Principle | Assessment | Verdict |
| --- | --- | --- |
| **I. Separation of Concerns** | Body grammar and Meta's naming rule live in a pure module. Authoring validation lives in the serializer (the constitution assigns input validation to serializers). Recording and reconciliation orchestration live in use cases. Every Meta and Flows call goes through an existing client. | **PASS with two recorded exceptions under Complexity Tracking #1** — `TemplateTranslationSerializer.create()` and `views.py::partial_update` already perform ORM writes and Meta calls today. This plan adds arguments / a `parameters.py` call on those paths rather than extracting use cases. |
| **II. Simplicity (KISS + YAGNI)** | Three columns, one pure module, one use case, one command, one flag. `NULL` carries the third format state instead of a separate boolean. The `MIXED` template-level value is derived on read and never stored. | **PASS** — the one configuration flag is mandated by FR-027 and gates a cross-repository rollout, not a hypothetical need. |
| **III. DRY With Evidence** | `build_translation_parameters()` has exactly two real call sites (sync, reconciliation), so extraction is evidence-based. The webhook app lookup is deliberately **not** extracted into a shared helper with `_apps_for_waba`, because the two call sites apply genuinely different filters. | **PASS** |
| **IV. SOLID for Django** | The reconciliation use case receives its Redis connection, template service and sync-use-case factory through constructor injection. Naming follows `*UseCase` / `*Service` / `*Client` / `*Interface`. `TemplatesRequestsInterface` is updated so client and interface stay substitutable. No new Protocol is introduced for Flows — none exists today and one use case does not justify inventing one. | **PASS** |
| **V. Multi-Tenancy by `project_uuid`** | Read surfaces are unchanged in scoping: `get_queryset()` filters by `app_uuid` behind `ProjectManagePermission`. Parameter names and examples are written per app from that app's own WABA response and never resolved across app boundaries (FR-042). | **PASS with a noted boundary** — reconciliation is an operator fleet operation that spans projects by design. It has no HTTP surface, and its artifact is written to the operator's filesystem, never served. |
| **VI. Authorization at the Edge** | No new endpoint, no new permission class, no change to `permission_classes`. Reconciliation is a management command precisely so it needs neither (FR-030). | **PASS** |
| **VII. External I/O Through Clients** | All Meta calls stay in `TemplatesRequests`; all Flows calls stay in `FlowsClient`. The new pure module performs no I/O at all. | **PASS** |
| **VIII. Test-First Quality Gate** | The bulk of new logic is pure functions, which are exhaustively testable. Meta and Flows are mocked at the client boundary. Redis is injected as a fake. `marketplace/clients/*` and `marketplace/interfaces/*` are already omitted by `.coveragerc`, so the signature changes carry no coverage cost. | **PASS** |

**Post-Phase-1 re-evaluation**: the design in [`data-model.md`](./data-model.md) and [`contracts/`](./contracts)
introduces no layer violation beyond the two already recorded under Complexity Tracking #1. Verdict unchanged.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-named-template-parameters/
├── plan.md              # This file
├── research.md          # Phase 0 output — the ten planning decisions with rationale
├── data-model.md        # Phase 1 output — schema, states, transitions, migration safety
├── quickstart.md        # Phase 1 output — runnable validation scenarios
├── contracts/           # Phase 1 output
│   ├── meta-graph-templates.md    # Outbound contract to Meta (create payload, list response)
│   ├── flows-push.md              # Outbound contract to Flows (bulk PATCH, webhook POST)
│   ├── read-surfaces.md           # Inbound REST contract (template list, template detail)
│   ├── internal-python-api.md     # Client/service/interface signatures, pure module API
│   └── reconciliation-cli.md      # Command arguments, exit codes, report artifact schema
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
marketplace/
├── settings.py                                  # MODIFIED — WHATSAPP_TEMPLATE_VERSION,
│                                                #   WHATSAPP_TEMPLATE_API_URL,
│                                                #   WHATSAPP_NAMED_TEMPLATES_ENABLED
│
├── clients/facebook/client.py                   # MODIFIED — TemplatesRequests.template_api_url
│                                                #   (not BASE_URL — FacebookClient MRO);
│                                                #   create_template_message(+parameter_format)
├── services/facebook/service.py                 # MODIFIED — TemplateService.create_template_message
│                                                #   (+parameter_format)
├── interfaces/facebook/interfaces.py            # MODIFIED — TemplatesRequestsInterface signature
│
└── wpp_templates/
    ├── parameters.py                            # NEW — pure module: body grammar, Meta naming rule,
    │                                             #   format normalisation, Meta-response mapping
    ├── models.py                                # MODIFIED — parameter_format, body_named_params,
    │                                             #   parameter_anomaly on TemplateTranslation
    ├── migrations/0014_templatetranslation_parameters.py   # NEW
    ├── template_helpers.py                      # MODIFIED — extract_body_example made format-aware
    ├── serializers.py                           # MODIFIED — named authoring validation + submission;
    │                                             #   read shape (format, names, anomaly flag)
    ├── utils.py                                 # MODIFIED — extract_template_data carries format and
    │                                             #   examples; webhook app lookup widened
    ├── usecases/
    │   ├── template_sync.py                     # MODIFIED — records format, names, examples, count
    │   ├── template_library_creation.py         # MODIFIED — leaves format not yet known
    │   └── template_parameter_reconciliation.py # NEW — TemplateParameterReconciliationUseCase
    ├── management/
    │   └── commands/
    │       └── reconcile_template_parameters.py # NEW — operator-triggered entry point
    ├── tests/
    │   ├── test_parameters.py                   # NEW — pure module, table-driven
    │   ├── test_utils.py                        # EXTENDED — webhook rebuild + widened lookup
    │   ├── test_serializers.py                  # EXTENDED — named authoring accept/reject matrix
    │   ├── test_views.py                        # EXTENDED — read surfaces, no-index assertion
    │   └── test_template_api_version.py         # NEW — version scoping, endpoint by endpoint
    └── usecases/tests/
        ├── test_template_sync.py                # EXTENDED — recording matrix
        └── test_template_parameter_reconciliation.py  # NEW — classification, resume, idempotency
```

**Structure Decision**: this is a single Django project and the feature is almost entirely contained in the
existing `marketplace/wpp_templates/` app. Three shared files outside it change only because the
`create_template_message` signature must be threaded through the client, service and interface layers, and
`settings.py` changes to add the template-scoped version and the authoring flag. No new Django app, no new
package outside `wpp_templates`, and the only genuinely new directory is
`wpp_templates/management/commands/` — which the repository does not yet have for this app, following the
one existing precedent at `marketplace/event_driven/management/commands/edaconsume.py`.

---

## Key Design Decisions

Full rationale and rejected alternatives are in [`research.md`](./research.md). Summarised here because
these are the decisions a reviewer needs to agree with before tasks are generated.

### 1. Graph API version: pin `v25.0`, scoped to `TemplatesRequests`

`v23.0` is the floor but expires **2027-10-08** — about 12 months of runway from today, which is not enough
for a version this service will not revisit soon. `v25.0` expires **2028-07-29** (~22 months), is one
release behind the latest (`v26.0`, released 2026-07-29 with expiry still TBD), and its expiry date is
already published — which matters because FR-040's fleet-wide alignment needs a dated deadline to be
scheduled against.

The scoping is a property on `TemplatesRequests`, **not** a `BASE_URL` override:

```python
@property
def template_api_url(self):
    return settings.WHATSAPP_TEMPLATE_API_URL
```

Every template method builds its URL from `self.template_api_url`. Catalog, phone, profile, OAuth and
onboarding methods keep using `self.get_url` → `FacebookAuthorization.BASE_URL` → `WHATSAPP_API_URL`.

A class-level `BASE_URL` on `TemplatesRequests` was rejected after verifying `FacebookClient`'s MRO:
`FacebookClient` mixins `CatalogsRequests` then `TemplatesRequests`, so `FacebookClient.BASE_URL` would
resolve to `v25.0` and every production call constructed as `FacebookClient(token)` — catalogs, VTEX
product batch, commerce, onboarding, photos — would silently move with the template surfaces, which is
exactly the failure FR-039 and SC-009 exist to prevent. A distinct property is invisible to those methods.

A fact worth surfacing: the configured default `v16.0` **expired on 2025-05-14**. Meta serves calls to an
expired version from the next oldest usable version, so today's template calls are already running at a
version nobody chose. This is not only a missing capability — it is an unpinned production dependency.

### 2. Schema: `NULL` is the third state

Three nullable-or-constant-default columns on `TemplateTranslation`:

| Column | Type | Meaning |
| --- | --- | --- |
| `parameter_format` | `CharField(max_length=10, null=True, default=None)` | `"NAMED"`, `"POSITIONAL"`, or `NULL` = format not yet known |
| `body_named_params` | `JSONField(default=list, blank=True)` | Ordered `[{"param_name": ..., "example": ... \| null}]` |
| `parameter_anomaly` | `JSONField(null=True, default=None)` | `NULL` = clean; otherwise the anomaly type plus both observed name sets |

Using `NULL` for "not yet known" is what makes NFR-005 free: `ADD COLUMN` with a nullable or constant
default does not rewrite the table on PostgreSQL 14, the lock is a sub-millisecond catalog update, there is
no backfill, and every pre-existing row is immediately valid and readable as "this service has not been
told the format". That is a true statement about those rows, not a placeholder — which is precisely the
state reconciliation exists to resolve.

`body_named_params` uses **Meta's own key names** (`param_name`, `example`) so that
`extract_template_data` can emit `example.body_text_named_params` with zero transformation and the sync can
ingest it with almost none. Names and examples live in one ordered list rather than two parallel fields so
they cannot drift apart.

### 3. Where parsing and validation live

`marketplace/wpp_templates/parameters.py` is a pure module — no Django, no DRF, no ORM, no I/O. It owns the
body grammar, Meta's naming rule, format normalisation, the FR-011 body-vs-examples reconciliation, and the
Meta-response → recorded-values mapping. The serializer calls it to validate and to build the Meta payload;
`TemplateSyncUseCase` and `TemplateParameterReconciliationUseCase` call the same
`build_translation_parameters()` to record. One grammar, one rule, one mapping, three callers, no drift.

### 4. `create_template_message` signature

```python
def create_template_message(
    self, waba_id, name, category, components, language, parameter_format=None
) -> dict
```

identically across `interfaces/facebook/interfaces.py`, `services/facebook/service.py` and
`clients/facebook/client.py`. The client includes `parameter_format` in the payload **only when it is not
None**, so a positional create is byte-identical to today's request — Meta documents an omitted
`parameter_format` as positional, so sending `"positional"` explicitly would be a gratuitous change to the
live authoring path.

`update_template_message` is **deliberately unchanged**. FR-019 forbids attempting to change a template's
format at Meta, and the way to guarantee that is for the edit path to have no way to express it.

### 5. `extract_body_example` becomes format-aware by exclusion

Today the function flattens every value of Meta's `example` dict, so `body_text_named_params` would push
dict objects into an `ArrayField(CharField)`. The fix skips the named-parameter keys
(`body_text_named_params`, `header_text_named_params`) and leaves every other key's handling byte-identical.
An allowlist of `body_text` was rejected: the authoring path passes an author-supplied `example` dict whose
keys are not guaranteed, and an allowlist would silently change today's positional behaviour, which FR-041
and SC-008 forbid.

### 6. `variable_count`

Named translations: the count of declared names. Positional translations: unchanged, including the literal
`0` written on all three paths (`serializers.py`, `usecases/template_sync.py`,
`usecases/template_library_creation.py`). Not-yet-known translations: `0`, unchanged. Only the named branch
is new.

### 7. Read shape

Per translation: `parameter_format` (`"NAMED"` / `"POSITIONAL"` / `null`), `parameter_names` (ordered
strings, no examples, no index), `has_parameter_anomaly` (boolean), and the existing `variable_count` and
`body_example` untouched. Template level: a derived `parameter_format` that is the agreed value of its
translations, `"MIXED"` when known translations disagree, and `null` when none is known. `"MIXED"` is a
read-only derivation — never stored, never sent to Meta.

The anomaly is published as a boolean rather than the evidence blob. A consumer's readiness rule becomes
`parameter_format == "NAMED" and not has_parameter_anomaly`, which satisfies FR-011 and FR-015 without this
service publishing a dispatch-readiness judgement it does not own — the parameter policy belongs to Flows.

### 8. Authoring flag

`WHATSAPP_NAMED_TEMPLATES_ENABLED = env.bool("WHATSAPP_NAMED_TEMPLATES_ENABLED", default=False)`.

It gates **only** the authoring path. When it is off and a submitted body is named, the request is rejected
with a field-level error — not silently downgraded to positional, which would create a broken template. The
sync, webhook, read and reconciliation paths are **not** gated: recording what Meta has already told us is
additive and safe, and gating it would leave the mirror wrong for templates authored in Meta's own panel.

### 9. The two pre-existing defects — one IN, one OUT

**`extract_template_data` drops `body_example`: leave it.** This was originally recommended IN on the
premise that Flows was losing positional examples on the webhook path. Verification against Flows PR #876
disproved the premise: Flows' `TemplateTranslation` has no example field and `update_local_templates` never
reads `example.body_text`. Restoring it would be a deliberate deviation from FR-041 and SC-008 with **zero
downstream consumer** — complexity with no payoff. Recorded as separate debt instead.

The function is still edited for FR-017, to add `parameter_format` and the named examples. Only the
positional restoration is dropped.

**Widen the webhook app lookup: fix it.** `get_apps_by_waba_id` matches only `config__wa_waba_id`, while
`_apps_for_waba` in `tasks.py` also accepts `config__waba__id`. `wpp` (on-premises) apps store their WABA
at the nested path and *are* synced, so they can hold named templates but never receive a webhook. The fix
is one `Q(...) | Q(...)`. It is not extracted into a shared helper with `_apps_for_waba`, because that
function additionally filters by `code` and `ignores_meta_sync`, and a webhook should not be dropped just
because scheduled sync is disabled.

Its named-specific value is **lower than first assessed**: Flows' `NAMED_TEMPLATE_CHANNEL_TYPES` is
`{"WAC", "WCD"}`, which excludes on-premises WhatsApp, so those apps cannot dispatch named templates
downstream regardless. It remains worth doing because it corrects webhook coverage generally and keeps our
own mirror and read surfaces true for that app population. Recorded in Complexity Tracking #3.

### 10. Reconciliation shape

An operator-triggered `reconcile_template_parameters` management command driving
`TemplateParameterReconciliationUseCase`. It reuses the existing per-WABA TTL lock keys
(`TTL_WHATSAPP_TEMPLATES`), paces itself from the existing `META_SYNC_TEMPLATES_DRAIN_BUDGET`, and applies
Meta's list through the existing `TemplateSyncUseCase.sync_templates(templates=...)` — which is why
convergence, in-place updates and the absence of duplicate rows are structural rather than re-implemented.
Progress lives in Redis at `template_param_reconcile:progress` with a 24h TTL, mirroring the
`template_status:{app_uuid}` pattern, so an interrupted run resumes.

It runs **synchronously** rather than through the paced queue's drain. The drain's beat entry hardcodes
`task_sync_whatsapp_templates_item` as its item task, so routing reconciliation through it would require a
second queue key and a second permanent beat schedule for a one-time capability — and asynchronous
execution would make FR-033's single exportable artifact impossible to produce. Recorded in Complexity
Tracking #4.

---

## Complexity Tracking

> Recorded because each of these is either a constitution deviation or a deliberate departure from the
> letter of a requirement. Each carries an explicit justification per the constitution's governance rule
> that added complexity carries the burden of proof.

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| **1. Extending `TemplateTranslationSerializer.create()` and `views.py::partial_update`**, both of which already perform ORM writes, base64 media upload and Meta calls, instead of extracting use cases (Constitution I) | FR-020/FR-021 require the authoring path to detect the format and submit it; FR-019 requires the edit path to re-derive names from the submitted body. Each change is assembled where the rest of that path already lives. | Extracting `CreateTemplateTranslationUseCase` or an edit-path use case would rewrite the highest-traffic write paths — including media upload and header/button assembly — and directly endangers SC-008's "0% of positional templates change behaviour". Mitigation: **no new business logic enters the serializer or the view**; the grammar, the naming rule and the payload assembly all live in the pure `parameters.py` module, so neither existing violation is deepened. The extractions are recorded as follow-up debt. |
| **2. A second Graph API version setting** (`WHATSAPP_TEMPLATE_VERSION`) diverging from `WHATSAPP_VERSION` (Constitution II — two settings where one existed) | FR-039. `WHATSAPP_VERSION` feeds the base URL of roughly thirty Graph endpoints across catalogs, the VTEX product batch pipeline, commerce settings, phone numbers, profile, OAuth, credit sharing and onboarding. | One global raise couples a defect fix to a compatibility review of the entire VTEX product pipeline, and makes rollback all-or-nothing. The divergence is bounded to `TemplatesRequests` **methods** via `template_api_url` (a `BASE_URL` override is unsafe under `FacebookClient` MRO — see Decision 1), is documented in `research.md` and in a settings comment, and FR-040 tracks the fleet-wide alignment as a separate change with a dated deadline (`v25.0` expires 2028-07-29). |
| **3. Widening the webhook app lookup** to `Q(config__wa_waba_id=...) \| Q(config__waba__id=...)` — beyond what the spec requires (the spec records it as a risk, not a requirement) | Without it, `wpp` on-premises apps are invisible to every webhook event, so FR-017 and FR-018 simply do not apply to them and their mirror drifts from Meta on every status change. | Leaving it rejected because it caps the feature's coverage for a whole app code with no way for an operator to tell, and the cost is one `Q` expression. **Consequences to review**: apps matched only by the nested path begin receiving webhook-driven Flows pushes they have never received — correct behaviour, but new traffic. And its named-specific benefit is limited, because Flows' `NAMED_TEMPLATE_CHANNEL_TYPES = {"WAC", "WCD"}` excludes on-premises channels from named dispatch anyway. |
| **4. Reconciliation executes synchronously in the command** rather than through the existing paced queue drain (arguably not "reusing the existing pacing" in the most literal reading of FR-032) | FR-033 requires one exportable artifact produced by the run. Work dispatched to the drain is asynchronous and the command cannot observe it, so no artifact could be produced. | Adding a second queue key plus a second permanent Celery beat drain entry was rejected: it is standing infrastructure for a one-time capability and contradicts FR-030's intent. Mitigation: the command reuses the **same** per-WABA TTL lock keys and derives its inter-WABA pace from the **same** `META_SYNC_TEMPLATES_DRAIN_BUDGET`, so Meta sees the same request rate and the scheduled sync is never double-hit for a WABA. |

**Removed after cross-repository verification**: an earlier entry justified restoring positional
`body_example` on the webhook Flows payload. Flows has no field for it and never reads it, so the change
had no downstream consumer and is dropped rather than justified.

### Follow-up debt recorded, not delivered here

- Extract `CreateTemplateTranslationUseCase` from `TemplateTranslationSerializer.create()` and an edit-path
  use case from `views.py::partial_update` (Complexity #1).
- Align `WHATSAPP_VERSION` fleet-wide onto `v25.0` with its own compatibility review (FR-040), before
  **2028-07-29**.
- `extract_template_data` drops the positional `body_example`. Pre-existing, and currently harmless because
  Flows has no field for it. Revisit only if a consumer for positional examples appears.
- Remove the dead `WHATSAPP_VERSION = settings.WHATSAPP_VERSION` module-level assignments in
  `wpp_templates/views.py:42` and `wpp_templates/serializers.py:26` — both are assigned and never read.
- Remove the stale `marketplace/wpp_templates/requests.py` entry from `.coveragerc`; the file does not exist.

The last two are trivial and in files this feature already touches, so they are folded into the relevant
tasks rather than deferred.

---

## Phase Status

- [x] **Phase 0** — research complete, all unknowns resolved → [`research.md`](./research.md)
- [x] **Phase 1** — design complete → [`data-model.md`](./data-model.md), [`contracts/`](./contracts),
      [`quickstart.md`](./quickstart.md)
- [ ] **Phase 2** — task generation (`/speckit-tasks`, not produced by this command)
