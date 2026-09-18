# Contract — Weni Flows template registry

**Direction**: outbound, this service → Flows
**Client**: `marketplace/clients/flows/client.py::FlowsClient`

Two paths push template data to Flows.

| Path | Method | Payload origin | Contract change |
| --- | --- | --- | --- |
| Bulk sync | `PATCH /template/{flow_object_uuid}/` | **Meta's list response, verbatim** | **None** — verify only |
| Webhook sync | `POST /template/{flow_object_uuid}/template-sync/` | **Rebuilt from the local mirror** | **Required** |

**Verified against the Flows side**: [`weni-ai/flows` PR #876](https://github.com/weni-ai/flows/pull/876),
branch `feat/named-template-variables`, head `6f0b9d9`. Everything below that describes Flows' behaviour
was read from `temba/templates/views.py`, `temba/templates/serializers.py` and
`temba/utils/whatsapp/tasks.py` on that branch.

## How Flows consumes both paths

```python
# temba/templates/views.py
class TemplateViewSet(viewsets.ModelViewSet, InternalGenericViewSet):
    def partial_update(self, request, pk):                     # ← bulk PATCH
        update_local_templates(channel, request.data.get("data"))

    def _handle_template_sync(self, validated_data, channel):   # ← webhook POST
        template = Template.objects.filter(name=template_name, org=channel.org).first()
        if template:
            update_template_sync(template.id, webhook)          # status/category ONLY
            return Response(status=200)
        update_local_templates(channel, [validated_data.get("template_data")], True)
```

```python
# temba/utils/whatsapp/tasks.py — the single parser for both paths
parameter_format = normalize_parameter_format(template.get("parameter_format"))
parameter_names = (
    extract_parameter_names_from_components(template.get("components")) if parameter_format == "named" else []
)
variable_count = len(parameter_names) if parameter_format == "named" else _calculate_variable_count(content)
```

Three consequences that shape this contract:

1. **`normalize_parameter_format` is case-insensitive** (`value.strip().lower() == "named"`) and returns
   `"positional"` for anything else, including `None`. Our uppercase `"NAMED"` works; an omitted key means
   positional, matching Meta.
2. **`TemplateSyncSerializer.template_data` is a plain `serializers.DictField`**, so no field of ours is
   stripped in validation.
3. **For a template Flows already has, `template_data` is never read.** `update_template_sync` routes to
   `update_template_status` / `update_template_category`, which write only `status` or `category`. The
   payload only reaches the parser when Flows has **not** yet seen the template.

---

## Path 1 — Bulk sync (no contract change)

```python
# marketplace/clients/flows/client.py:97 — UNCHANGED
def update_facebook_templates(self, flow_object_uuid, fba_templates):
    data = {"data": fba_templates}
    url = f"{self.base_url}/template/{flow_object_uuid}/"
    return self.make_request(url, method="PATCH", headers=..., json=data)
```

Called from `TemplateSyncUseCase.sync_templates()` with the Meta list `templates` list unmodified, **before**
the local upsert.

**Verified**: the only transformation is the `{"data": ...}` envelope. Nothing iterates the list, nothing
copies fields, nothing filters keys. `parameter_format` and `example.body_text_named_params` therefore
reach Flows for free (FR-013, NFR-002).

### The task here is verification, not modification

FR-013 forbids any field being stripped, renamed or reshaped on this path. A regression test asserts that
the object passed to `update_facebook_templates` is **identity-equal** to the list received from
`list_template_messages`:

```python
self.assertIs(flows_client.update_facebook_templates.call_args.args[1], meta_templates)
```

Identity rather than equality, because a defensive `copy()` or a comprehension introduced later would still
compare equal while creating a place where a field could subsequently be dropped. The point of the
assertion is to make that impossible to add silently.

**Do not** "improve" this path by building a payload. The fact that it forwards Meta verbatim is the reason
it is already correct.

---

## Path 2 — Webhook sync (contract change required)

```python
# marketplace/clients/flows/client.py:109 — UNCHANGED
def update_facebook_templates_webhook(self, flow_object_uuid, template_data, template_name, webhook=None):
    data = {"template_name": template_name, "template_data": template_data}
    if webhook:
        data["webhook"] = webhook
    url = f"{self.base_url}/template/{flow_object_uuid}/template-sync/"
    return self.make_request(url, method="POST", headers=..., json=data)
```

The client is unchanged. What changes is **`template_data`**, produced by
`marketplace/wpp_templates/utils.py::extract_template_data(translation)`.

### Why this still matters — and the risk correction

This function **rebuilds** the payload from the local mirror rather than forwarding Meta's, and it runs on
every `message_template_status_update` and every `template_category_update`.

The spec (following product spec BD-015) treats this as the highest-risk regression: a routine approval
event overwriting what the bulk sync recorded. **Verification against Flows PR #876 shows that does not
happen.** When Flows already has the template, `_handle_template_sync` calls `update_template_sync`, which
only writes `status` or `category` and never re-reads `template_data`. Nothing gets cleared.

The change is still required, for a narrower window: when Flows has **not** yet seen the template — the
first webhook after approval, before the next daily bulk sync — `update_local_templates` *is* called with
this payload. Without `parameter_format`, `normalize_parameter_format(None)` returns `"positional"` and the
template lands positional in Flows, staying broken until the next bulk sync corrects it.

So: same change, same tests across all three event types, materially lower severity than the spec assumed.

### Current output (defective)

```json
{
  "name": "order_update",
  "components": [
    { "type": "BODY", "text": "Olá {{nome}}, sua cota {{cota}} vence hoje" }
  ],
  "language": "pt_BR",
  "status": "APPROVED",
  "category": "UTILITY",
  "id": "1234567890"
}
```

No `parameter_format`. No `example` on the BODY component — note this drops the **positional**
`body_example` too, which is a pre-existing defect on the same expression.

### Required output — named translation

```json
{
  "name": "order_update",
  "parameter_format": "NAMED",
  "components": [
    { "type": "BODY", "text": "Olá {{nome}}, sua cota {{cota}} vence hoje",
      "example": {
        "body_text_named_params": [
          { "param_name": "nome", "example": "João" },
          { "param_name": "cota", "example": "3/12" }
        ]
      } }
  ],
  "language": "pt_BR",
  "status": "APPROVED",
  "category": "UTILITY",
  "id": "1234567890"
}
```

Because `body_named_params` is stored in Meta's own shape, the BODY `example` is emitted with **zero
transformation**:

```python
if translation.body_named_params:
    body_component["example"] = {"body_text_named_params": translation.body_named_params}
```

### Required output — positional translation

```json
{
  "name": "order_update",
  "parameter_format": "POSITIONAL",
  "components": [
    { "type": "BODY", "text": "Olá {{1}}, seu pedido {{2}} foi enviado." }
  ],
  "language": "pt_BR",
  "status": "APPROVED",
  "category": "UTILITY",
  "id": "1234567890"
}
```

`parameter_format` is the **only** addition. The BODY component is unchanged, and the pre-existing drop of
`example.body_text` is deliberately **left in place**: Flows' `TemplateTranslation` has no example field,
and `update_local_templates` reads `example` only inside `extract_parameter_names_from_components`, which
looks exclusively at `body_text_named_params`. Positional examples have no consumer, so restoring them
would deviate from FR-041 and SC-008 for nothing. Recorded as debt in `plan.md`.

### Output — not-yet-known translation

`parameter_format` is **omitted** from the payload when `translation.parameter_format` is `NULL`. Omitting
is honest — Meta's own convention treats an absent `parameter_format` as positional, and this service has
nothing to assert. Emitting `null` would invite a consumer to record a literal null as a format.

### Anomalous translations (FR-011)

A translation with a non-null `parameter_anomaly` **must not be pushed as a clean named template**. Its
`parameter_format` is emitted as recorded, but no `body_text_named_params` example block is attached,
because the names and the examples are known to disagree and sending them would present unverified data as
a clean named declaration. The anomaly itself is not pushed — it is operator-facing, reported through the
logs and the reconciliation artifact.

This also produces the **correct** result on the Flows side. Their
`extract_parameter_names_from_components` reads `body_text_named_params` first and then appends body names
not already seen, so on a mismatch it yields the *union* of both sets. Omitting the example block makes it
fall back to body text alone, which is the declared set FR-011 requires and matches what we record.

---

## Change summary

| Element | Before | After |
| --- | --- | --- |
| `template_data.parameter_format` | absent | present for `NAMED` / `POSITIONAL`; omitted when not yet known |
| BODY `example.body_text_named_params` | absent | present for clean named translations |
| BODY `example.body_text` | **dropped** (pre-existing defect) | still dropped — no consumer in Flows; recorded as debt |
| HEADER / FOOTER / BUTTONS components | as today | unchanged |
| `name`, `language`, `status`, `category`, `id` | as today | unchanged |

---

## Pre-release gate — closed

The gate was: confirm Flows' `template-sync` route accepts `parameter_format` at the root of
`template_data` and `example.body_text_named_params` on the BODY component.

**Both confirmed** against PR #876. `TemplateSyncSerializer.template_data` is a plain `DictField` that
strips nothing, and `update_local_templates` — the parser for both the bulk and the webhook path — reads
exactly those two fields. No cross-repository confirmation remains outstanding for this contract.

Fields `update_local_templates` requires and that `extract_template_data` already emits: `status`,
`components`, `language`, `category`, `name`, and `id` (falling back to `{language}/{name}` when absent).

---

## Also unchanged

| Element | Why |
| --- | --- |
| Endpoint URLs | No new endpoint, no extra round trip (NFR-002) |
| Call ordering | The bulk push still happens **before** the local upsert |
| `FlowsClient` method signatures | Both methods unchanged; only `template_data`'s contents change |
| `FlowsService.update_facebook_templates_webhook` | Pass-through, unchanged |
| Header/footer variable skip | Lives in Flows' `update_local_templates`, **not here**. This service processes every template Meta returns. Do not implement it |
