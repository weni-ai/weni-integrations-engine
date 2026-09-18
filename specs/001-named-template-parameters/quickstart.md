# Quickstart — Validating Named Template Parameters

**Feature**: `001-named-template-parameters`

Runnable scenarios that prove the feature works end to end. Each maps to a user story and its success
criteria. This is a validation guide — implementation detail lives in
[`data-model.md`](./data-model.md) and [`contracts/`](./contracts).

---

## Prerequisites

```bash
poetry install
```

Environment additions for this feature (`.env`):

```bash
WHATSAPP_TEMPLATE_VERSION=v25.0
WHATSAPP_NAMED_TEMPLATES_ENABLED=False   # True only after Flows/mailroom/goflow/courier ship
```

Apply the schema change:

```bash
poetry run python manage.py migrate wpp_templates
poetry run python manage.py makemigrations --check --dry-run   # must report no changes
```

Expected: `0014_templatetranslation_parameters` applies in well under a second. It adds three columns with
no backfill and no index, so there is no table rewrite (NFR-005).

---

## Running the suite

```bash
poetry run python manage.py test marketplace.wpp_templates --verbosity=2
poetry run coverage run manage.py test && poetry run coverage report -m
poetry run python contrib/code_check.py          # migrations + flake8 + tests + coverage
```

Gates: coverage at or above **75%**, `flake8` clean at 119 columns, `black --check` clean, `makemigrations`
reporting no changes.

No test may reach real Redis, RabbitMQ, S3, OIDC or a provider API. Meta and Flows are mocked at
`TemplateService` / `FlowsClient`; Redis is injected as a fake.

---

## Scenario 1 — A named template syncs correctly (Story 1, SC-001)

**Setup**: a `wpp-cloud` app whose stubbed Meta list response contains one named and one positional
template.

```python
META_RESPONSE = {"data": [
    {"id": "1001", "name": "cota_aviso", "language": "pt_BR", "status": "APPROVED",
     "category": "UTILITY", "parameter_format": "NAMED",
     "components": [{"type": "BODY", "text": "Olá {{nome}}, sua cota {{cota}} vence hoje",
                     "example": {"body_text_named_params": [
                         {"param_name": "nome", "example": "João"},
                         {"param_name": "cota", "example": "3/12"}]}}]},
    {"id": "1002", "name": "pedido_enviado", "language": "pt_BR", "status": "APPROVED",
     "category": "UTILITY",
     "components": [{"type": "BODY", "text": "Olá {{1}}, seu pedido {{2}} foi enviado.",
                     "example": {"body_text": [["João", "12345"]]}}]},
]}
```

**Run**: `TemplateSyncUseCase(app).sync_templates(templates=META_RESPONSE["data"])`

**Assert**:

| Check | Expected |
| --- | --- |
| Named translation format | `"NAMED"` |
| Named translation names | `["nome", "cota"]` — body order |
| Named translation examples | `"João"`, `"3/12"` |
| Named `variable_count` | `2`, never `0` |
| Named `parameter_anomaly` | `None` |
| Positional translation | `parameter_format="POSITIONAL"`, `body_named_params=[]`, `variable_count=0`, `body_example=["João", "12345"]` — **identical to today** |
| Flows bulk push | `update_facebook_templates` received the Meta list **by identity**, including `parameter_format` |

```bash
poetry run python manage.py test marketplace.wpp_templates.usecases.tests.test_template_sync
```

### Provider-data variants (Story 1 scenarios 2–7)

| Input | Expected |
| --- | --- |
| `parameter_format` key absent | `"POSITIONAL"` — Meta's documented default |
| `"named"` lowercase | `"NAMED"` — case-insensitive |
| `"SOMETHING_ELSE"` | `"POSITIONAL"` + `UNRECOGNISED_FORMAT` anomaly, logged; format **never** inferred from the body |
| Named, body has zero placeholders | Valid: `names=[]`, `variable_count=0`, no anomaly |
| Body says `{{nome}},{{cota}}` but examples say `nome`,`quota` | Declared set is the **body's**; `cota` example is `null`; `BODY_EXAMPLE_NAME_MISMATCH` anomaly retaining **both** sets |
| Named with `header_text_named_params` | Header names ignored entirely |
| Named, empty example for one name | `MISSING_NAMED_EXAMPLE`; that example stored as `null` |
| Named, body repeats a name | `DUPLICATE_BODY_PARAM_NAME`; names retained as observed |
| Positional (or omitted) format, named body | `POSITIONAL` + `POSITIONAL_FORMAT_NAMED_BODY`; format never inferred from the body |
| Names changed at Meta since last sync | Replaced **in place**; no duplicate template or translation |

---

## Scenario 2 — The format survives every webhook (Story 2, SC-002)

