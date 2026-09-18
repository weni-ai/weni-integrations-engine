# Phase 1 — Data Model: Named WhatsApp Template Parameters

**Feature**: `001-named-template-parameters` | **Date**: 2026-09-17

Scope of change: three columns added to `TemplateTranslation`. No new model, no new table, no new index,
no data migration. `TemplateMessage`, `TemplateButton` and `TemplateHeader` are unchanged.

---

## Entities

### `TemplateTranslation` (modified)

Located at `marketplace/wpp_templates/models.py:84`. Existing fields are unchanged; three are added.

| Field | Type | Null | Default | Added |
| --- | --- | --- | --- | --- |
| `uuid` | `UUIDField(unique=True)` | no | `uuid4` | — |
| `template` | `FK(TemplateMessage, related_name="translations")` | no | — | — |
| `status` | `CharField(20, choices=STATUS_CHOICES)` | yes | — | — |
| `body` | `CharField(2048)` | yes | — | — |
| `body_example` | `ArrayField(CharField(255))` | no | `list` | — |
| `footer` | `CharField(60)` | yes | — | — |
| `variable_count` | `IntegerField` | yes | — | — |
| `language` | `CharField(60)` | yes | — | — |
| `country` | `CharField(60)` | yes | — | — |
| `namespace` | `CharField(60)` | yes | — | — (dead field, untouched) |
| `external_id` | `CharField(60)` | yes | — | — (dead field, untouched) |
| `message_template_id` | `CharField(20)` | yes | — | — |
| **`parameter_format`** | `CharField(10, choices=PARAMETER_FORMAT_CHOICES)` | **yes** | `None` | **NEW** |
| **`body_named_params`** | `JSONField` | no | `list` | **NEW** |
| **`parameter_anomaly`** | `JSONField` | **yes** | `None` | **NEW** |

#### `parameter_format`

```python
PARAMETER_FORMAT_NAMED = "NAMED"
PARAMETER_FORMAT_POSITIONAL = "POSITIONAL"

PARAMETER_FORMAT_CHOICES = (
    (PARAMETER_FORMAT_NAMED, "WhatsApp.data.templates.parameter_format.named"),
    (PARAMETER_FORMAT_POSITIONAL, "WhatsApp.data.templates.parameter_format.positional"),
)

parameter_format = models.CharField(
    max_length=10, choices=PARAMETER_FORMAT_CHOICES, null=True, blank=True, default=None
)
```

Three states, carried by two choices plus `NULL`:

