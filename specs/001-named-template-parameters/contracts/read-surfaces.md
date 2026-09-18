# Contract — REST read surfaces

**Direction**: inbound, consumers → this service
**Serializers**: `marketplace/wpp_templates/serializers.py`
**Permission**: `ProjectManagePermission` (unchanged)

Two endpoints return template content and are therefore in scope (FR-035):

| Endpoint | View |
| --- | --- |
| `GET /api/v1/apps/{app_uuid}/templates/` | `TemplateMessageViewSet.list` |
| `GET /api/v1/apps/{app_uuid}/templates/{uuid}/` | `TemplateMessageViewSet.retrieve` |

`GET /api/v1/project/templates/details/` is **out of scope**. It returns `WhatsappCloudDTO`
(`{app_uuid, templates_uuid}`) and resolves a Meta `message_template_id` to local UUIDs. It carries no
body, no format and no parameter names, so there is nothing to extend.

---

## Response shape

```json
{
  "uuid": "6b2f...",
  "name": "order_update",
  "created_on": "2026-09-17T12:00:00Z",
  "category": "UTILITY",
  "text_preview": "Olá {{nome}}, sua cota {{cota}} vence hoje",
  "gallery_version": null,
  "parameter_format": "NAMED",
  "translations": [
    {
      "uuid": "9c41...",
      "message_template_id": "1234567890",
      "status": "APPROVED",
      "language": "pt_BR",
      "country": "Brasil",
      "header": { "header_type": "TEXT", "text": "Aviso" },
      "body": "Olá {{nome}}, sua cota {{cota}} vence hoje",
      "body_example": [],
      "footer": "Equipe Weni",
      "buttons": [],
      "variable_count": 2,
      "parameter_format": "NAMED",
      "parameter_names": ["nome", "cota"],
      "has_parameter_anomaly": false
    }
  ]
}
```

### New fields

| Field | Level | Type | Semantics |
| --- | --- | --- | --- |
| `parameter_format` | template | `"NAMED"` \| `"POSITIONAL"` \| `"MIXED"` \| `null` | Derived from the translations. Never stored |
| `parameter_format` | translation | `"NAMED"` \| `"POSITIONAL"` \| `null` | The recorded value. `null` = format not yet known |
| `parameter_names` | translation | `string[]` | Declared names in body order. `[]` for positional and for not-yet-known |
| `has_parameter_anomaly` | translation | `boolean` | `true` when `parameter_anomaly` is set |

### Unchanged fields

`variable_count` is kept and still published (FR-036), so one consumer handles both formats: it reads the
declared-name count for a named translation and the existing constant `0` for a positional one.
`body_example` is kept, still the positional example array, and is **never** populated with named examples
(FR-007).

---

## Template-level derivation

| Condition | `parameter_format` |
| --- | --- |
| No translations, or all translations `null` | `null` |
| All translations with a known format agree | that value |
| Translations with a known format disagree | `"MIXED"` |

Translations whose format is `null` do not force `"MIXED"` — an unclassified row is not a disagreement.
The per-translation values are in the same response, so a consumer can always see the detail behind
`"MIXED"` (FR-008, Story 5 scenario 4).

`"MIXED"` is read-only. It is never persisted, never sent to Meta, and never accepted as input.

---

## Format matrix

| Translation state | `parameter_format` | `parameter_names` | `variable_count` | `has_parameter_anomaly` |
| --- | --- | --- | --- | --- |
| Named, clean, 2 parameters | `"NAMED"` | `["nome", "cota"]` | `2` | `false` |
| Named, zero placeholders | `"NAMED"` | `[]` | `0` | `false` |
| Named, body/examples disagree | `"NAMED"` | body's names | count of body names | `true` |
| Positional | `"POSITIONAL"` | `[]` | `0` | `false` |
| Positional body but named placeholders | `"POSITIONAL"` | `[]` | `0` | `true` |
| Format not yet known (library, pre-sync) | `null` | `[]` | `0` | `false` |
| Legacy row, pre-reconciliation | `null` | `[]` | `0` or as recorded | `false` |

---

## Prohibited in every response

FR-005, FR-037 and SC-006 forbid publishing a positional index or slot number beside a named parameter. The
shape makes this structural: `parameter_names` is a list of **bare strings**, so there is no field in which
an index could appear.

**No response may contain** `index`, `position`, `slot` or `order` keyed against a parameter — at any depth.

A test asserts this by walking the whole response recursively:

```python
def assert_no_positional_keys(self, node):
    forbidden = {"index", "position", "slot", "order"}
    if isinstance(node, dict):
        self.assertEqual(forbidden & set(node), set())
        for value in node.values():
            self.assert_no_positional_keys(value)
    elif isinstance(node, list):
        for item in node:
            self.assert_no_positional_keys(item)
```

The array ordering of `parameter_names` is display metadata, which FR-005 permits explicitly.

---

## Also not published

| Not published | Why |
| --- | --- |
| Example values | No requirement asks for them, and they are metadata the author already holds. YAGNI |
| The `parameter_anomaly` evidence object | Operator-facing, not consumer-facing. It reaches operators through the logs and the reconciliation artifact. The boolean is what a consumer needs |
| A `ready_for_named_dispatch` flag | Readiness also depends on the parameter policy, which belongs to Flows. This service publishes facts, not verdicts. The derivation is `parameter_format == "NAMED" and not has_parameter_anomaly` |

---

## Compatibility

| Guarantee | How |
| --- | --- |
| Every existing field keeps its name, type and meaning | Only additive fields |
| A positional template's response gains three fields and changes none | `parameter_format: "POSITIONAL"`, `parameter_names: []`, `has_parameter_anomaly: false` |
| Tenancy is unchanged | `get_queryset()` filters by `app_uuid` behind `ProjectManagePermission` (Story 5 scenario 5) |
| Pagination, filtering and ordering unchanged | `CustomResultsPagination` and `filter_queryset` untouched |
| Write payloads unchanged | The three new fields are **read-only**. `parameter_format` is never accepted as input — it is a property of the body (FR-020) |
