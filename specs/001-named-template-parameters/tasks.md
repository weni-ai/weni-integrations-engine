---

description: "Dependency-ordered task list for Named WhatsApp Template Parameters — Integrations Engine"
---

# Tasks: Named WhatsApp Template Parameters — Integrations Engine

**Input**: Design documents from `/specs/001-named-template-parameters/`

**Prerequisites**: [`plan.md`](./plan.md), [`spec.md`](./spec.md), [`research.md`](./research.md),
[`data-model.md`](./data-model.md), [`contracts/`](./contracts), [`quickstart.md`](./quickstart.md),
[`.specify/memory/constitution.md`](../../.specify/memory/constitution.md)

**Scope**: `weni-integrations-engine` only. Flows, mailroom, goflow and courier own dispatch, the parameter
policy, per-recipient resolution, named substitution and the `parameter_name` provider payload. No task
below touches them. Cross-repository alignment with [`weni-ai/flows` PR #876](https://github.com/weni-ai/flows/pull/876)
(head `6f0b9d9`) is **already verified** — no task re-confirms it.

**Tests**: REQUIRED, not optional. Constitution VIII is non-negotiable and NFR-009 requires project
coverage to stay at or above 75%. Every behaviour task below is paired with a test task in the same phase.

**Organization**: grouped by user story so each is independently deliverable and independently testable
against the "Independent Test" its story defines in `spec.md`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelisable — a different file from every other `[P]` task in the same phase, and no
  dependency on an incomplete task
- **[Story]**: `US1`–`US6`, mapping to the user stories in `spec.md`. Setup, Foundational and Polish tasks
  carry no story label
- **⚠️ CT#n**: the task implements a deviation recorded in `plan.md` § Complexity Tracking entry *n*

## Path Conventions

Single Django project. All paths are relative to the repository root and follow the tree in
`plan.md` § Project Structure.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: housekeeping in files this feature touches. Neither task changes runtime behaviour.

- [X] T001 [P] Add `WHATSAPP_TEMPLATE_VERSION="v25.0"` and `WHATSAPP_NAMED_TEMPLATES_ENABLED="False"` to the
      generated development env file in `contrib/gen_env.py`, directly after the existing
      `WHATSAPP_VERSION` / `WHATSAPP_API_URL` entries at lines 51–52
- [X] T002 [P] Remove the stale `marketplace/wpp_templates/requests.py` entry from the `omit` list in
      `.coveragerc` — the file does not exist (`plan.md` § Follow-up debt)

**Checkpoint**: housekeeping done; foundational work can start.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the settings, the schema and the pure module that every user story depends on.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete.

- [X] T003 [P] ⚠️ CT#2 Add the three template-scoped settings to `marketplace/settings.py`, after
      `WHATSAPP_API_URL` (line 345): `WHATSAPP_TEMPLATE_VERSION = env.str("WHATSAPP_TEMPLATE_VERSION",
      default="v25.0")`, `WHATSAPP_TEMPLATE_API_URL = urllib.parse.urljoin(env.str("WHATSAPP_API_URL",
      default="https://graph.facebook.com/"), WHATSAPP_TEMPLATE_VERSION)`, and
      `WHATSAPP_NAMED_TEMPLATES_ENABLED = env.bool("WHATSAPP_NAMED_TEMPLATES_ENABLED", default=False)`.
      Include the comment block from `contracts/meta-graph-templates.md` recording why the version diverges
      and that `v25.0` expires **2028-07-29** (FR-039, FR-040). `WHATSAPP_VERSION` and `WHATSAPP_API_URL`
      are **not** modified
- [X] T004 [P] Add the three columns to `TemplateTranslation` in `marketplace/wpp_templates/models.py`
      (class at line 84), exactly as specified in `data-model.md`: `parameter_format =
      models.CharField(max_length=10, choices=PARAMETER_FORMAT_CHOICES, null=True, blank=True,
      default=None)`, `body_named_params = models.JSONField(default=list, blank=True)`, and
      `parameter_anomaly = models.JSONField(null=True, blank=True, default=None)`. Declare
      `PARAMETER_FORMAT_NAMED = "NAMED"`, `PARAMETER_FORMAT_POSITIONAL = "POSITIONAL"` and
      `PARAMETER_FORMAT_CHOICES` with the translation-key labels
      `WhatsApp.data.templates.parameter_format.named` / `.positional`, matching the convention
      `STATUS_CHOICES` and `CATEGORY_CHOICES` already use in this file. Declare the constants locally
      rather than importing them from `parameters.py` — the pure module must stay Django-free and the
      migration must not depend on it; T008 asserts the two declarations agree
- [X] T005 Create `marketplace/wpp_templates/migrations/0014_templatetranslation_parameters.py` with
      `dependencies = [("wpp_templates", "0013_auto_20260410_1837")]` and the three `AddField` operations
      verbatim from `data-model.md` § Migration `0014`. No `RunPython`, no backfill, no index (NFR-005).
      Depends on T004
- [X] T006 [P] Create the pure module `marketplace/wpp_templates/parameters.py` implementing the full API in
      `contracts/internal-python-api.md` § 1: the `TranslationParameters` frozen dataclass,
      `normalize_parameter_format`, `extract_named_placeholders`, `extract_positional_placeholders`,
      `detect_authoring_format`, `validate_parameter_name`, `build_named_example_payload` and
      `build_translation_parameters`. Constraints: **no Django import, no DRF import, no ORM access, no
      I/O, no logging of example values**; `PARAMETER_NAME_RE = r"^[a-z_][a-z0-9_]*$"` (the leading
      non-digit is required for Flows compatibility — do not loosen it); `NAMED_PLACEHOLDER_RE` admits
      uppercase so an invalid name is detected and reported rather than read as literal text;
      `build_translation_parameters` applies the recording rules table in `data-model.md` § Recording rules
      including all five anomaly types (`UNRECOGNISED_FORMAT`, `BODY_EXAMPLE_NAME_MISMATCH`,
      `MISSING_NAMED_EXAMPLE`, `DUPLICATE_BODY_PARAM_NAME`, `POSITIONAL_FORMAT_NAMED_BODY`), sets
      `variable_count` to `len(body_named_params)` for `NAMED` and literal `0` otherwise, ignores
      `header_text_named_params` entirely, and never infers a format from body text (FR-003)
- [X] T007 Create `marketplace/wpp_templates/tests/test_parameters.py` as a table-driven `SimpleTestCase`
      suite covering: format normalisation across `"named"` / `"NAMED"` / `"Named"` / `"positional"` /
      absent / unrecognised; body grammar for named, positional, mixed, duplicated, zero-placeholder and
      literal-brace bodies (`{ not a param }` and `{{ }}` produce no parameters); the naming rule accepting
      `item_2` and non-ASCII-free lowercase names and rejecting `Nome` and `2fa_code`; the FR-011
      body-vs-examples divergence storing the body's names with `null` for unsupplied examples and both
      sets retained in the anomaly; an empty or absent named example recording `MISSING_NAMED_EXAMPLE`
      with `example: null`; a Meta body that repeats a name recording `DUPLICATE_BODY_PARAM_NAME`
      without silently deduplicating; a positional (or omitted) format whose body contains named
      placeholders recording `POSITIONAL` with `POSITIONAL_FORMAT_NAMED_BODY`; `header_text_named_params`
      ignored entirely; and determinism (NFR-008) by asserting the same input twice. Depends
      on T006
- [X] T008 Extend `marketplace/wpp_templates/tests/test_models.py` with a `TemplateTranslation` defaults
      test asserting a freshly created row reads `parameter_format is None`, `body_named_params == []` and
      `parameter_anomaly is None`, plus a parity assertion that `models.PARAMETER_FORMAT_NAMED` /
      `PARAMETER_FORMAT_POSITIONAL` equal the constants in `parameters.py`, guarding the deliberate
      duplication from T004. Depends on T005 and T006
- [X] T009 ⚠️ CT#2 Scope the template Graph version without touching `BASE_URL`: in
      `marketplace/clients/facebook/client.py`, add a `template_api_url` property on
      `class TemplatesRequests` (line 233) that returns `settings.WHATSAPP_TEMPLATE_API_URL`, and switch
      every method in that class (`create_template_message`, `create_library_template_message`,
      `list_template_messages`, `update_template_message`, `delete_template_message`,
      `get_template_namespace`, `get_template_analytics`, `enable_template_insights`) from `self.get_url`
      to `self.template_api_url`. **Do not** assign `BASE_URL` on `TemplatesRequests` — `FacebookClient`
      mixins `CatalogsRequests` then `TemplatesRequests`, so a class-level `BASE_URL` would make every
      `FacebookClient(token)` call (catalogs, VTEX product batch, commerce, onboarding, photos) silently
      move to `v25.0` (FR-039, SC-009). Sibling classes and `FacebookAuthorization.BASE_URL` (line 26)
      stay untouched. Depends on T003
- [X] T010 Create `marketplace/wpp_templates/tests/test_template_api_version.py`. Mock `make_request` on a
      `FacebookClient` instance and assert `create_template_message` / `list_template_messages` URLs start
      with `settings.WHATSAPP_TEMPLATE_API_URL` while a catalog method URL starts with
      `settings.WHATSAPP_API_URL`. Assert `"BASE_URL" not in TemplatesRequests.__dict__`. Assert
      `CatalogsRequests`, `PhoneNumbersRequests`, `CloudProfileRequests`, `PhotoAPIRequests`,
      `CallingRequests`, `BusinessMetaRequests`, `BusinessVerificationRequests` and `FacebookClient`
      still resolve `BASE_URL` to `settings.WHATSAPP_API_URL` (SC-009). Do not restructure the client
      around `BASE_URL` to make a test pass. Depends on T009

**Checkpoint**: settings, schema and the recording grammar exist. User stories can now begin, in parallel
if staffed.

---

## Phase 3: User Story 1 — A named template synced from Meta stops being silently broken (Priority: P1) 🎯 MVP

**Goal**: the scheduled and on-demand sync record a named template's parameter format, its ordered
parameter names and its examples instead of a constant zero, and Meta's payload still reaches Flows
verbatim.

**Independent Test**: sync a WABA whose Meta response contains one named template (`parameter_format:
"named"`, body `Olá {{nome}}, sua cota {{cota}}`, `example.body_text_named_params` for both names) and one
positional template. Assert the named translation records `NAMED`, both names in body order with their
examples, and `variable_count == 2`; assert the positional translation is byte-identical to today's result;
assert the list passed to `PATCH /template/{flow_object_uuid}/` is the object received from Meta.

**Ships without Stories 2–6.**

- [X] T011 [US1] Make `extract_body_example` format-aware in
      `marketplace/wpp_templates/template_helpers.py`: add
      `NAMED_EXAMPLE_KEYS = frozenset({"body_text_named_params", "header_text_named_params"})`, change the
      loop from `.values()` to `.items()` purely so the key can be tested, and `continue` on a named key.
      Every other key — including the `else: body_example.append(values)` branch — keeps byte-identical
      handling. This is a denylist, **not** an allowlist of `body_text`: the authoring call site passes an
      author-supplied dict whose keys are not guaranteed, and an allowlist would silently change today's
      positional behaviour (FR-007, FR-041, SC-008)
- [X] T012 [P] [US1] Extend the `extract_body_example` test class in
      `marketplace/wpp_templates/tests/test_utils.py`: `body_text_named_params` and
      `header_text_named_params` are skipped rather than flattened into the `ArrayField(CharField)`; a
      payload carrying both `body_text` and `body_text_named_params` yields only the positional values; and
      every existing positional case still returns an identical list (regression assertion). Depends on
      T011
- [X] T013 [US1] Record the parameters in `TemplateSyncUseCase.sync_templates()` in
      `marketplace/wpp_templates/usecases/template_sync.py`: call
      `build_translation_parameters(template)` and assign `parameter_format`, `body_named_params`,
      `parameter_anomaly` and `variable_count` onto `returned_translation`, replacing the unconditional
      `returned_translation.variable_count = 0` at line 223 — see `contracts/internal-python-api.md` § 3
      for the exact assignment block. The existing `get_or_create` on `(template, language)` is unchanged
      so names are replaced in place with no duplicate rows (FR-012). Log every anomaly at `WARNING` with
      app UUID, project UUID, template name and `message_template_id` via `logging.getLogger(__name__)`
      and f-strings. **Drop or redact** the existing post-save `logger.info` at lines 226–229 that
      interpolates `body_example: {returned_translation.body_example}` — it already writes example values
      at INFO, and leaving it will fail T014 on the positional matrix row. Do not replace it with a log of
      `body_named_params`. Status and `message_template_id` may stay at INFO. **Never log example values at
      any level** (FR-043, FR-044, SC-011). The existing `body_example` *assignment* (line 220) is
      untouched; only that log is in scope
- [X] T014 [US1] Extend `marketplace/wpp_templates/usecases/tests/test_template_sync.py` with the recording
      matrix for Story 1 scenarios 1–9, mocking `TemplateService` and `FlowsClient` at the client boundary:
      named records `NAMED` + `["nome", "cota"]` in body order + both examples + `variable_count == 2` +
      `parameter_anomaly is None`; absent `parameter_format` records `POSITIONAL`; `"NAMED"` and `"named"`
      both record `NAMED`; an unrecognised value records `POSITIONAL` with an `UNRECOGNISED_FORMAT` anomaly
      and never inspects the body; a named body with zero placeholders records `NAMED`, `[]` and `0`;
      a body/examples divergence records the body's names with `null` for the unsupplied example and a
      `BODY_EXAMPLE_NAME_MISMATCH` anomaly retaining both sets; a named parameter with an empty example
      records `MISSING_NAMED_EXAMPLE` and stores `example: null`; a Meta body that repeats a name records
      `DUPLICATE_BODY_PARAM_NAME` without silently deduplicating; a positional or omitted format whose body
      contains named placeholders records `POSITIONAL` with `POSITIONAL_FORMAT_NAMED_BODY` and never
      infers named from the body; changed names at Meta are replaced in place
      with no new `TemplateMessage` or `TemplateTranslation` row; one Meta response applied to several apps
      sharing a WABA records the same values per app with the per-WABA TTL lock and drain budget unchanged;
      and the positional translation is byte-identical to today including `variable_count == 0` and its
      `body_example`. Assert no example value appears in any `INFO` record — including the positional
      row's `body_example` strings and the named row's example strings — so the pre-existing post-save
      log at `template_sync.py:226-229` cannot be left in place (FR-044, SC-011). Depends on T013
- [X] T015 [US1] Add the FR-013 bulk-push regression test to
      `marketplace/wpp_templates/usecases/tests/test_template_sync.py`, asserting **identity** —
      `self.assertIs(flows_client.update_facebook_templates.call_args.args[1], meta_templates)` — so a
      later defensive `copy()` or comprehension cannot be introduced silently. `FlowsClient` and
      `update_facebook_templates` are **not** modified; this task is a test only. Depends on T013
- [X] T016 [P] [US1] Ensure the library creation path leaves the format unknown in
      `marketplace/wpp_templates/usecases/template_library_creation.py::_save_template_in_db` (line 256):
      the translation dict keeps `"variable_count": 0` (line 298) and must **not** set
      `parameter_format`, so the column stays `NULL`. Meta's creation response carries only `id`, `status`
      and `category`, and the request carries `library_template_name` rather than body text, so no format
      can be derived here (FR-014, FR-015, SC-012). The existing post-creation `sync_pending_templates`
      task resolves it; no new polling is added
- [X] T017 [P] [US1] Extend
      `marketplace/wpp_templates/usecases/tests/test_template_library_creation.py` asserting a
      library-created translation has `parameter_format is None`, `body_named_params == []` and
      `variable_count == 0`, and that a subsequent `TemplateSyncUseCase` run over a Meta response declaring
      the template named resolves it to `NAMED` with its names (SC-012). Depends on T016

**Checkpoint**: Story 1 is fully functional and independently testable. The mirror and the Flows bulk push
are correct for every template Meta describes. This is the MVP and it is shippable on its own.

---

## Phase 4: User Story 2 — The format and the names survive every update path (Priority: P1)

**Goal**: the payload rebuilt from the local mirror for the Flows single-template sync endpoint carries the
parameter format and the named examples, every webhook event preserves the recorded values, and an edit
re-derives the names from the submitted body.

**Independent Test**: take a translation recorded as named with two names and examples. Fire
`message_template_status_update` and `template_category_update`; after each, assert the local format and
names are unchanged and that the `template_data` posted to `POST /template/{flow_object_uuid}/template-sync/`
contains the parameter format and the named examples. Fire `template_correct_category_detection`; assert
the local values are unchanged and that Flows is **not** called. Gallery re-sync (scenario 5) is **not**
part of this Independent Test — it depends on T013.

**Severity note**: verified against Flows PR #876, `_handle_template_sync` only applies the status/category
event for a template Flows already has and never re-reads `template_data`, so nothing is cleared. The change
still matters for the **first** webhook on a template Flows has not yet seen. Same work, lower severity than
`spec.md` implies.

- [X] T018 [US2] Carry the format and the named examples in
      `marketplace/wpp_templates/utils.py::extract_template_data` (line 305): emit
      `parameter_format` at the payload root for `NAMED` and `POSITIONAL`, **omit the key entirely** when
      `translation.parameter_format` is `NULL` (emitting `null` would invite a consumer to record it as a
      format); attach `body_component["example"] = {"body_text_named_params":
      translation.body_named_params}` with **zero transformation** when `body_named_params` is non-empty
      **and** `parameter_anomaly is None`; attach **no** example block for an anomalous translation, so
      Flows falls back to body names instead of unioning both sets (FR-011, FR-017). The pre-existing drop
      of the positional `example.body_text` is **deliberately left in place** — Flows has no field for it
      and never reads it (`plan.md` § 9). `FlowsClient.update_facebook_templates_webhook` and
      `FlowsService` are unchanged
- [X] T019 [US2] ⚠️ CT#3 Widen the webhook app lookup in
      `marketplace/wpp_templates/utils.py::TemplateWebhookEventProcessor.get_apps_by_waba_id` (line 183)
      from `App.objects.filter(config__wa_waba_id=waba_id)` to
      `App.objects.filter(Q(config__wa_waba_id=waba_id) | Q(config__waba__id=waba_id))`, so `wpp`
      on-premises apps — which store their WABA at the nested path and are synced — stop being invisible to
      every webhook event. **Do not** extract a shared helper with `tasks.py::_apps_for_waba` (line 36):
      that function additionally filters by `code` and `ignores_meta_sync`, and a webhook must not be
      dropped because scheduled sync was disabled (Constitution III). Depends on T018 (same file)
- [X] T020 [P] [US2] Add `extract_template_data` tests to
      `marketplace/wpp_templates/tests/test_utils.py`: a clean named translation emits
      `"parameter_format": "NAMED"` and a BODY `example.body_text_named_params` matching
      `body_named_params` exactly; an anomalous named translation emits the format but **no** example
      block; a positional translation gains only `parameter_format: "POSITIONAL"` with the BODY component
      otherwise unchanged and `example.body_text` still absent; a `NULL`-format translation omits the key;
      and `name`, `language`, `status`, `category` and `id` are unchanged. Depends on T018
- [X] T021 [US2] Add webhook-preservation tests across
      `marketplace/wpp_templates/tests/test_utils.py` and
      `marketplace/wpp_templates/tests/test_template_status_update_handler.py`: for
      `message_template_status_update` and `template_category_update`, assert the locally recorded
      `parameter_format`, `body_named_params` and `parameter_anomaly` are byte-identical before and after
      and that the captured `template_data` carries the format (SC-002); for
      `template_correct_category_detection`, assert the local values are unchanged and that Flows is **not**
      called (that event is proxied to Commerce only); assert the gallery-template path that triggers a
      full re-sync instead of posting to Flows also preserves them (Story 2 scenario 5) — this case
      **Depends on T013**; and assert an app configured only at `config.waba.id` now receives the event
      while an app at `config.wa_waba_id` still does. Depends on T019, T020 and T013
- [X] T022 [US2] ⚠️ CT#1 Re-derive the stored names on the edit path in
      `marketplace/wpp_templates/views.py::partial_update` (line 166), where `translation.body =
      body.get("text")` is assigned before `translation.save()` (lines 237–246): when the submitted body is
      named, recompute `body_named_params` and `variable_count` from it using `parameters.py` and clear a
      stale `parameter_anomaly`; leave `parameter_format` untouched — the format is Meta's and this path
      must never try to change it. `update_template_message` (line 275) keeps its existing signature and
      never receives a `parameter_format` (FR-019). Fold in the removal of the dead
      `WHATSAPP_VERSION = settings.WHATSAPP_VERSION` assignment at `marketplace/wpp_templates/views.py:42`,
      which is assigned and never read. **Constitution note**: `partial_update` performs ORM writes,
      base64 media upload and a Meta call directly in the view, violating Constitution I. That violation is
      pre-existing and is recorded under `plan.md` § Complexity Tracking #1 alongside
      `TemplateTranslationSerializer.create()`. Do **not** extract a use case inside this task — that
      would rewrite the highest-traffic write path and directly endangers SC-008. Mitigation: no new
      business logic enters the view; re-derivation delegates to `parameters.py`
- [X] T023 [P] [US2] Add edit-path tests to `marketplace/wpp_templates/tests/test_views.py`: editing a named
      template's body to a different name set replaces `body_named_params` and `variable_count` in place;
      `parameter_format` is unchanged; the `update_template_message` call kwargs contain no
      `parameter_format` key; and editing a positional template's body behaves exactly as today
      (Story 2 scenario 6). Depends on T022

**Checkpoint**: Stories 1 and 2 both work independently. A routine webhook can no longer degrade a named
template, and on-premises apps receive webhook events.

---

## Phase 5: User Story 3 — Authoring a named template in Weni actually reaches Meta as named (Priority: P1)

**Goal**: the authoring path detects the format from the body, validates names and examples before
submission, submits the named format with one example per name, and rejects invalid bodies with field-level
errors before any Meta call.

**Independent Test**: submit a translation whose body is `Olá {{nome}}, sua cota {{cota}} vence em {{data}}`
with an example per name; assert the Meta payload declares `parameter_format: "named"` and carries three
`body_text_named_params` entries. Then submit a mixed body, a duplicated name, a name breaking the rule and
a body with a missing example; assert each is rejected with a field-level error naming the offending
parameter, that `create_template_message` was not called, and that zero rows were created.

- [X] T024 [P] [US3] Add the trailing `parameter_format: Optional[str] = None` to
      `TemplatesRequestsInterface.create_template_message` in
      `marketplace/interfaces/facebook/interfaces.py` (line 31), matching
      `contracts/internal-python-api.md` § 2 exactly. `update_template_message` and
      `create_library_template_message` are unchanged
- [X] T025 [P] [US3] Add the same trailing `parameter_format=None` to
      `TemplateService.create_template_message` in `marketplace/services/facebook/service.py` (line 161)
      and forward it to the client as a keyword argument
- [X] T026 [US3] Add the same trailing `parameter_format=None` to
      `TemplatesRequests.create_template_message` in `marketplace/clients/facebook/client.py` (line 236)
      and include the key in the payload **only when it is not `None`**, so a positional create stays
      byte-identical to today's request (FR-026, SC-008). Depends on T009 (same file)
- [X] T027 [P] [US3] Update the fake `create_template_message(self, waba_id, name, category, components,
      language)` test double at `marketplace/services/facebook/tests/test_services.py:73` to accept the new
      trailing parameter, and assert the service forwards it unchanged. This is the one legitimate
      modification to an existing test caused by the signature change
- [X] T028 [US3] ⚠️ CT#1 Add named-body validation to `TemplateTranslationSerializer` in
      `marketplace/wpp_templates/serializers.py` (class at line 60), delegating **all** grammar and rule
      logic to `parameters.py` so no new business logic enters the serializer: detect the format with
      `detect_authoring_format`; reject a mixed body with a field-level error stating that a template uses
      one parameter format and identifying the minority-format variables (FR-022); reject a duplicated name
      by naming it (FR-023); reject a name failing `^[a-z_][a-z0-9_]*$` by stating the rule, including the
      leading-digit case (FR-024); reject a named parameter with no example by identifying that parameter
      (FR-025); and, when `settings.WHATSAPP_NAMED_TEMPLATES_ENABLED` is `False` and the body is named,
      reject with a field-level error stating that named templates are not enabled — **never** a silent
      downgrade to positional (FR-027). Every rejection produces zero local records and zero Meta calls.
      Error messages name the field, the offending parameter and the condition (NFR-006); example values
      may appear in errors returned to the author but never in `INFO` logs (FR-044). Fold in the removal of
      the dead `WHATSAPP_VERSION = settings.WHATSAPP_VERSION` assignment at line 26
- [X] T029 [US3] Build and submit the named payload in
      `marketplace/wpp_templates/serializers.py`: at the `create_template_message` call site (line 168),
      pass `parameter_format="named"` (lowercase, matching Meta's creation documentation) for a named body
      and **omit the argument entirely** for a positional body; assemble the BODY component's
      `example.body_text_named_params` with `build_named_example_payload` in body order; and record the
      created translation with `parameter_format = "NAMED"`, `body_named_params` and `variable_count =
      len(names)`. A positional create keeps the literal `variable_count=0` at line 189 and its existing
      `body_example` handling unchanged (FR-026). Depends on T025, T026 and T028
- [X] T030 [US3] Surface Meta's rejection correctly in `marketplace/wpp_templates/serializers.py`,
      reusing `marketplace/wpp_templates/error_handlers.py` where it already applies: a `400` naming a body
      or parameter problem is surfaced **verbatim, not reinterpreted**, with no local record (FR-024, Story
      3 scenario 7); a `400` indicating `parameter_format` is unsupported is re-raised as a **configuration**
      error naming the unsupported capability rather than a template validation error (Edge Cases —
      Provider version). Depends on T029
- [X] T031 [P] [US3] Add the accept-path tests to `marketplace/wpp_templates/tests/test_serializers.py`
      with `TemplateService` mocked and `override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=True)`: a
      three-parameter named body calls `create_template_message` with `parameter_format="named"` and a BODY
      component carrying three `{param_name, example}` entries in body order, and records the translation
      as `NAMED` with `variable_count == 3` and `body_named_params` populated. Depends on T029
- [X] T032 [US3] Add the reject matrix to `marketplace/wpp_templates/tests/test_serializers.py`, one case
      per row of `quickstart.md` § Scenario 3 — `Olá {{nome}}, pedido {{1}}`,
      `Olá {{nome}}, tudo bem {{nome}}?`, `Olá {{Nome}}`, `Seu código {{2fa_code}}`, `Olá {{nome}}` with no
      example, and a body valid locally that Meta rejects. Each asserts a field-level error naming the
      offending parameter, `create_template_message.assert_not_called()` where applicable, and zero new
      `TemplateTranslation` rows (SC-004). Include the unsupported-`parameter_format` Meta error asserting
      a configuration-flavoured message. Depends on T030 and T031
- [X] T033 [US3] Add the flag and positional-parity tests to
      `marketplace/wpp_templates/tests/test_serializers.py`: with
      `override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=False)` a named body is rejected with a
      field-level error and makes no Meta call, while a positional body is unaffected; with the flag `True`
      the named body is permitted; and in both states a positional submission's `create_template_message`
      call kwargs contain **no** `parameter_format` key (SC-008). Depends on T032

**Checkpoint**: Stories 1–3 all work independently. Authoring a named template now reaches Meta correctly,
and the path is closed by default until downstream ships.

---

## Phase 6: User Story 4 — The existing fleet is classified and the broken templates are counted (Priority: P2)

**Goal**: an operator-triggered command classifies every already-recorded template against Meta, corrects
the format and names, and reports the fleet broken by the pre-existing defect.

**Independent Test**: seed translations recorded with a named body and `variable_count = 0` alongside
correctly recorded positional ones. Run reconciliation against a stubbed Meta response with an injected fake
Redis. Assert every template's format is set, named ones gain names and examples, the previously broken ones
appear in the report, no duplicate template or translation is created, and a second run produces an
identical result and an identical artifact.

**Depends on Story 1** only because it applies Meta's list through `TemplateSyncUseCase.sync_templates()` —
the recording behaviour it converges to is T013's.

- [ ] T034 [P] [US4] Create the management package scaffolding
      `marketplace/wpp_templates/management/__init__.py` and
      `marketplace/wpp_templates/management/commands/__init__.py`, following the repository's one precedent
      at `marketplace/event_driven/management/commands/edaconsume.py`
- [ ] T035 [US4] Create `marketplace/wpp_templates/usecases/template_parameter_reconciliation.py` with
      `TemplateParameterReconciliationUseCase` and the frozen `ReconciliationResult` dataclass exactly as
      specified in `contracts/internal-python-api.md` § 5: constructor injection for `redis_conn`,
      `sync_use_case_factory`, `apps_for_waba`, `sleep` and `logger`, each defaulting to the concrete
      collaborator; `execute(waba_ids=None, app_uuids=None, dry_run=False, restart=False, limit=None)`;
      and `ReconciliationResult(run_id, rows, counters, resumed)` with `to_dict()`. The use case is
      framework-agnostic — **no `rest_framework` import** (Constitution I, IV)
- [ ] T036 [US4] ⚠️ CT#4 Implement the execution loop in
      `marketplace/wpp_templates/usecases/template_parameter_reconciliation.py`: resolve target WABAs
      through `tasks.py::_apps_for_waba`, honouring `--waba-id` / `--app-uuid` / `--limit`; skip a WABA
      whose per-WABA TTL lock is held by a recent scheduled sync and record a **WABA-level**
      `skipped_recent_sync` (run counter + log line, **not** a sixth translation category, not marked
      done, no translation CSV rows), reusing the **same** `TTL_WHATSAPP_TEMPLATES` key namespace and
      `core/pacing/ttl.py`'s `is_recently_synced` /
      `mark_synced`; and pace between WABAs by `60 / budget` seconds where `budget` defaults to
      `settings.META_SYNC_TEMPLATES_DRAIN_BUDGET`, through the injected `sleep`. The run is **synchronous**
      by design — the existing drain hardcodes `task_sync_whatsapp_templates_item` and an async run could
      not produce FR-033's single artifact. A WABA whose Meta call fails, whose token is invalid or which no
      longer exists yields `unclassifiable` rows with the reason and the run continues. Depends on T035
- [ ] T037 [US4] Implement snapshot, apply and classification in
      `marketplace/wpp_templates/usecases/template_parameter_reconciliation.py`: capture the pre-state
      `(body, parameter_format, body_named_params, variable_count)` for every translation of every app on
      the WABA; apply Meta's list through `TemplateSyncUseCase(app).sync_templates(templates=...)` — skipped
      under `--dry-run` — so convergence, in-place name replacement and the absence of duplicate rows are
      structural rather than reimplemented (FR-031); then classify each translation into exactly one of
      `corrected`, `unchanged`, `anomalous`, `format_not_yet_known` and `unclassifiable` per
      `contracts/reconciliation-cli.md` § Classification, with `previously_broken` as a **separate boolean**
      set when the pre-state body contained named placeholders and the row had no recorded parameters. Apps
      excluded by `ignores_meta_sync` are `unclassifiable` with reason `sync_disabled` and are never counted
      as classified; `format_not_yet_known` and `unclassifiable` count as neither classified nor broken
      (FR-015, FR-034). Depends on T036
- [ ] T038 [US4] Implement Redis progress and resumption in
      `marketplace/wpp_templates/usecases/template_parameter_reconciliation.py`: write the JSON document in
      `contracts/reconciliation-cli.md` § Progress (`run_id`, `started_at`, `done_waba_ids`, `counters`,
      `rows_written`) to `template_param_reconcile:progress` with `ex=60*60*24`, mirroring the
      `template_status:{app_uuid}` pattern; resume by skipping `done_waba_ids` unless `restart=True`, which
      deletes the key and starts a new `run_id`. All access goes through the injected `redis_conn`.
      Depends on T037
- [ ] T039 [US4] Implement the CSV artifact and structured logging in
      `marketplace/wpp_templates/usecases/template_parameter_reconciliation.py`: write the fixed column set
      from `contracts/reconciliation-cli.md` § Report artifact, one row per translation, appended **per
      WABA** rather than buffered, so an interrupted run leaves a usable partial report; name lists are
      semicolon-delimited; **no example value appears in the artifact or in any log record** (FR-044,
      SC-011). Emit the log points from § Logging at their specified levels, each attributable to project,
      app and template (FR-043). Depends on T038
- [ ] T040 [US4] Create the operator entry point
      `marketplace/wpp_templates/management/commands/reconcile_template_parameters.py` as a thin
      `BaseCommand` that parses `--waba-id` (repeatable), `--app-uuid` (repeatable), `--limit`,
      `--dry-run`, `--restart`, `--output` and `--budget` per `contracts/reconciliation-cli.md` §
      Invocation, delegates to the use case, and exits `0` on a completed run — a non-zero unclassifiable
      count is a finding, not a failure — or `1` when the run cannot start or the artifact cannot be
      written. No new model, endpoint or permission (FR-030). Depends on T034 and T039
- [ ] T041 [US4] Create
      `marketplace/wpp_templates/usecases/tests/test_template_parameter_reconciliation.py` with an injected
      fake Redis, `TemplateService` mocked at the client boundary and `sleep` injected so no test waits:
      one fixture per category asserting the five are never conflated; a named-body / `variable_count = 0`
      translation asserted both `previously_broken` **and** `corrected`; resumption by truncating progress
      mid-way and asserting processed WABAs are skipped on re-run; idempotency by running twice against the
      same stubbed response and asserting **byte-identical** artifacts (SC-005); an `ignores_meta_sync` app
      asserted `unclassifiable` with reason `sync_disabled` and not counted as classified; a WABA whose Meta
      call fails asserted `unclassifiable` with the run continuing; `--dry-run` asserted to classify without
      writing to the mirror; a WABA whose TTL lock is held asserted `skipped_recent_sync`, **not** in
      `done_waba_ids`, with no mirror write, no translation CSV rows, and not counted as classified,
      broken or unclassifiable; injected `sleep` asserted called with `60 / budget` seconds; template and
      translation counts asserted unchanged (no duplicates); and no
      example value present in the artifact or the captured logs. **No test reaches real Redis or a provider
      API.** Depends on T039
- [ ] T042 [US4] Create
      `marketplace/wpp_templates/tests/test_reconcile_template_parameters_command.py` exercising the
      command through `call_command` with the use case patched: argument parsing for every option including
      repeatable `--waba-id`, the artifact written to `--output`, exit code `0` on completion with a
      non-zero unclassifiable count, and exit code `1` on an unwritable output path. Depends on T040

**Checkpoint**: Stories 1–4 all work independently. The broken-template count is measurable.

---

## Phase 7: User Story 5 — The read surfaces publish the format and the names (Priority: P2)

**Goal**: the template list and template detail publish each translation's parameter format and parameter
names, plus a derived template-level format that reports `"MIXED"` on disagreement.

**Independent Test**: read a named template and a positional template through
`GET /api/v1/apps/{app_uuid}/templates/` and `/{uuid}/`. Assert the named one reports `NAMED` with its
parameter names, the positional one reports `POSITIONAL` and keeps `variable_count`, and no positional index
appears beside a named parameter in either response.

**Depends on Story 1** only for data to read.

- [ ] T043 [US5] Add the three read-only fields to `TemplateTranslationSerializer` in
      `marketplace/wpp_templates/serializers.py` (class at line 60): `parameter_format` (the recorded
      value — `"NAMED"`, `"POSITIONAL"` or `null`), `parameter_names` (a `SerializerMethodField` returning
      the ordered `param_name` values as **bare strings**, `[]` for positional and not-yet-known), and
      `has_parameter_anomaly` (a boolean derived from `parameter_anomaly is not None`). All three are
      read-only and never accepted as input. Example values and the anomaly evidence object are **not**
      published. `variable_count` and `body_example` keep their existing names, types and meanings
      (FR-035, FR-036, FR-037)
- [ ] T044 [US5] Add the derived template-level `parameter_format` to `TemplateMessageSerializer` in
      `marketplace/wpp_templates/serializers.py` (class at line 206) as a `SerializerMethodField`: `null`
      when there are no translations or every translation's format is `NULL`; the agreed value when all
      translations with a known format agree; `"MIXED"` when they disagree. Translations whose format is
      `NULL` are excluded from the agreement test rather than forcing `"MIXED"`. `"MIXED"` is derived on
      read only — never stored, never sent to Meta, never accepted as input (FR-008). Depends on T043
- [ ] T045 [US5] Extend `marketplace/wpp_templates/tests/test_views.py` (using `APIBaseTestCase`) with the
      read-surface matrix from `contracts/read-surfaces.md` § Format matrix across both the list and the
      detail endpoint: named clean, named with zero placeholders, named anomalous, positional, positional
      with a named body, not-yet-known and legacy rows; a template whose translations disagree reading
      `"MIXED"` at template level with per-translation values still visible; the recursive
      `assert_no_positional_keys` scan proving no `index`, `position`, `slot` or `order` key appears at any
      depth (SC-006); and tenancy unchanged — only templates for apps the caller's project is authorised
      for, behind `ProjectManagePermission` (Story 5 scenario 5). Depends on T044

**Checkpoint**: Stories 1–5 all work independently. An integrator can determine a template's format and
parameter names from the API alone.

---

## Phase 8: User Story 6 — Positional templates and existing integrations are untouched (Priority: P3)

**Goal**: prove that positional behaviour has not changed anywhere, and that the two formats coexist in one
app without interfering.

**Independent Test**: run the existing template sync, serializer, view and webhook suites unchanged and
confirm identical behaviour. Then sync an account containing both formats and confirm each is recorded in
its own format with neither affecting the other.

- [ ] T046 [US6] Run the existing suites unmodified — `poetry run python manage.py test
      marketplace.wpp_templates` plus `marketplace.services.facebook` — and record, in the pull request
      description, the complete inventory of test modifications. Only two categories are legitimate: a test
      asserting the absence of the new fields, and the `create_template_message` test double at
      `marketplace/services/facebook/tests/test_services.py:73` (T027). Any third modification is a
      behaviour change and must be justified or reverted (SC-008)
- [ ] T047 [P] [US6] Add a coexistence test to
      `marketplace/wpp_templates/usecases/tests/test_template_sync.py`: one Meta response containing both a
      named and a positional template for the same app records each in its own format, with the positional
      row's `parameter_format`, `body_named_params`, `variable_count` and `body_example` unaffected by the
      named row and vice versa (Story 6 scenario 2). Depends on T013
- [ ] T048 [US6] Add the positional-parity and NFR-001 assertions in
      `marketplace/wpp_templates/tests/test_serializers.py` and
      `marketplace/wpp_templates/usecases/tests/test_template_sync.py`: a positional create's outbound
      payload is byte-identical to today's, carrying no `parameter_format` key; and syncing an account of
      positional templates issues exactly the same number of `TemplateService` calls as before — the new
      recording reads only the list response already in hand, with no additional Meta request per template
      (NFR-001, NFR-003). Depends on T029 and T013
- [ ] T049 [US6] Add the SC-006 sweep: assert no positional index, slot or ordinal is computed, stored,
      published or transmitted for a named parameter — in the mirror (`body_named_params` entries carry only
      `param_name` and `example`), in the read surfaces (covered by T045), and in **both** Flows payloads —
      the bulk push forwards Meta verbatim (covered by T015) and the webhook payload emits
      `body_text_named_params` untransformed (asserted in
      `marketplace/wpp_templates/tests/test_utils.py`). Depends on T015, T020 and T045

**Checkpoint**: all six stories complete and independently verified.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T050 Perform the SC-009 endpoint-by-endpoint pre-release check by walking the version map table in
      `specs/001-named-template-parameters/contracts/meta-graph-templates.md` § Endpoint-by-endpoint version
      map: confirm `TemplatesRequests` calls `v25.0` and that catalogs, product batch upload, commerce
      settings, phone numbers, business profile, OAuth, credit sharing, onboarding and the on-premises WABA
      surfaces in `marketplace/core/types/channels/whatsapp/apis.py` and
      `whatsapp_base/requests/facebook.py` all still call their current version. Record the result in the
      pull request description. The automated half is T010; this is the manual half the requirement asks for
- [ ] T051 Run every scenario in `specs/001-named-template-parameters/quickstart.md` — migration timing,
      Scenarios 1–7 and the rollout preconditions — and confirm
      `poetry run python manage.py makemigrations --check --dry-run` reports no changes
- [ ] T052 Run the full quality gate: `poetry run python contrib/code_check.py` (makemigrations + `flake8
      marketplace/` at 119 columns + `coverage run manage.py test` + `coverage report -m`), plus
      `poetry run black --check marketplace/` — which `code_check.py` does not run but pre-commit and CI
      do — and `poetry run python contrib/compare_coverage.py`. Coverage must stay at or above the 75%
      floor (NFR-009). Depends on every preceding task

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies — can start immediately
- **Foundational (Phase 2)**: independent of Setup in practice, but **blocks every user story**
- **User Stories (Phases 3–8)**: all depend on Phase 2. Story 1 depends on nothing else. Stories 4, 5 and 6
  depend on Story 1 for the data they reconcile, read and regression-check. Story 2's Independent Test
  (status + category-update `template_data`, correct-category local preservation) is independent of Story 1;
  T021's gallery re-sync case depends on T013. Story 3 is independent of Story 1 and of Story 2
- **Polish (Phase 9)**: depends on all desired stories being complete

### User story dependencies

| Story | Priority | Depends on | Independently shippable |
| --- | --- | --- | --- |
| US1 — sync recording | P1 | Phase 2 | **Yes** — this is the MVP |
| US2 — update paths | P1 | Phase 2; T021 gallery case → T013 | Yes for the Independent Test; gallery re-sync (AS-5) after US1 |
| US3 — authoring | P1 | Phase 2 | Yes |
| US4 — reconciliation | P2 | Phase 2, US1 (applies Meta's list through `TemplateSyncUseCase`) | Yes, after US1 |
| US5 — read surfaces | P2 | Phase 2, US1 (needs recorded data to publish) | Yes, after US1 |
| US6 — regression verification | P3 | Phase 2, US1 (and whichever of US2–US5 shipped) | Yes, scoped to what shipped |

### Critical path

`T003/T004 → T005 → T006 → T013 → T014` is the shortest route to the MVP. `T009 → T010` runs alongside it.

### Cross-file contention (why some tasks are not `[P]`)

| File | Tasks |
| --- | --- |
| `marketplace/clients/facebook/client.py` | T009 (foundational), T026 (US3) |
| `marketplace/wpp_templates/serializers.py` | T028, T029, T030 (US3); T043, T044 (US5) |
| `marketplace/wpp_templates/utils.py` | T018, T019 (US2) |
| `marketplace/wpp_templates/tests/test_utils.py` | T012 (US1), T020, T021 (US2) |
| `marketplace/wpp_templates/usecases/tests/test_template_sync.py` | T014, T015 (US1), T047, T048 (US6) |
| `marketplace/wpp_templates/tests/test_serializers.py` | T031, T032, T033 (US3), T048 (US6) |
| `marketplace/wpp_templates/usecases/template_parameter_reconciliation.py` | T035–T039 (US4) |

### Within each user story

- Behaviour task before its paired test task; both ship in the same pull request (Constitution VIII)
- Pure module before its callers; model before migration; client before the version test
- Story complete and its Independent Test green before moving to the next priority

---

## Parallel Opportunities

### Phase 1 + Phase 2 — the widest parallel window

`T001`, `T002`, `T003`, `T004` and `T006` have no dependency on one another and touch five different files.
The pure module, the schema and the settings change can be written simultaneously:

```bash
Task: "Add env entries in contrib/gen_env.py"                          # T001
Task: "Remove stale .coveragerc entry"                                 # T002
Task: "Add the three settings in marketplace/settings.py"              # T003
Task: "Add the three columns in marketplace/wpp_templates/models.py"   # T004
Task: "Create the pure module marketplace/wpp_templates/parameters.py" # T006
```

### Once Phase 2 completes

Stories 1, 2 and 3 can be developed by three people in parallel — they share only
`marketplace/wpp_templates/serializers.py` between US3 and US5, and US5 comes later.

### Within User Story 1

```bash
Task: "extract_body_example tests in tests/test_utils.py"                            # T012
Task: "Library creation leaves NULL in usecases/template_library_creation.py"        # T016
Task: "Library tests in usecases/tests/test_template_library_creation.py"            # T017
```

### Within User Story 3

```bash
Task: "Interface signature in marketplace/interfaces/facebook/interfaces.py"   # T024
Task: "Service signature in marketplace/services/facebook/service.py"          # T025
Task: "Test double in marketplace/services/facebook/tests/test_services.py"    # T027
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Complete Phase 1 (Setup) — T001–T002
2. Complete Phase 2 (Foundational) — T003–T010. **Blocks everything**
3. Complete Phase 3 (User Story 1) — T011–T017
4. **STOP and VALIDATE**: run Story 1's Independent Test and `quickstart.md` Scenario 1
5. Deploy. `WHATSAPP_NAMED_TEMPLATES_ENABLED` is `False`, so nothing new becomes creatable — the mirror and
   the Flows bulk push simply stop being wrong for templates authored in Meta's panel

### Incremental delivery

1. Setup + Foundational → foundation ready
2. **US1** → the active production defect is fixed → deploy (MVP)
3. **US2** → webhook paths stop degrading what US1 recorded → deploy
4. **US3** → named authoring works, still closed by the default-off flag → deploy
5. **US4** → run the bounded `--limit --dry-run` probe, then the fleet; the broken-template count becomes a
   number (SC-010)
6. **US5** → the template list can show the format without opening a template
7. **US6 + Polish** → regression evidence, the SC-009 walk, and the quality gate
8. **After Flows, mailroom, goflow and courier ship** → flip `WHATSAPP_NAMED_TEMPLATES_ENABLED` to `True`
   (product spec BD-016)

### Parallel team strategy

With three developers, after Phase 2: Developer A takes US1 then US4; Developer B takes US2 then US5;
Developer C takes US3 then US6. The only shared file across those pairings is
`marketplace/wpp_templates/serializers.py` (US3 and US5), which the sequencing keeps apart.

---

## Constitution Notes

Four tasks implement deviations already justified in `plan.md` § Complexity Tracking and are marked
`⚠️ CT#n` above: T003 and T009 (CT#2, the second Graph version setting, scoped via `template_api_url`
not `BASE_URL`), T019 (CT#3, the widened webhook lookup), T028 and T022 (CT#1, extending the
layer-violating authoring serializer and edit view) and T036 (CT#4, synchronous reconciliation).

---

## Notes

- `[P]` tasks touch different files and have no dependency on an incomplete task
- `[Story]` labels map each task to a user story for traceability
- Every user story is independently completable, independently testable and independently deployable
- Commit after each task or logical group; stop at any checkpoint to validate a story on its own
- **No test may reach real Redis, RabbitMQ, S3, OIDC or a provider API.** Meta and Flows are mocked at
  `TemplateService` / `FlowsClient`, Redis is injected as a fake, and `CACHES` is overridden to
  `LocMemCache` wherever the Django cache is touched (Constitution VIII)
- `marketplace/clients/*`, `marketplace/interfaces/*`, `*migrations/*`, `*urls.py*` and
  `marketplace/settings.py` are omitted by `.coveragerc`, so T003, T005, T009, T024 and T026 carry no
  coverage cost
- Nothing in the spec's **Out of Scope** section has a task, and no task re-opens a decision settled in
  `research.md`