| Value | Meaning | How a row reaches it |
| --- | --- | --- |
| `"NAMED"` | Meta reported the template as named | Sync or reconciliation read `parameter_format` from Meta's list response; or authoring submitted a named template and Meta accepted it |
| `"POSITIONAL"` | Meta reported the template as positional, or omitted the key (Meta's documented default) | Sync, reconciliation, or positional authoring |
| `NULL` | **Format not yet known.** This service has not been told the format by Meta | Every row that existed before migration `0014`; every row created by the library path before its post-creation sync |

Stored uppercase regardless of the casing Meta used. Meta documents `named` / `positional` in its creation
payload and the enum `{NAMED, POSITIONAL}` in the Graph API reference, so normalisation is case-insensitive
(FR-002). The choices labels follow the translation-key convention already used by `STATUS_CHOICES` and
`CATEGORY_CHOICES` in this file.

`NULL` is not a placeholder standing in for a real value — it is a true statement about the row, and it is
what reconciliation exists to resolve (FR-014, FR-015).

#### `body_named_params`

```python
body_named_params = models.JSONField(default=list, blank=True)
```

An **ordered** list of objects using Meta's own key names:

```json
[
  { "param_name": "nome", "example": "João" },
  { "param_name": "cota", "example": null }
]
```

| Property | Rule |
| --- | --- |
| Order | The order the placeholders appear in `body`. Display metadata only (FR-005) |
| `param_name` | Stored exactly as it appears in the body. Never case-folded, stripped or otherwise transformed (NFR-007) |
| `example` | The value from Meta's `body_text_named_params`, or `null` when Meta supplied none or supplied an empty one (FR-011) |
| Uniqueness | Names are unique within a translation. Enforced at authoring (FR-023); a duplicate observed from Meta is recorded as an anomaly, not silently deduplicated |
| Positional translations | Always `[]` |
| Not-yet-known translations | Always `[]` |

**Never present in this structure**: any `index`, `position`, `slot` or `order` key. FR-005, FR-037 and
SC-006 forbid this service computing, storing, publishing or transmitting a positional index for a named
parameter, and the way that is guaranteed is that the structure has no field to hold one.

The key names are Meta's, not local inventions, so `extract_template_data` can emit
`{"body_text_named_params": translation.body_named_params}` with **zero transformation** — which matters
because that function rebuilds the Flows payload from the mirror and the less it transforms, the less it
can break (FR-017).

#### `parameter_anomaly`

```python
parameter_anomaly = models.JSONField(null=True, blank=True, default=None)
```

`NULL` means clean. When set, it holds the anomaly type plus the evidence that produced it:

```json
{
  "type": "BODY_EXAMPLE_NAME_MISMATCH",
  "observed_at": "2026-09-17T18:04:11.402Z",
  "body_param_names": ["nome", "cota"],
  "example_param_names": ["nome", "quota"],
  "reported_format": "named"
}
```

Anomaly types, one per condition the spec requires to be reported rather than guessed:

| `type` | Condition | Spec reference | Recorded format |
| --- | --- | --- | --- |
| `UNRECOGNISED_FORMAT` | Meta returned a `parameter_format` value that is neither named nor positional in any casing | FR-002, Story 1 scenario 4 | `POSITIONAL` |
| `BODY_EXAMPLE_NAME_MISMATCH` | The body's placeholders and `body_text_named_params` declare different name sets | FR-011, Story 1 scenario 6 | `NAMED`, with the body's names as the declared set |
| `MISSING_NAMED_EXAMPLE` | Meta declared a name with an empty or absent example | Edge Cases — Provider data | `NAMED`, example stored as `null` |
| `DUPLICATE_BODY_PARAM_NAME` | Meta's body repeats a parameter name | FR-023 (the inbound counterpart) | `NAMED`, names retained as observed |
| `POSITIONAL_FORMAT_NAMED_BODY` | Meta reports the template positional but its body contains named placeholders | Edge Cases; the shape reconciliation uses to detect the pre-existing defect | `POSITIONAL` — Meta is authoritative |

Evidence keys are populated per type; `body_param_names` and `example_param_names` are both retained for
`BODY_EXAMPLE_NAME_MISMATCH` because FR-011 requires both observed sets to survive.

**Why one JSON object**: FR-011 requires the marking to retain both name sets, so a bare code would lose
the evidence and a code plus two array columns would be three columns for one concept. `NULL` cleanly means
clean, which is the exact check every read surface and the reconciliation report performs.

#### `variable_count` (semantics changed, schema unchanged)

| Format | Value | Written by |
| --- | --- | --- |
| `NAMED` | `len(body_named_params)` | `TemplateSyncUseCase`, reconciliation, named authoring |
| `POSITIONAL` | literal `0` — unchanged | `serializers.py:189`, `template_sync.py:223`, `template_library_creation.py:298` |
| `NULL` (not yet known) | literal `0` — unchanged | `template_library_creation.py:298` |

FR-006. The positional constant zero is preserved deliberately: changing it is a positional behaviour
change with no requirement behind it, and Flows computes its own count from Meta's raw payload on the bulk
path, so this value is consumed only by this service's own read surfaces.

---

## Derived values (never stored)

### Template-level parameter format

Computed by `TemplateMessageSerializer` from the template's translations. Published on the read surfaces;
**never persisted, never sent to Meta, never accepted as input**.

| Condition | Value |
| --- | --- |
| No translations, or every translation's format is `NULL` | `null` |
| All translations with a known format agree | that value — `"NAMED"` or `"POSITIONAL"` |
| Translations with a known format disagree | `"MIXED"` |

Translations whose format is `NULL` are excluded from the agreement test rather than forcing `"MIXED"` — a
row nobody has classified yet is not a disagreement. The per-translation values remain visible in the same
response, so nothing is hidden (FR-008, Story 5 scenario 4).

### Readiness for named dispatch

Not a field and not a published verdict. A consumer derives it as
`parameter_format == "NAMED" and not has_parameter_anomaly`. This service publishes the facts; the
parameter policy and the dispatch decision belong to Flows (FR-011, FR-015).

---

## State machine — `parameter_format`

```
                    ┌──────────────────────────────────────────┐
                    │  NULL  — format not yet known            │
                    │  (every pre-0014 row; every library row  │
                    │   before its post-creation sync)         │
                    └───────────────┬──────────────────────────┘
                                    │
                   Meta describes the template
              (scheduled sync, on-demand sync, library
               post-creation sync, or reconciliation)
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
        ┌───────────────────┐               ┌───────────────────┐
        │     "NAMED"       │               │   "POSITIONAL"    │
        │ body_named_params │               │ body_named_params │
        │   = [...]         │◄──────────────│   = []            │
        │ variable_count    │   (only if    │ variable_count = 0│
        │   = len(names)    │  Meta itself  │                   │
        └─────────┬─────────┘   changes it) └─────────┬─────────┘
                  │                                   │
                  │  every subsequent sync re-reads Meta and
                  │  overwrites names/examples IN PLACE (FR-012)
                  └───────────────────┬───────────────┘
                                      ▼
                            translation deleted when
                            Meta stops returning it
                            (existing behaviour, takes the
                             parameter metadata with it)
```

**Transitions**

| From | To | Trigger | Rule |
| --- | --- | --- | --- |
| `NULL` | `NAMED` / `POSITIONAL` | Any path that reads Meta's description of the template | The normal resolution. This is what reconciliation does to the legacy fleet |
| `NAMED` | `NAMED` | Sync observes changed names | Names replaced **in place** — no duplicate template, no duplicate translation (FR-012, Story 1 scenario 8) |
| `NAMED` / `POSITIONAL` | the other | Only if Meta itself reports a different format | Meta fixes the format at creation, so this is not expected. It is not blocked, because Meta is authoritative (FR-001) and blocking would let the mirror diverge permanently |
| anything | `NULL` | **Never** | Once Meta has described a template, the recorded value is never unset. A status-only or category-only webhook must not clear it (FR-017, FR-018) |
| `NULL` | anything, by inference from body text | **Never**, for a template that already exists at Meta | FR-003. Detection from body text is permitted only at authoring, before the template exists at Meta (FR-020) |

**The one-way rule is the spine of Story 2.** The regression the product spec calls the highest risk
(BD-015) is precisely a transition back toward `NULL`/empty on a routine webhook, so it is expressed here
as a prohibition rather than left implicit.

---

## Recording rules — Meta list response to stored values

Applied identically by `TemplateSyncUseCase` and `TemplateParameterReconciliationUseCase`, because both
call the same `parameters.build_translation_parameters(meta_template)`.

| Meta's `parameter_format` | Recorded `parameter_format` | Recorded `body_named_params` | Anomaly |
| --- | --- | --- | --- |
| `"named"` / `"NAMED"` / `"Named"` | `NAMED` | Names parsed from the body in body order, each paired with its example from `body_text_named_params` where one exists | Set only if a condition below applies |
| `"positional"` / `"POSITIONAL"` | `POSITIONAL` | `[]` | `POSITIONAL_FORMAT_NAMED_BODY` if the body contains named placeholders |
| key absent | `POSITIONAL` (Meta's documented default) | `[]` | `POSITIONAL_FORMAT_NAMED_BODY` if the body contains named placeholders |
| unrecognised string | `POSITIONAL` | `[]` | `UNRECOGNISED_FORMAT`, logged with app, project and template identifiers |

Within the `NAMED` branch:

| Situation | Declared set | Examples | Anomaly |
| --- | --- | --- | --- |
| Body names and `body_text_named_params` names match | body names, body order | one per name | none |
| Body has zero placeholders | `[]`, `variable_count = 0` | — | none — this is valid (Story 1 scenario 7) |
| Name sets disagree | **the body's names** — the only ordered source and the set a send must satisfy | only for the names Meta actually supplied; the rest `null`, never borrowed or invented | `BODY_EXAMPLE_NAME_MISMATCH`, retaining both sets (FR-011) |
| A name has an empty or absent example | body names | `null` for that name | `MISSING_NAMED_EXAMPLE` |
| The body repeats a name | names as observed | matched where possible | `DUPLICATE_BODY_PARAM_NAME` |
| `header_text_named_params` present | ignored entirely | — | none — this release names body parameters only |

Determinism (NFR-008): the mapping is a pure function of the Meta template dict. The same response always
produces the same format, the same names in the same order, the same examples and the same anomaly.

---

## Migration `0014`

**File**: `marketplace/wpp_templates/migrations/0014_templatetranslation_parameters.py`
**Depends on**: `0013_auto_20260410_1837`

```python
class Migration(migrations.Migration):
    dependencies = [("wpp_templates", "0013_auto_20260410_1837")]

    operations = [
        migrations.AddField(
            model_name="templatetranslation",
            name="parameter_format",
            field=models.CharField(
                blank=True,
                choices=[
                    ("NAMED", "WhatsApp.data.templates.parameter_format.named"),
                    ("POSITIONAL", "WhatsApp.data.templates.parameter_format.positional"),
                ],
                default=None,
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="templatetranslation",
            name="body_named_params",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="templatetranslation",
            name="parameter_anomaly",
            field=models.JSONField(blank=True, default=None, null=True),
        ),
    ]
```

### NFR-005 compliance

| Requirement | How it is met |
| --- | --- |
| No long exclusive lock | Three `ADD COLUMN` statements. On PostgreSQL 14, a nullable `ADD COLUMN` never rewrites the table, and `ADD COLUMN` with a **constant** default (`'[]'::jsonb`) has been catalog-only since PostgreSQL 11. The `ACCESS EXCLUSIVE` lock covers a catalog update measured in milliseconds, not a table scan |
| No index build | None of the three columns is indexed. There is no query that filters on them: the read surfaces fetch translations by template, and reconciliation iterates by WABA |
| No data migration | No `RunPython`, no backfill. `NULL` is the correct value for every existing row, which is the whole reason the third state is carried by `NULL` |
| Existing rows valid and readable immediately | Post-migration, every pre-existing row reads as `parameter_format=None`, `body_named_params=[]`, `parameter_anomaly=None` — "format not yet known, no parameters recorded, no anomaly observed". True for every one of them |
| Reversible | All three operations reverse to `RemoveField`. Rolling back drops columns the previous code never read |

### Deployment ordering

The migration is **additive and independently deployable**. It can land before the code that writes the new
columns, because nothing reads them until the new code ships. Old application instances running against the
migrated schema are unaffected — they neither read nor write the new columns, and every one has a usable
default.

This matters for a rolling deploy: there is no window in which mixed old/new instances can corrupt a row.

---

## Tenancy

`TemplateTranslation` reaches the tenant through `template → app → project_uuid`, exactly as today. The new
columns change nothing about that:

- Parameter names and examples are written per app from that app's own WABA response. When several apps
  share a WABA, each app's own rows are written from the same response; no value is ever read from one
  app's row to populate another's (FR-042).
- Read surfaces are unchanged in scoping: `TemplateMessageViewSet.get_queryset()` filters by `app_uuid`
  behind `ProjectManagePermission` (Story 5 scenario 5).
- The reconciliation report spans projects by design — it is an operator fleet artifact with no HTTP
  surface, written to the operator's filesystem and never served by this service.

---

## What is deliberately not modelled

| Not added | Why |
| --- | --- |
| A `TemplateParameter` model with an `order` column | An explicit ordinal per parameter is precisely the positional index FR-005 and SC-006 forbid this service from computing or storing. It would also add a join to every read for data that is always read and written as a whole list |
| A persisted reconciliation report model | Explicitly out of scope (FR-030, Out of Scope). Progress lives in Redis with a 24h TTL; the report is a file |
| A `ready_for_named_dispatch` column | Readiness depends on the parameter policy, which belongs to Flows. This service stores facts |
| A `header_named_params` column | Named header parameters are out of scope this release. `header_text_named_params` is skipped, not stored |
| Revival of `namespace` / `external_id` | Pre-existing dead fields, explicitly out of scope |
| A constraint enforcing `variable_count == len(body_named_params)` for named rows | Positional rows keep a literal `0` that has never matched their body, so the invariant cannot be expressed as a table-level check without first changing positional behaviour — which FR-041 forbids. The invariant is enforced in the single pure function that computes both |