`extract_template_data` rebuilds the Flows payload from the mirror. Verified against
[Flows PR #876](https://github.com/weni-ai/flows/pull/876): for a template Flows already has, the
`template-sync` route only applies the status or category event and never re-reads `template_data`, so
nothing is cleared. The payload reaches Flows' parser when Flows has **not** yet seen the template — the
first webhook after approval, before the next bulk sync — and without `parameter_format` it lands
positional there.

**Setup**: a translation recorded as named with two names and examples.

**Run**: fire `message_template_status_update` and `template_category_update` (the two events that post
`template_data` to Flows). Separately fire `template_correct_category_detection` (Commerce proxy only).

**Assert after status and category-update**:

| Check | Expected |
| --- | --- |
| Local `parameter_format` | Still `"NAMED"` |
| Local `body_named_params` | Unchanged |
| `template_data` sent to Flows | Contains `"parameter_format": "NAMED"` |
| BODY component | Contains `example.body_text_named_params` with both entries |
| Anomalous translation | `parameter_format` present, but **no** `body_text_named_params` block — so Flows falls back to body names instead of unioning both sets |
| Positional translation | `template_data` reports `"POSITIONAL"`; BODY component otherwise unchanged, `example.body_text` still absent (no consumer in Flows) |
| Widened app lookup | An app configured only at `config.waba.id` now receives the event |

**Assert after `template_correct_category_detection`**: local format and names unchanged; Flows is **not**
called.

Gallery re-sync (Story 2 scenario 5) is exercised with Story 1's recording path in place, not as part of
Story 2's Independent Test.

```bash
poetry run python manage.py test marketplace.wpp_templates.tests.test_utils
```

**The regression this guards**: run Scenario 1, then Scenario 2, then re-read the mirror and the captured
Flows payload. The local format and names must be unchanged after every event. The payload must carry the
format on the two events that post to Flows.

---

## Scenario 3 — Authoring a named template (Story 3, SC-003, SC-004)

**Setup**: `WHATSAPP_NAMED_TEMPLATES_ENABLED=True`, `TemplateService.create_template_message` mocked.

### Accept

```json
POST /api/v1/apps/{app_uuid}/templates/{uuid}/translations/
{
  "language": "pt_BR",
  "body": {
    "type": "BODY",
    "text": "Olá {{nome}}, sua cota {{cota}} vence em {{data}}",
    "example": { "body_text_named_params": [
      {"param_name": "nome", "example": "João"},
      {"param_name": "cota", "example": "3/12"},
      {"param_name": "data", "example": "20/10/2026"}]}
  }
}
```

**Assert**: `create_template_message` called with `parameter_format="named"`; the BODY component carries
`body_text_named_params` with three entries; the translation is recorded `"NAMED"` with
`variable_count=3`.

### Reject — each produces zero local records and zero Meta calls

| Body | Expected field-level error |
| --- | --- |
| `Olá {{nome}}, pedido {{1}}` | One format per template; identifies the minority-format variables (FR-022) |
| `Olá {{nome}}, tudo bem {{nome}}?` | Names the duplicated parameter (FR-023) |
| `Olá {{Nome}}` | States Meta's naming rule (FR-024) |
| `Seu código {{2fa_code}}` | States the naming rule — a leading digit is rejected because Flows silently drops such names, leaving a parameter that never resolves |
| `Olá {{nome}}` with no example for `nome` | Identifies that parameter (FR-025) |
| `Olá {{nome}}` with the flag **off** | States that named templates are not enabled (FR-027) — **not** a silent downgrade to positional |
| Valid locally, rejected by Meta | Meta's reason surfaced verbatim; no local record (Story 3 scenario 7) |

**Assert on every rejection**: `create_template_message.assert_not_called()` and zero new
`TemplateTranslation` rows.

### Positional authoring unchanged

Submit a `{{1}}`/`{{2}}` body and assert the call kwargs contain **no** `parameter_format` key — the
request is byte-identical to today's (SC-008).

```bash
poetry run python manage.py test marketplace.wpp_templates.tests.test_serializers
```

---

## Scenario 4 — Reconciliation (Story 4, SC-005, SC-010)

**Setup**: seed translations recorded before the format existed — some with named bodies and
`variable_count=0` (the broken fleet), some correctly positional. Stub Meta's list response. Inject a fake
Redis.

```bash
poetry run python manage.py reconcile_template_parameters --limit 5 --dry-run --output /tmp/probe.csv
poetry run python manage.py reconcile_template_parameters --output /tmp/recon.csv
```

**Assert**:

| Check | Expected |
| --- | --- |
| Every template classified | Format set from Meta; named ones gain names and examples |
| Broken fleet counted | `previously_broken=true` on every named-body/zero-parameter row |
| Categories distinct | `corrected`, `unchanged`, `anomalous`, `format_not_yet_known`, `unclassifiable` never conflated |
| `ignores_meta_sync` apps | `unclassifiable`, reason `sync_disabled`; **not** counted as classified |
| No duplicates | Template and translation counts unchanged |
| Idempotent | A second run produces a **byte-identical** artifact |
| Resumable | Interrupt, re-run; already-processed WABAs are skipped |
| Pacing | Uses the existing per-WABA TTL lock and the existing drain budget; the scheduled sync is not interrupted |
| TTL lock held | WABA is `skipped_recent_sync`, not in `done_waba_ids`, no translation rows, not counted as classified |
| No example values | Neither the artifact nor the logs contain any (SC-011) |

```bash
poetry run python manage.py test marketplace.wpp_templates.usecases.tests.test_template_parameter_reconciliation
```

---

## Scenario 5 — Read surfaces (Story 5, SC-006, SC-007)

```bash
GET /api/v1/apps/{app_uuid}/templates/
GET /api/v1/apps/{app_uuid}/templates/{uuid}/
```

**Assert**:

| Check | Expected |
| --- | --- |
| Named template | Template `parameter_format: "NAMED"`; translation lists `parameter_names: ["nome","cota"]` |
| Positional template | `"POSITIONAL"`, `parameter_names: []`, `variable_count` still present |
| Not-yet-known | `parameter_format: null`, `parameter_names: []` |
| Translations disagree on format | Template level reads `"MIXED"`; per-translation values remain visible |
| Anomalous translation | `has_parameter_anomaly: true` |
| **No positional index** | No `index`, `position`, `slot` or `order` key anywhere in the response, at any depth |
| Tenancy | Only templates for apps the caller's project is authorised for |

The no-index check is a recursive scan of the whole response — see
[`contracts/read-surfaces.md`](./contracts/read-surfaces.md).

```bash
poetry run python manage.py test marketplace.wpp_templates.tests.test_views
```

---

## Scenario 6 — Positional templates untouched (Story 6, SC-008)

```bash
poetry run python manage.py test marketplace.wpp_templates
```

The existing sync, serializer, view and webhook suites must pass **unmodified**, except where a test
asserts the absence of the new fields or is a test double for the changed `create_template_message`
signature.

Then sync an account containing both formats and confirm each is recorded in its own format with neither
affecting the other.

---

## Scenario 7 — Graph API version scoping (SC-009)

```bash
poetry run python manage.py test marketplace.wpp_templates.tests.test_template_api_version
```

**Assert, on a `FacebookClient` instance** (this is the production client; class-level checks alone are not enough):

| Call | URL prefix |
| --- | --- |
| `create_template_message` / `list_template_messages` | `settings.WHATSAPP_TEMPLATE_API_URL` → `…/v25.0` |
| A catalog method (e.g. `create_catalog`) | `settings.WHATSAPP_API_URL` → unchanged |
| `"BASE_URL" in TemplatesRequests.__dict__` | `False` |
| `CatalogsRequests`, `PhoneNumbersRequests`, `CloudProfileRequests`, `PhotoAPIRequests`, `CallingRequests`, `BusinessMetaRequests`, `BusinessVerificationRequests`, `FacebookClient.BASE_URL` | `settings.WHATSAPP_API_URL` → unchanged |

**Note for the implementer**: do **not** override `BASE_URL` on `TemplatesRequests`. `FacebookClient`
mixins that class after `CatalogsRequests`, so a class-level `BASE_URL` would move catalogs, VTEX product
batch, commerce and onboarding to `v25.0`. Use a `template_api_url` property read only by template methods.
`FacebookAuthorization.BASE_URL` is still bound at class-definition time (`client.py:26`);
`override_settings` will not affect sibling class URLs.

### Manual pre-release check

Walk the endpoint table in [`contracts/meta-graph-templates.md`](./contracts/meta-graph-templates.md) and
confirm endpoint by endpoint that catalogs, product batch upload, commerce settings, phone numbers,
profile, OAuth, credit sharing and onboarding all still call their current version.

---

## Success criteria coverage

| Criterion | Scenario |
| --- | --- |
| SC-001 named templates recorded with format and names | 1 |
| SC-002 format survives every webhook | 2 |
| SC-003 authoring reaches Meta as named | 3 |
| SC-004 invalid bodies rejected before any Meta call | 3 |
| SC-005 reconciliation idempotent, no duplicates | 4 |
| SC-006 zero positional indexes anywhere | 5, plus mirror and both Flows payloads |
| SC-007 integrator determines format from the read surfaces alone | 5 |
| SC-008 positional behaviour unchanged | 1, 3, 6 |
| SC-009 version scoped to template surfaces | 7 |
| SC-010 broken fleet becomes a measured count | 4 |
| SC-011 no example values in informational logs | 1, 4 |
| SC-012 library rows never defaulted to positional | 1 (library variant) |
| SC-013 body-vs-example divergence stored per FR-011 | 1 (divergence variant) |

---

## Rollout

1. **Ship with `WHATSAPP_NAMED_TEMPLATES_ENABLED=False`.** Sync, webhook, read and reconciliation all work;
   only the creation of *new* named templates is closed. Safe regardless of downstream readiness.
2. **Run reconciliation** — bounded `--limit --dry-run` probe first, then the fleet. The first report turns
   the broken-template count from unknown into a number (SC-010).
3. **Flip the flag to `True`** once Flows, mailroom, goflow and courier have shipped (product spec BD-016).
4. **Track FR-040** — align `WHATSAPP_VERSION` fleet-wide with its own compatibility review, before
   `v25.0` expires on **2028-07-29**.
