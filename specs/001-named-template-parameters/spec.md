# Feature Specification: Named WhatsApp Template Parameters — Integrations Engine

**Feature Directory**: `specs/001-named-template-parameters`

**Created**: 2026-09-17

**Status**: Draft

**Service**: `weni-integrations-engine`

**Upstream product spec**: [`weni-ai/vtex-cx-engine-specs` PR #10](https://github.com/weni-ai/vtex-cx-engine-specs/pull/10) — `specs/008-named-template-variables/spec.md` at commit `8bf459d` (revision of 2026-09-03)

**Input**: "Based on this product spec, evaluate what needs to be done in the integrations-engine application and create our engineering spec."

---

## Context & Scope *(mandatory)*

Meta's WhatsApp templates can declare `parameter_format: "named"`, write their body as `Olá {{nome}}, sua cota {{cota}} vence hoje`, and receive values as `{"type": "text", "parameter_name": "nome", "text": "João"}`. The Weni platform treats every template as positional from end to end, so a named template **breaks silently today**: it syncs in, this service records it with `variable_count = 0` and no parameter metadata, the delivery layer never substitutes its placeholders, and Meta either rejects the send or the recipient sees a literal `{{nome}}` in the message.

The product spec spans five repositories. **This spec covers only `weni-integrations-engine`**, which the product spec's component-to-service mapping assigns five responsibilities:

| # | Responsibility | Product spec reference |
| --- | --- | --- |
| R1 | Body format detection, parameter name and example validation, submission to Meta | Component mapping row 1 |
| R2 | Local template mirror carrying parameter format, parameter names and named examples | Component mapping row 2 |
| R3 | Scheduled and webhook template sync; push to the Flows template registry | Component mapping row 3 |
| R4 | One-time reconciliation of the existing fleet and the broken-template report | Component mapping row 4 |
| R5 | Meta Graph API version for template create, update and list | Component mapping row 5 |

**Explicitly owned by other services and out of scope here** (listed so reviewers do not look for them): the Flows template registry and its read surfaces; the parameter policy (required / default / contact-field fallback); the broadcast write contract, format-match validation, channel-capability check and per-recipient resolution; the delivery layer's named substitution (`mailroom`, `goflow`); the provider payload assembly with `parameter_name` (`courier`).

Because of that split, **this service never dispatches a message and never resolves a value for a recipient.** Its entire contribution is to make the parameter format and the parameter names *true, complete and durable* in the local mirror and in what it pushes to Flows. Every downstream layer's correctness depends on that, which is why the product spec's rollout gate (BD-016) cannot be satisfied until this service ships.

---

## Clarifications

### Session 2026-09-17

- Q: `WHATSAPP_VERSION` is joined into `WHATSAPP_API_URL`, the base URL for every Meta client in this service — not only the template client — so raising it to support `parameter_format` would also move product catalogs, product batch upload, commerce settings, phone numbers, business profile, OAuth, credit sharing and onboarding. One global raise, a template-scoped setting, or a scoped setting now with the global raise tracked separately? → A: **A template-scoped version setting now, with the fleet-wide alignment tracked as a separate change.** This unblocks the defect fix without coupling it to a compatibility review of the VTEX product pipeline and the commerce surfaces, makes rollback surgical, and keeps the resulting version divergence explicit and owned rather than permanent. Recorded as FR-039 and FR-040. This is the one point where the product spec's assumption — that the version is "a single environment setting … a configuration change with a compatibility review" — does not hold in this codebase.
- Q: Reconciliation must be resumable, re-runnable and must produce a report an operator can act on, but the repository has no template management command and no reporting surface to extend. What triggers it and where does the report go? → A: **An operator-triggered management command that reuses the existing paced queue and per-WABA locks, keeps progress in Redis, and reports through structured logs plus one exportable artifact.** No new model, read surface or permission is introduced for a one-time capability. Recorded as FR-030, FR-031, FR-032 and FR-033.

### Review session 2026-09-17 (second pass)

A review of the first draft raised five findings, all upheld. Two were contradictions inside this spec, two were factual errors about current behaviour, and one was an omission.

- Q: FR-003 forbade inferring the parameter format from body text "on any code path", while FR-019 required the authoring path to detect the format from the body. Which wins? → A: **Both, scoped by time.** The prohibition applies to a template that already exists at Meta, where a recorded value exists and body text is an unreliable classifier. Before creation there is no recorded value and the author's body is the only declaration available, which is exactly what the product spec's design vision describes. FR-003 now carves authoring out explicitly and requires a locally detected format to be superseded by Meta's on first sync.
- Q: Is `GET /project/templates/details/` a template read surface? → A: **No.** It returns `{app_uuid, templates_uuid}` and resolves a Meta `message_template_id` to local UUIDs; it carries no body, format or names. Removed from Story 5, from FR-035 and from the gap analysis, where it is now recorded as having no gap. The real read surfaces are the template list and the template detail.
- Q: Can the library creation path record the parameter format? → A: **No, and requiring it was a defect in the first draft.** Its request payload carries `library_template_name` rather than body text, and Meta's creation response returns only an id, a status and a category. FR-014 and FR-015 now require a *format not yet known* state that the existing post-creation sync resolves, rather than a positional default that would fight that sync.
- Q: When a body's placeholders and `body_text_named_params` disagree, what actually lands in the mirror? → A: **The body's names as the declared set, examples only where Meta supplied them, plus an anomaly marking that retains both sets.** The first draft said "report it, don't guess" without saying what is stored, which left implementers to pick a side. Recorded in FR-011.
- Q: Which Graph API version? → A: **Floor `v23.0`, exact target pinned in planning.** Meta's documentation demonstrates the capability on `v23.0` and its changelog does not record the introducing version, so no lower bound is assumable. Recorded in FR-038.

---

## Current State & Gap Analysis *(mandatory)*

This is the evaluation the request asked for: what exists today in this repository, and what is missing. Field, task and function names are the current ones.

### Data model — `marketplace/wpp_templates/models.py`

| Surface | Today | Gap |
| --- | --- | --- |
| `TemplateTranslation` | `body`, `body_example` (`ArrayField(CharField)`), `footer`, `variable_count`, `language`, `country`, `namespace`, `external_id`, `message_template_id`, `status` | No parameter format. No parameter names. No named example storage — `body_example` is a flat string array and structurally cannot hold `{param_name, example}` pairs |
| `variable_count` | Written as literal `0` on **all three** write paths: `serializers.py` (manual create), `usecases/template_sync.py` (sync), `usecases/template_library_creation.py` (library create) | Never derived from the body. A named template is therefore indistinguishable from a template with no parameters |
| Latest migration | `0013_auto_20260410_1837` | A new migration is required |
| `namespace`, `external_id` | Declared on the model, never read or written anywhere in the repo | Pre-existing dead fields; not touched by this feature |

### Authoring — `marketplace/wpp_templates/serializers.py`, `views.py`

| Surface | Today | Gap |
| --- | --- | --- |
| Meta create payload | `TemplatesRequests.create_template_message()` sends `{name, category, components, language}` | No `parameter_format`. Meta therefore defaults the template to positional and **rejects a `{{nome}}` body**, so authoring a named template in Weni fails today with an opaque provider error |
| Body variable validation | **None.** No regex on `{{...}}`, no count, no sequence check, no duplicate check anywhere in the repo | Format detection, mixed-format rejection, duplicate-name rejection, Meta naming-rule validation and example-per-name validation all have to be built from zero |
| `extract_body_example()` (`template_helpers.py`) | Flattens *every* value of Meta's `example` dict into a flat list | Given `example.body_text_named_params`, it would extend a `CharField` array with dict objects — a corruption or write failure, not a graceful skip. Must be made format-aware |
| `partial_update` (edit path) | Rebuilds components and calls `update_template_message()`; never touches `body_example` or `variable_count` | Editing a named template's body would leave stale parameter names in the mirror |
| Client / service / interface signatures | `create_template_message(waba_id, name, category, components, language)` across `clients/facebook/client.py`, `services/facebook/service.py`, `interfaces/facebook/interfaces.py` | All three need the parameter format threaded through |

### Sync — `marketplace/wpp_templates/usecases/template_sync.py`, `tasks.py`

| Surface | Today | Gap |
| --- | --- | --- |
| `refresh_whatsapp_templates_from_facebook` (beat, daily) → paced Redis queue → `task_drain_paced_queue` (per minute, budget 30) → `task_sync_whatsapp_templates_item` | Fetches Meta's list once per WABA, applies it to every app sharing that WABA, honours the per-WABA TTL lock | **No change needed.** Cadence, pacing and locking are independent of parameter format |
| `TemplateSyncUseCase.sync_templates()` | Reads the BODY component's `text` and `example`; writes `variable_count = 0` unconditionally | Must read `parameter_format`, derive and store the ordered parameter names, store the named examples, and stop writing a constant zero for named templates |
| Bulk push to Flows | `FlowsClient.update_facebook_templates()` → `PATCH /template/{flow_object_uuid}/` with `{"data": <raw Meta list>}`, sent **before** the local upsert | Shape is already correct — it forwards Meta's payload verbatim, so `parameter_format` and `body_text_named_params` reach Flows for free. Must be verified that nothing strips or reshapes it |
| Header/footer variable skip | **Does not exist in this service.** Every template Meta returns is processed | The product spec's skip rule lives in Flows' `update_local_templates`. Nothing to build here; noted so it is not mistakenly implemented twice |
| Library templates | `TemplateCreationUseCase._save_template_in_db()` writes `body = ""`, `footer = ""`, `variable_count = 0`, and reads only `id`, `status` and `category` from Meta's response | This path **cannot** know the format at creation time: the request payload carries `library_template_name` rather than body text, and Meta's creation response states no format. Library templates can be named, so the row must not be defaulted to positional in a way that fights the sync 8 hours later, which is the path that actually learns the format |

### Update paths — `marketplace/wpp_templates/utils.py`, `webhooks/facebook/`

| Surface | Today | Gap |
| --- | --- | --- |
| `update_templates_by_webhook` → `TemplateWebhookEventProcessor` | Handles `message_template_status_update`, `template_correct_category_detection`, `template_category_update` | Routing unchanged |
| `extract_template_data(translation)` | **Rebuilds** `{name, components, language, status, category, id}` from the local mirror and posts it to `POST /template/{flow_object_uuid}/template-sync/`. Already drops `body_example` entirely | **The highest-risk regression in the change** (product spec BD-015). A routine status webhook would overwrite what the bulk sync recorded in Flows, silently returning a working named template to the broken state. Must carry the parameter format and the named examples. Note the positional `body_example` is *already* being dropped here today — a pre-existing defect on the same line of code |
| Webhook app lookup | `App.objects.filter(config__wa_waba_id=waba_id)` only — misses apps whose WABA lives at `config.waba.id`, unlike the sync path which checks both | Pre-existing inconsistency. Flagged as a risk to the feature's coverage; fixing it is a judgement call for planning, not a requirement of this spec |

### Read surfaces — `marketplace/wpp_templates/serializers.py`, `urls.py`

| Surface | Today | Gap |
| --- | --- | --- |
| `GET /api/v1/apps/{app_uuid}/templates/` and `/{uuid}/` | `TemplateMessageSerializer` → nested `TemplateTranslationSerializer` exposing `variable_count` read-only | Neither the format nor the parameter names are published, so the Weni template list cannot mark a template as named or show its parameter names |
| `GET /api/v1/project/templates/details/` | `TemplateDetailUseCase` → `WhatsappCloudDTO`, which is `{app_uuid, templates_uuid}` | **No gap.** This is a UUID-resolution endpoint — given a Meta `message_template_id` it returns the matching app and template UUIDs. It exposes no body, no format and no parameter names, so there is nothing here to extend. Listed to correct an earlier reading of this spec that treated it as a template read surface |

### Provider version — `marketplace/settings.py`

| Surface | Today | Gap |
| --- | --- | --- |
| `WHATSAPP_VERSION` | `env.str("WHATSAPP_VERSION", default="v16.0")` | `parameter_format` and `body_text_named_params` do not exist on v16.0. Named templates cannot be created or read at all until this is raised |
| Blast radius | `WHATSAPP_VERSION` is joined into `WHATSAPP_API_URL`, which is the `BASE_URL` of the **entire** `FacebookAuthorization` client hierarchy — product catalogs, product batch upload (the VTEX pipeline), commerce settings, phone numbers, business profile, OAuth, credit sharing and onboarding — plus the on-premises WhatsApp views and `apis.py` | The product spec calls this "a single environment setting … a configuration change with a compatibility review". In this codebase it is not contained: raising it moves roughly thirty Graph endpoints across unrelated product surfaces at once. Resolved by scoping a version to the template surfaces and tracking the fleet-wide alignment separately — see Clarifications, FR-039 and FR-040 |

### Reconciliation

No template backfill, reconcile or resync management command exists. The only management command in the repository is `edaconsume`. The reusable patterns are the paced Redis queue with per-WABA TTL locks (`marketplace/core/pacing/`), the on-demand per-app sync (`TemplateSyncUseCase.request_sync`), and the Redis-backed progress map used by library template polling (`template_status:{app_uuid}`, 24h TTL).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A named template synced from Meta stops being silently broken (Priority: P1)

A WhatsApp Business Account contains a named template, authored either in Weni or directly in Meta's panel. The scheduled sync runs. The template is recorded with its parameter format and its ordered parameter names and examples instead of landing with zero parameters, and Meta's payload — which already carries the format — reaches the Flows registry intact.

**Why this priority**: This is the active defect and the spine of the whole feature. Nothing downstream can work until the format and the names are true in the mirror and in what Flows receives, and every other story in this spec depends on this data existing. It is also the only story that fixes something already broken in production.

**Independent Test**: Sync a WABA whose Meta response contains one named template (`parameter_format: "named"`, body `Olá {{nome}}, sua cota {{cota}}`, `example.body_text_named_params` for both names) and one positional template. Assert the named translation records the named format, the two names in body order with their examples, and a parameter count of two; assert the positional translation is byte-identical to today's result; assert the payload sent to `PATCH /template/{flow_object_uuid}/` still forwards Meta's list verbatim including `parameter_format`.

**Acceptance Scenarios**:

1. **Given** Meta returns a template with `parameter_format: "named"`, **When** the sync processes it, **Then** the translation records the named format, the parameter names in the order they appear in the body, and one example value per name.
2. **Given** Meta returns a template with no `parameter_format` key, **When** the sync processes it, **Then** the translation is recorded as positional, because that is Meta's documented default.
3. **Given** Meta returns `parameter_format` in a different case (`"NAMED"` as the Graph API reference documents, versus `"named"` as the creation payload documents), **When** the sync processes it, **Then** both are recognised as the same format.
4. **Given** Meta returns an unrecognised `parameter_format` value, **When** the sync processes it, **Then** the translation is recorded as positional, the condition is logged as an anomaly with the app and template identifiers, and the format is never guessed from the body text.
5. **Given** a named template whose body declares names, **When** it is recorded, **Then** its parameter count is the number of declared names and is never a constant zero.
6. **Given** a named template whose body placeholders and whose `body_text_named_params` declare different name sets, **When** it is recorded, **Then** the body's names become the declared set, an example is stored only for the names Meta supplied one for, the translation is marked anomalous with both observed name sets retained, and it is not presented as ready for named dispatch.
7. **Given** a named template with zero placeholders in its body, **When** it is recorded, **Then** it is valid, with an empty parameter name list and a parameter count of zero.
8. **Given** a named template whose parameter names have changed at Meta after a re-review, **When** the next sync runs, **Then** the stored names are replaced by Meta's, in place, with no duplicate template or translation created.
9. **Given** a WABA shared by several apps, **When** one Meta list response is applied to all of them, **Then** each app's mirror records the same format and names, and the existing per-WABA TTL lock and drain budget are unchanged.
10. **Given** a library template created through the library path, **When** Meta's creation response does not state a parameter format — which is the normal case, since that response carries only an id, a status and a category, and the request carries no body text — **Then** the translation is left with its format not yet known rather than defaulted to positional, is not offered for named dispatch, and has its format resolved authoritatively by the post-creation sync that already runs for pending library templates.

---

### User Story 2 — The format and the names survive every update path (Priority: P1)

A named template that already synced correctly receives a routine status-change webhook from Meta. The payload this service rebuilds and posts to Flows carries the parameter format and the named examples, so the status change does not clear what the bulk sync recorded.

**Why this priority**: Same priority as Story 1 and deliberately separate from it, because it is a different code path with a different failure mode. The webhook path *reconstructs* the payload from the local mirror rather than forwarding Meta's, so it is the one place where an ordinary status change can silently undo the fix. The product spec calls this the highest-risk regression in the entire change (BD-015). A correct Story 1 with a broken Story 2 degrades back to today's defect within hours of the next approval event.

**Independent Test**: Take a translation recorded as named with two parameter names and examples. Fire `message_template_status_update` and `template_category_update`; after each, assert that the format and the names are still recorded locally and that the `template_data` posted to `POST /template/{flow_object_uuid}/template-sync/` contains the parameter format and the named examples. Fire `template_correct_category_detection`; assert that the locally recorded format and names are unchanged and that Flows is **not** called — that event is proxied to Commerce only. Gallery re-sync (scenario 5) is not part of this Independent Test; it depends on Story 1's recording path.

**Acceptance Scenarios**:

1. **Given** a named translation, **When** a `message_template_status_update` event arrives, **Then** the rebuilt `template_data` carries the parameter format and the named examples, and the locally recorded format and names are unchanged.
2. **Given** a named translation, **When** a `template_category_update` event arrives, **Then** the same holds.
3. **Given** a named translation, **When** a `template_correct_category_detection` event arrives, **Then** the locally recorded format and names are unchanged, and nothing is posted to Flows.
4. **Given** a positional translation, **When** a `message_template_status_update` or `template_category_update` event arrives, **Then** the rebuilt `template_data` reports the positional format and is otherwise unchanged from today. **When** a `template_correct_category_detection` event arrives, **Then** the locally recorded values are unchanged and Flows is not called.
5. **Given** a named translation belonging to a gallery template, **When** a status event arrives and the handler triggers a full re-sync instead of posting to Flows, **Then** the format and names are preserved by that re-sync.
6. **Given** a named template edited through this service's own update endpoint, **When** the body's parameter names change, **Then** the mirror's names are re-derived from the submitted body, and no attempt is made to change the parameter format at Meta.

---

### User Story 3 — Authoring a named template in Weni actually reaches Meta as named (Priority: P1)

An author writes a body containing named variables in Weni. The service detects the format from the body, validates the names and the examples before submission, and submits the template to Meta declaring the named format with one example per name. Invalid bodies are rejected with field-level errors and nothing is created.

**Why this priority**: P1 because it is the customer's stated path and because authoring is broken today in a way that produces an opaque Meta error rather than a useful message. It is ranked after Stories 1 and 2 because a template authored in Meta's own panel must be a first-class citizen regardless — sync is the load-bearing path, authoring is the convenience path that gives fast feedback.

**Independent Test**: Submit a translation whose body is `Olá {{nome}}, sua cota {{cota}} vence em {{data}}` with an example per name. Assert the payload sent to Meta declares the named parameter format and carries `body_text_named_params` with three entries. Then submit a mixed body, a duplicated name, a name that breaks Meta's rule, and a body with a missing example, and assert each is rejected with a field-level error naming the offending parameter and that no local record and no Meta call result from any of them.

**Acceptance Scenarios**:

1. **Given** a body containing only named variables with an example per name, **When** it is submitted, **Then** the Meta create payload declares the named parameter format and carries one `{param_name, example}` entry per name, and the translation is recorded as named.
2. **Given** a body containing only positional variables, **When** it is submitted, **Then** the submission and the resulting record are unchanged from today, and the author never has to choose a format explicitly.
3. **Given** a body mixing named and positional variables, **When** it is submitted, **Then** it is rejected with a field-level error stating that a template uses one parameter format and identifying the variables of the minority format, and nothing is created.
4. **Given** a body repeating the same parameter name, **When** it is submitted, **Then** it is rejected with a field-level error naming the duplicated parameter, and nothing is created.
5. **Given** a parameter name that breaks Meta's documented rule for named parameters, **When** it is submitted, **Then** it is rejected with a field-level error stating the rule, and nothing is created.
6. **Given** a named parameter with no example value, **When** it is submitted, **Then** it is rejected with a field-level error identifying that parameter, because Meta requires an example per parameter for review.
7. **Given** a body whose names pass local validation but which Meta rejects, **When** the submission fails, **Then** Meta's reason is surfaced without being reinterpreted, and no local record is created.
8. **Given** a named example set returned or submitted for a named template, **When** it is stored, **Then** it is never written into the positional example array, and a positional example set is never written into the named structure.

---

### User Story 4 — The existing fleet is classified and the broken templates are counted (Priority: P2)

An operator runs reconciliation across templates recorded before parameter format existed. Every template's format and, for named ones, its parameter names are corrected against Meta. Templates recorded with a named body and no parameters — the fleet broken by the pre-existing defect — are identified in a report.

**Why this priority**: P2 because Stories 1–3 already make every *future* sync and every *future* authoring correct, which is the bulk of the value. Reconciliation converts an unknown number of already-broken templates into a finite, actionable number. Note it is also possible to run reconciliation *only* after Story 1 exists, since it converges to the same recorded values.

**Independent Test**: Seed translations recorded with a named body and `variable_count = 0` alongside correctly recorded positional ones. Run reconciliation against a stubbed Meta response. Assert every template's format is set, named ones gain their names and examples, the previously broken ones appear in the report, no duplicate template or translation is created, and a second run produces an identical result and an identical report.

**Acceptance Scenarios**:

1. **Given** templates recorded before parameter format existed, **When** reconciliation runs, **Then** each one's format is set from Meta and named ones gain their parameter names and examples.
2. **Given** a translation whose body contains named placeholders and which has no recorded parameters, **When** reconciliation runs, **Then** it is identified in a report an operator can act on, and it is not silently left in place.
3. **Given** reconciliation has already run, **When** it runs again, **Then** it converges to Meta's values and creates no duplicate template or translation.
4. **Given** reconciliation is interrupted partway, **When** it is restarted, **Then** it resumes rather than restarting from the beginning, and no template is left in a state a re-run cannot correct.
5. **Given** reconciliation encounters a WABA whose per-WABA TTL lock is held by a recent scheduled sync, **When** it would otherwise fetch that WABA, **Then** it skips the WABA, does not mark it done, does not write concurrently, and records a WABA-level `skipped_recent_sync` that is **not** one of the five translation categories. The WABA remains eligible on resume. **Given** the same WABA is later processed by both paths at different times, **Then** both apply Meta's list through the same recording path, they converge, last write wins, and neither produces a duplicate record.
6. **Given** reconciliation across an account with many templates, **When** it runs, **Then** it respects the existing Meta pacing and per-WABA locking and does not interrupt the scheduled sync.

---

### User Story 5 — The read surfaces publish the format and the names (Priority: P2)

An integrator or the Weni template list reads a template through this service's API and discovers whether it is named or positional and what its parameters are called, without opening a support ticket or inspecting the body text.

**Why this priority**: P2 because it delivers no delivery-path capability, but the product spec's design vision requires the template list to show the format without a template being opened, and that list is served from here. It is independently testable the moment Story 1 records the data.

**Independent Test**: Read a named template and a positional template through the template list and the template detail — the two surfaces that return template content. Assert the named one reports the named format with its parameter names, the positional one reports the positional format and keeps `variable_count`, and no positional index appears beside a named parameter in either response.

**Acceptance Scenarios**:

1. **Given** a named template, **When** it is read, **Then** the response states its parameter format and lists its parameter names per translation.
2. **Given** a positional template, **When** it is read, **Then** the response keeps `variable_count` and reports the positional format, so one consumer can handle both.
3. **Given** a named template, **When** it is read, **Then** no positional index or slot number is published beside any parameter name.
4. **Given** a template whose translations disagree on parameter format, **When** it is read, **Then** the disagreement is visible rather than collapsed into one arbitrary value.
5. **Given** a caller reading templates, **When** the response is built, **Then** it contains only templates belonging to apps the caller's project is authorised for, exactly as today.

---

### User Story 6 — Positional templates and existing integrations are untouched (Priority: P3)

Every positional template continues to sync, author, update and read exactly as it does today. Named and positional templates coexist in the same app indefinitely.

**Why this priority**: P3 because it adds no capability, but it protects live traffic and the platform's own bulk-send experience. It is verified by the existing suites rather than by new behaviour.

**Independent Test**: Run the existing template sync, serializer, view and webhook suites unchanged and confirm identical behaviour. Then sync an account containing both formats and confirm each is recorded in its own format with neither affecting the other.

**Acceptance Scenarios**:

1. **Given** any positional template, **When** it is synced, authored, updated or read, **Then** its behaviour and its recorded values are unchanged from today, including a parameter count of zero.
2. **Given** an app containing both named and positional templates, **When** a sync runs, **Then** each is recorded in its own format and neither affects the other.
3. **Given** the existing test suite, **When** it runs against this change, **Then** it passes without modification except where a test asserts the absence of the new fields.

---

### Edge Cases

**Provider data**

- Meta omits `parameter_format`: recorded as positional, per Meta's documented default.
- Meta returns `parameter_format` in a different case, or as an unrecognised string: case is normalised; an unrecognised value is recorded as positional and logged as an anomaly, never inferred from the body.
- A named template's body placeholders and its `body_text_named_params` declare different name sets: the body's names are stored as the declared set, examples are stored only where Meta supplied them, the translation is marked anomalous with both sets retained, and it is not offered for named dispatch (FR-011). Storing the body's names is not a preference between sources — it is the only ordered source and the set a send must satisfy — and the anomaly marking is what keeps the choice from being silent.
- A library template whose format Meta has not stated at creation: left with its format not yet known and resolved by the post-creation sync (FR-014, FR-015). A *format not yet known* translation is distinct from a positional one and from a broken one, and all three must stay distinguishable in the reconciliation report.
- A named template declares a name in `body_text_named_params` with an empty example: the example is recorded as absent and the condition is reported; the template is still recorded as named.
- A named template with zero body placeholders: valid, with an empty name list.
- A template Meta reports as positional whose body contains named placeholders: recorded as positional because Meta is authoritative, and logged as an anomaly — this is the shape reconciliation uses to detect the pre-existing defect.
- Meta returns named examples for a header (`header_text_named_params`): ignored. This release names body parameters only.
- Meta's template list is unavailable or slow: existing sync error handling and pacing apply; already-recorded formats and names are retained.
- A Meta account whose sync is disabled by `ignores_meta_sync`: skipped exactly as today, and therefore never reconciled until the flag is cleared — this must be visible in the reconciliation report rather than counted as classified.

**Authoring**

- A body containing both `{{nome}}` and `{{1}}`: rejected with a field-level error identifying the minority-format variables.
- A body repeating a name: rejected with a field-level error naming the duplicate.
- A name Meta rejects even though local validation accepted it: Meta's reason is surfaced and no template is created; local validation is never made stricter than Meta's documented rule.
- A named parameter with no example: rejected before submission.
- A body whose text contains literal curly braces that are not a placeholder: must not be detected as a parameter.
- An author edits a named template's body at Meta through this service: the names are re-derived from the submitted body and the parameter format is never sent as a change.
- Authoring submitted while the downstream layers are not yet aware of named templates: the named authoring path is gated so a named template cannot be created into a pipeline that would deliver it broken.

**Update paths and lifecycle**

- A status-only webhook for a named template: the format and the names are preserved. An update that clears them is a defect and must be detectable from the observability requirement.
- A named template pending or rejected at Meta: its recorded format and names persist through its normal lifecycle.
- A translation removed at Meta: deleted locally as today, together with its parameter metadata.
- A translation added to a named template declaring different names from its siblings: each translation's own names are recorded; the divergence is reported. The dispatch rejection for it belongs to Flows.
- A template whose translations disagree on parameter *format*, not just on names: recorded per translation and reported; the template-level read value must not collapse the disagreement.

**Reconciliation**

- Interrupted partway: resumable, and a re-run converges to Meta's values.
- Running while the scheduled sync holds the per-WABA TTL lock: reconciliation skips that WABA, does not mark it done, and records a WABA-level `skipped_recent_sync`. It does not write concurrently. Once the lock is clear, a resume processes the WABA; both paths then converge through the same recording use case, last write wins, no duplicate records.
- An app whose WABA no longer exists or whose token is invalid: recorded as unclassifiable in the report rather than failing the whole run.
- An account with thousands of templates: respects the existing pacing and per-WABA locking.

**Provider version**

- Meta rejects a create because the configured Graph version does not support `parameter_format`: surfaced as a configuration error naming the unsupported capability, not as a template validation error.
- The template version is raised while the shared base URL stays where it is: the two must be allowed to diverge without any Meta client silently reading the wrong one, and the divergence must be visible to whoever later performs the fleet-wide alignment (FR-039, FR-040).

**Tenancy and privacy**

- Template records, parameter names and examples are scoped to the app and its project, exactly as today. Nothing resolves a format or a name across app boundaries.
- Parameter names and example values are template metadata, not recipient data. The product spec's prohibition on logging values targets per-recipient broadcast values, which this service never receives; example values may therefore appear in error messages returned to the author who submitted them, and must not be logged at info level as a matter of hygiene.

---

## Requirements *(mandatory)*

Each requirement traces to the upstream product spec's functional requirements (`PS FR-nnn`), binding decisions (`PS BD-nnn`) or non-functional requirements (`PS NFR-nnn`).

### Template mirror data

- **FR-001**: A template translation MUST record a parameter format of either named or positional, taken from Meta's template response, and that recorded value MUST be the only source any consumer reads. *(PS FR-001, FR-004, BD-002)*
- **FR-002**: A template whose parameter format Meta does not state MUST be recorded as positional. A value differing only in letter case MUST be recognised. An unrecognised value MUST be recorded as positional and logged as an anomaly. *(PS FR-002, Edge Cases)*
- **FR-003**: For a template that **already exists at Meta**, the service MUST NOT infer its parameter format from body text, parameter count, or the shape of a request. The value recorded from Meta is the only source. Two things are explicitly not inference under this rule, and are required elsewhere in this spec: deriving parameter *names* from the body of a template Meta has already declared named (FR-004), and detecting the format from the body an author wrote **before the template exists at Meta** (FR-020), where no recorded value can exist yet. A format detected at authoring time is a submission decision, not a recorded classification, and MUST be superseded by Meta's value on the first sync that reports it. *(PS FR-004, BD-002)*
- **FR-004**: A named translation MUST record the set of parameter names it declares, in the order they appear in the body, together with one example value per name. *(PS FR-006, FR-016, FR-017)*
- **FR-005**: The recorded order MUST be treated as display metadata only. The service MUST NOT compute, store, publish or transmit a positional index for a named parameter. *(PS FR-007, FR-034, BD-003)*
- **FR-006**: The recorded parameter count for a named translation MUST be the number of names it declares. For a positional translation it MUST remain exactly as today. *(PS FR-016, FR-051)*
- **FR-007**: Named example values MUST NOT be written into the positional example store, and positional example values MUST NOT be written into the named structure. The example extraction used on both paths MUST be format-aware. *(PS FR-017, FR-051)*
- **FR-008**: Parameter format and parameter names MUST be recorded per translation, matching Meta's own granularity. A template-level format published to consumers MUST be derived from its translations and MUST NOT collapse a disagreement between them into one arbitrary value. *(PS FR-006, FR-024, BD-004)*

### Template sync

- **FR-009**: The scheduled sync MUST record the parameter format for every template it processes. *(PS FR-015)*
- **FR-010**: The scheduled sync MUST record a named template's parameter names and examples, and MUST NOT record a named template as having zero parameters when its body declares them. *(PS FR-016)*
- **FR-011**: When a named template's body placeholders and its `body_text_named_params` declare different name sets, the mirror MUST record: the **body's** names as the declared set, because the body is the only ordered source and is what a send has to satisfy; an example only for those names Meta actually supplied one for, with the remainder left without an example rather than borrowing or inventing one; **and** a marking that the translation is anomalous, retaining both observed name sets so an operator can see the divergence. The marking is what keeps this from being a silent guess — an anomalous translation MUST NOT be presented as ready for named dispatch by any read surface, MUST NOT be pushed as a clean named template on the update path, and MUST be distinguishable from the zero-parameter case that reconciliation reports as broken. The service MUST NOT resolve the divergence by editing either source at Meta. *(PS FR-006, BD-002, Edge Cases — Integration; the dispatch rejection itself is owned by Flows)*
- **FR-012**: When a sync observes that a named template's parameter names have changed at Meta, the service MUST replace the stored names in place, without creating a duplicate template or translation. *(PS FR-023)*
- **FR-013**: The bulk push to the Flows registry MUST continue to forward Meta's template list verbatim, so `parameter_format` and the named examples reach Flows unmodified. No field may be stripped, renamed or reshaped on this path. *(PS FR-018)*
- **FR-014**: The library template creation path MUST record the parameter format when Meta's creation response states it. It MUST NOT derive a format from the request payload, which carries no body text, and MUST NOT write a positional format as a stand-in for a format it has not been told. A translation created by this path whose format Meta has not yet stated MUST be left in a *format not yet known* state that the first sync resolves authoritatively. *(PS "Library template polling" stage; corrects an earlier draft that asked this path for data it does not have)*
- **FR-015**: A translation whose format is not yet known MUST NOT be presented as ready for named dispatch by any read surface, MUST NOT be counted by reconciliation as either classified or broken, and MUST be resolved by the existing post-creation library sync rather than by a new polling mechanism. *(PS BD-016)*
- **FR-016**: The sync cadence, its paced queue, its drain budget and its per-WABA time-to-live lock MUST be unchanged by this feature. *(PS "Scheduled dispatcher — No change")*

### Update paths

- **FR-017**: The payload this service rebuilds from the local mirror for the Flows single-template sync endpoint MUST carry the parameter format and, for a named template, its named examples. A status-only or category-only update MUST NOT clear either. *(PS FR-019, BD-015)*
- **FR-018**: Every webhook event type this service handles MUST preserve the locally recorded parameter format and parameter names. *(PS FR-019, BD-015)*
- **FR-019**: When a template is edited through this service, the stored parameter names MUST be re-derived from the submitted body, and the service MUST NOT attempt to change the parameter format at Meta or convert a template between formats. *(PS FR-005, BD-013)*

### Authoring and validation

- **FR-020**: The authoring path MUST detect the parameter format from the body the author wrote and MUST submit the template to Meta declaring that format. Choosing a format MUST be a property of the body, not a separate setting the author selects. *(PS FR-009, FR-014)*
- **FR-021**: A named submission MUST carry one example value per parameter name, in Meta's named-example shape. *(PS FR-010)*
- **FR-022**: A body mixing named and positional variables MUST be rejected with a field-level error stating that a template uses one parameter format and identifying the variables of the minority format. Nothing MUST be created locally or at Meta. *(PS FR-011)*
- **FR-023**: A body repeating the same parameter name MUST be rejected with a field-level error naming the duplicated parameter. *(PS FR-012)*
- **FR-024**: A parameter name MUST be validated against Meta's documented rule for named parameters before submission. The service MUST NOT impose a stricter rule of its own, and MUST surface Meta's rejection reason when Meta proves stricter. *(PS FR-013)*
- **FR-025**: A named parameter with no example value MUST be rejected with a field-level error identifying that parameter. *(PS FR-010, Journey 1 scenario 6)*
- **FR-026**: Positional authoring MUST behave exactly as today, including its handling of body examples and its recorded parameter count. *(PS FR-014, FR-051)*
- **FR-027**: The named authoring path MUST be controllable by configuration, so a named template cannot be created into a pipeline whose delivery and channel layers are not yet aware of named parameters. *(PS BD-016)*

### Reconciliation

- **FR-028**: A reconciliation capability MUST classify every already-recorded template against Meta, setting its parameter format and, for named templates, its parameter names and examples. *(PS FR-020)*
- **FR-029**: Reconciliation MUST identify every translation recorded with a named body and no parameters, and MUST report them in a form an operator can act on. *(PS FR-021; resolves Q2)*
- **FR-030**: Reconciliation MUST be operator-triggered rather than scheduled, so it cannot run unannounced in production, and MUST NOT require a new persisted model, read surface or permission. *(Constitution II; resolves Q2)*
- **FR-031**: Reconciliation MUST be safe to re-run, MUST converge to Meta's values, MUST create no duplicate template or translation, and MUST be resumable after an interruption by reading persisted progress rather than restarting from the beginning. *(PS FR-022, NFR-007)*
- **FR-032**: Reconciliation MUST run without interrupting the scheduled sync or any other template operation, and MUST reuse the existing Meta pacing and per-WABA locking rather than introducing its own. Reusing the lock means: when the lock is held, reconciliation MUST skip that WABA rather than interleave writes; it MUST NOT mark the WABA done, so a resume retries it. *(PS NFR-007)*
- **FR-033**: The reconciliation report MUST be emitted both as structured log records, so a run is observable while it is in progress, and as a single exportable artifact an operator can keep and act on after the run ends. *(PS FR-021; resolves Q2)*
- **FR-034**: The report MUST distinguish templates that were corrected, templates found broken by the pre-existing defect, templates found anomalous under FR-002 or FR-011, templates whose format is not yet known under FR-014, and templates that could not be classified at all — including apps skipped because their Meta sync is disabled. These categories MUST NOT be conflated, because each one points an operator at a different action. A WABA skipped because the TTL lock is held is a **WABA-level skip** (`skipped_recent_sync`), not a sixth translation category: it MUST NOT be counted as classified, broken, or unclassifiable, and MUST remain eligible for resumption. *(PS FR-021, Edge Cases)*

### Read surfaces

- **FR-035**: The template list and template detail surfaces — the two endpoints that return template content — MUST publish a template's parameter format and, for a named template, its parameter names per translation. The project template details endpoint is a UUID-resolution surface carrying no template content and is out of scope. *(PS FR-008)*
- **FR-036**: A positional template's read shape MUST keep its existing parameter count field and report the positional format, so a single consumer handles both. *(PS FR-008, FR-051)*
- **FR-037**: No read surface MUST publish a positional index or slot number beside a named parameter. *(PS FR-007, BD-003)*

### Provider API version

- **FR-038**: Template creation, template update and template listing MUST operate at a Meta Graph API version that supports `parameter_format` and named examples. The configured default of `v16.0` predates the capability entirely, so it MUST be raised rather than worked around. **The floor is `v23.0`** — the lowest version Meta's current documentation demonstrates `parameter_format` and `body_text_named_params` on. Meta's published changelog does not state which version introduced the capability, so a lower working version could not be established and MUST NOT be assumed. Planning MUST pin one exact target at or above the floor, with a rationale that accounts for Graph API version expiry so the pinned version has usable runway, and MUST confirm against Meta's documentation at implementation time. *(PS FR-050, BD-014)*
- **FR-039**: The template surfaces MUST take their Graph API version from a template-scoped configuration value, so raising it does not move the other Meta surfaces that share the current base URL — product catalogs, product batch upload, commerce settings, phone numbers, business profile, OAuth, credit sharing and onboarding. Those surfaces MUST continue to operate at their existing version and MUST NOT regress. *(PS BD-014; resolves Q1)*
- **FR-040**: Aligning the shared Meta base URL onto the newer Graph version MUST be tracked as a separate change with its own compatibility review, and MUST NOT be a precondition for delivering this feature. The template-scoped value of FR-039 is a bridge, not the end state, and the divergence MUST be recorded where a future reader will find it. *(PS BD-014; resolves Q1)*

### Compatibility, tenancy and observability

- **FR-041**: Every positional template MUST behave and be recorded exactly as it does today across sync, authoring, update, webhook and read paths. A template's format MUST NOT affect how any other template is handled. *(PS FR-051, BD-019)*
- **FR-042**: Parameter formats, parameter names and examples MUST be scoped to the app and its project, and MUST never be resolved across app or project boundaries. *(PS NFR-008)*
- **FR-043**: Every recorded parameter format, every recorded parameter name set, every anomaly under FR-002 and FR-011, every reconciliation correction, and every rejected authoring submission MUST be observable in logs and attributable to the originating app, project and template. *(PS FR-054)*
- **FR-044**: Example values MUST NOT be written to logs at informational level. They may appear in validation errors returned to the author who submitted them. *(PS BD-020, adapted — this service never receives per-recipient values)*

### Non-Functional Requirements

- **NFR-001**: Recording a template's parameter format and parameter names MUST require no additional Meta request per template. The data MUST be taken from the list response the sync already fetches. *(PS NFR-006)*
- **NFR-002**: The parameter format and the parameter names MUST travel to Flows on the paths Flows already reads, with no new endpoint or extra round trip. *(PS FR-018, NFR-006)*
- **NFR-003**: Syncing an account of positional templates MUST show no measurable latency regression versus the current implementation. *(PS NFR-005)*
- **NFR-004**: Reconciliation MUST be bounded and observable: its progress MUST be readable while it runs, and its report size MUST be predictable for an account with thousands of templates. *(PS NFR-007, NFR-009)*
- **NFR-005**: The schema change MUST be applicable to the existing translation table without a long exclusive lock, and existing rows MUST remain valid and readable before reconciliation runs. *(PS NFR-007)*
- **NFR-006**: Validation error messages MUST name the offending field, the offending parameter when applicable, and the condition, so an author can correct the submission without contacting support. *(PS NFR-010)*
- **NFR-007**: A parameter name and an example value MUST be accepted and stored in the full character range Meta accepts, including non-ASCII and accented characters, without transformation. *(PS NFR-011)*
- **NFR-008**: Classification MUST be deterministic: the same Meta response MUST always produce the same recorded format, names and examples. *(PS NFR-012)*
- **NFR-009**: New and changed behaviour MUST ship with tests that mock Meta and Flows at the client boundary, and project coverage MUST stay at or above the 75% floor. *(Constitution VIII)*

### Key Entities

- **Parameter Format**: Named or positional. A property of the template at Meta, fixed at creation, recorded per translation because that is Meta's own granularity, and authoritative for every consumer. Defaults to positional when Meta does not state it.
- **Parameter Name**: Meta's declared identifier for one body parameter of a named template. Unique within its translation, recorded in body order for display only, never bound to a position by this service.
- **Named Example**: The example value Meta requires for each named parameter, recorded alongside its name so the webhook rebuild path can reproduce it. Distinct from, and never mixed with, the positional example array that exists today.
- **Format Anomaly**: An observed inconsistency that must be reported rather than guessed — an unrecognised format value, a disagreement between a body's placeholders and its named examples, a template Meta calls positional whose body is named, or translations of one template that disagree on format or names.
- **Reconciliation Report**: The record of the one-time classification of the existing fleet — templates corrected, templates found broken by the pre-existing defect, templates found anomalous, and templates that could not be classified.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of named templates present in a synced WhatsApp Business Account are recorded with the named format and with their parameter names, and 0% are recorded with zero parameters when their body declares them. *(PS SC-004)*
- **SC-002**: 100% of named templates retain their format and their parameter names across every webhook event type this service handles, asserted before and after each event. *(PS SC-006)*
- **SC-003**: A template authored in Weni with named variables is created at Meta with the named format and one named example per parameter, verified against the recorded Meta request payload. *(PS SC-001)*
- **SC-004**: 100% of invalid named bodies — mixed format, duplicated name, name breaking Meta's rule, missing example — are rejected before any Meta call, with the offending parameter named in the error, and produce zero local records. *(PS SC-001, NFR-010)*
- **SC-005**: Reconciliation classifies 100% of already-recorded templates on every WABA the run processes, produces a report listing every template broken by the pre-existing defect, creates zero duplicate templates or translations, and produces an identical result across re-runs. WABAs skipped because a TTL lock is held are not counted as classified in that run and remain eligible for resumption. *(PS SC-005)*
- **SC-006**: Zero positional indexes are computed, stored, published or transmitted for a named parameter anywhere in this service, verified by inspecting the mirror, the read surfaces and both Flows push payloads. *(PS SC-003)*
- **SC-007**: An integrator determines a template's parameter format and every parameter name from this service's read surfaces alone, with no support contact and no inspection of the body text. *(PS SC-017)*
- **SC-008**: 0% of positional templates change behaviour versus the current implementation, verified by the existing template sync, serializer, view and webhook suites passing unmodified, with no measurable latency regression on sync. *(PS SC-016)*
- **SC-009**: Every template surface that talks to Meta operates at a Graph version that supports `parameter_format`, and 0% of the service's other Meta surfaces — catalogs, product batch upload, commerce settings, phone numbers, profile, OAuth, credit sharing, onboarding — change the version they call, verified endpoint by endpoint before release. *(PS SC-021)*
- **SC-010**: The number of templates in the fleet broken by the pre-existing defect goes from unknown to a measured count published by the first reconciliation run. *(PS SC-005, Assumptions)*
- **SC-011**: 0% of named example values appear in informational logs. *(PS SC-020, adapted)*
- **SC-012**: 0% of library-created translations are recorded as positional before their format has been read from Meta, and 100% have their format resolved by the post-creation sync that already runs for pending library templates. *(FR-014, FR-015)*
- **SC-013**: For every template whose body names and named examples disagree, the mirror holds the body's names, holds an example only where Meta supplied one, is marked anomalous with both sets retained, and is reported in a category distinct from both the broken and the not-yet-known cases — verified with no implementer having to choose which source wins. *(FR-011, FR-034)*

---

## Assumptions *(mandatory)*

- **Meta is the authority on names and on format.** This service records and carries them; it never invents, renames or renumbers them. Local validation exists to give an author fast feedback before submission, and Meta's documented rule — unique, single strings of lowercase characters and underscores, wrapped in double curly brackets, with one example per parameter — is normative. Where the local rule and Meta's disagree, Meta wins.
- **Format is per translation in this service's model.** Meta returns `parameter_format` on each per-language message template, and this service already models one translation per language with its own `message_template_id`. Recording format per translation therefore matches the provider; the product spec's template-level read shape is satisfied by deriving a template-level value from its translations, with disagreement reported rather than collapsed.
- **Meta reports the format in more than one letter case.** Meta's creation documentation uses lowercase (`"named"`) while the Graph API reference documents the enum as uppercase (`NAMED`). Recording must be case-insensitive.
- **Parameter names are derived from the body, examples from the named example list, and the two are cross-checked.** Meta publishes the names in both places but only the body carries their order. Reading both and reporting a disagreement is what avoids guessing. When they disagree the body wins for *which names exist*, because Meta renders the body and requires a send to carry a `parameter_name` for each of its placeholders, while the examples are review metadata — but the translation is marked anomalous so that choice is never acted on as if it were clean data (FR-011).
- **Three format states exist, not two.** Named, positional, and *not yet known*. The third is not a hedge: the library creation path provably cannot learn the format at creation time, so defaulting those rows to positional would either mislabel a named library template for the eight hours until the next sync or fight the sync that corrects it. Meta's "absent means positional" default (FR-002) applies to a template Meta has actually described; it does not apply to a row this service created before ever reading that template back.
- **The Graph API version floor is `v23.0`, and the exact target is a planning decision.** Meta's current documentation demonstrates `parameter_format` and `body_text_named_params` on `v23.0`, and its published changelog does not record which version introduced the capability, so no lower bound could be established. The configured `v16.0` predates it outright. Graph API versions expire roughly two years after release, so the pinned target needs runway, which is why FR-038 requires a rationale rather than just a minimum.
- **Named parameters are body-only in this release.** Meta also supports `header_text_named_params`, which is out of scope. The product spec notes that templates with header or footer variables are skipped downstream; that skip lives in Flows, not in this service, and nothing about it changes here.
- **The Flows bulk push needs no contract change.** It forwards Meta's list verbatim, so `parameter_format` and the named examples reach Flows for free. The webhook push does need one, because it reconstructs the payload from the local mirror — which is also why it already drops the positional `body_example` today.
- **`variable_count` changes meaning only for named templates.** Positional templates keep their current constant zero. Flows computes its own count from the raw Meta payload on the bulk path, so this service's value is consumed only by its own read surfaces.
- **The Graph API version becomes template-scoped, deliberately and temporarily.** `WHATSAPP_VERSION` feeds the base URL of every Meta client in this service, so the product spec's assumption that raising it is a contained configuration change does not hold here. Q1 resolved this by scoping a version to the template surfaces and tracking the fleet-wide alignment separately (FR-039, FR-040). This accepts a known, bounded version divergence in exchange for not gating a defect fix on a compatibility review of the VTEX product pipeline and the commerce surfaces. The divergence is debt this feature is choosing knowingly, and FR-040 exists so it is owned rather than forgotten.
- **No reconciliation tooling exists to extend.** There is no template management command in the repository — only `edaconsume`. Q2 resolved reconciliation as an operator-triggered command that reuses the paced Redis queue with its per-WABA locks for pacing and a Redis progress map, following the pattern library template polling already uses, and reports through structured logs plus one exportable artifact. No new model, read surface or permission is introduced for a one-time capability, which is the outcome the constitution's simplicity principle points to.
- **Named templates already exist in customers' accounts and already fail.** How many is unknown; the first reconciliation report is what turns that into a number. This is a defect being fixed, not only a capability being added.
- **Downstream readiness gates the authoring path, not the sync path.** Recording the format and pushing it to Flows is additive and safe to ship first. Creating a *new* named template at Meta is not, because it becomes dispatchable into a pipeline that may not yet handle it — hence FR-027.
- **This service holds no per-recipient data.** The product spec's privacy rules about recipient values apply to Flows, mailroom and courier. Here the sensitive-data surface is limited to example values, which are template metadata supplied by the author.
- **The webhook app lookup inconsistency is pre-existing.** The webhook path resolves apps only by `config.wa_waba_id` while the sync path also accepts `config.waba.id`. It limits which apps receive webhook-driven updates today and will equally limit the FR-017 fix. It is recorded as a risk; whether to fix it is a planning decision.

---

## Out of Scope *(mandatory)*

- The Flows template registry, its read surfaces, the parameter policy, the broadcast write contract, per-recipient resolution and the rejection report.
- The delivery layer's named placeholder substitution and template assets (`mailroom`, `goflow`) and the provider payload assembly with `parameter_name` (`courier`).
- Converting a template between parameter formats, in either direction. Meta fixes the format at creation.
- Named parameters in a template's header, footer or buttons.
- Adding support for header or footer variables, and changing the downstream skip rule for templates that carry them.
- Any change to the sync cadence, the paced queue, the drain budget or the per-WABA locking.
- Reviving the unused `namespace` and `external_id` translation fields.
- Any change to the positional path's behaviour, including its constant parameter count.
- Aligning the service's shared Meta base URL onto the newer Graph version. FR-040 requires this to be tracked, not delivered here.
- A persisted reconciliation report model, a report read endpoint, or a permission for either.

---

## Open Questions

None. The two questions this spec raised were resolved in the 2026-09-17 session above and are recorded in the requirements they affect. The four confirmations from the product spec's 2026-08-28 session and the six from its 2026-09-03 revision are recorded upstream, and the assumptions above record the decisions this spec made on its own.
