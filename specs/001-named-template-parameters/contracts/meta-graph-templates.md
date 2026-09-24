# Contract — Meta Graph API (template surfaces)

**Direction**: outbound, this service → Meta
**Client**: `marketplace/clients/facebook/client.py::TemplatesRequests`
**Graph API version**: `v25.0` via `settings.WHATSAPP_TEMPLATE_API_URL`

---

## Version scoping

```python
# marketplace/settings.py

WHATSAPP_VERSION = env.str("WHATSAPP_VERSION", default="v16.0")
WHATSAPP_API_URL = urllib.parse.urljoin(
    env.str("WHATSAPP_API_URL", default="https://graph.facebook.com/"), WHATSAPP_VERSION
)

# Template surfaces run at their own Graph version because `parameter_format` and
# `body_text_named_params` do not exist below v23.0, while WHATSAPP_API_URL is the base URL for
# catalogs, product batch upload, commerce settings, phone numbers, profile, OAuth, credit sharing
# and onboarding. Aligning those onto the newer version is tracked separately (FR-040); v25.0
# expires 2028-07-29.
WHATSAPP_TEMPLATE_VERSION = env.str("WHATSAPP_TEMPLATE_VERSION", default="v25.0")
WHATSAPP_TEMPLATE_API_URL = urllib.parse.urljoin(
    env.str("WHATSAPP_API_URL", default="https://graph.facebook.com/"), WHATSAPP_TEMPLATE_VERSION
)
```

```python
# marketplace/clients/facebook/client.py

class TemplatesRequests(FacebookAuthorization, RequestClient, TemplatesRequestsInterface):
    @property
    def template_api_url(self):
        """Template Graph version. Not BASE_URL — FacebookClient MRO would leak a BASE_URL
        override onto catalogs, commerce and onboarding (FR-039, SC-009)."""
        return settings.WHATSAPP_TEMPLATE_API_URL
```

Do **not** assign `BASE_URL` on this class. Template methods interpolate `self.template_api_url`; every
other method on `FacebookClient` keeps `self.get_url` → `WHATSAPP_API_URL`.
### Endpoint-by-endpoint version map (SC-009 verification table)

| Client class | Endpoints | Version source | Changes? |
| --- | --- | --- | --- |
| `TemplatesRequests` methods (also when called on `FacebookClient`) | `POST/GET/DELETE {waba_id}/message_templates`, `POST {message_template_id}`, `GET {waba_id}/template_analytics`, `POST {waba_id}` (insights) | `WHATSAPP_TEMPLATE_API_URL` via `template_api_url` | **YES → v25.0** |
| `FacebookClient` non-template methods | catalogs, product batch, commerce, phone numbers, profile, OAuth, credit sharing, onboarding | `WHATSAPP_API_URL` via `get_url` | no |
| `CatalogsRequests` | `{business_id}/owned_product_catalogs`, catalog CRUD, product batch upload | `WHATSAPP_API_URL` | no |
| `PhoneNumbersRequests` | phone number nodes | `WHATSAPP_API_URL` | no |
| `CloudProfileRequests` | business profile, `{phone_number_id}/settings` | `WHATSAPP_API_URL` | no |
| `PhotoAPIRequests` | upload sessions | `WHATSAPP_API_URL` | no |
| `CallingRequests` | calling settings | `WHATSAPP_API_URL` | no |
| `BusinessMetaRequests` | OAuth, credit sharing, onboarding | `WHATSAPP_API_URL` | no |
| `BusinessVerificationRequests` | verification | `WHATSAPP_API_URL` | no |
| `core/types/channels/whatsapp/apis.py`, `whatsapp_base/requests/facebook.py` | on-premises WABA info | `WHATSAPP_VERSION` | no |

The three template surfaces that move beyond FR-038's literal list — template namespace, template
analytics and template insights — are template surfaces and are **not** in the set SC-009 protects. They
move because they live on `TemplatesRequests`, which is what makes the scoping a property on that class
rather than a per-method special case.

---

## `POST /{waba_id}/message_templates` — create

### Positional (unchanged from today — byte-identical)

```json
{
  "name": "order_update",
  "category": "UTILITY",
  "language": "pt_BR",
  "components": [
    { "type": "BODY", "text": "Olá {{1}}, seu pedido {{2}} foi enviado.",
      "example": { "body_text": [["João", "12345"]] } }
  ]
}
```

`parameter_format` **is not sent**. Meta documents an omitted `parameter_format` as positional, so omitting
it keeps this request identical to today's (FR-026, FR-041, SC-008).

### Named (new)

```json
{
  "name": "order_update",
  "category": "UTILITY",
  "language": "pt_BR",
  "parameter_format": "named",
  "components": [
    { "type": "BODY", "text": "Olá {{nome}}, sua cota {{cota}} vence em {{data}}.",
      "example": {
        "body_text_named_params": [
          { "param_name": "nome", "example": "João" },
          { "param_name": "cota", "example": "3/12" },
          { "param_name": "data", "example": "20/10/2026" }
        ]
      } }
  ]
}
```

| Element | Rule |
| --- | --- |
| `parameter_format` | Sent as lowercase `"named"`, matching Meta's creation documentation. Sent **only** for named templates |
| Placement | Template root, **not** inside the BODY component |
| `body_text_named_params` | One entry per placeholder in the body. Every entry has a non-empty `example` — a missing example is rejected locally before this request is built (FR-025) |
| Order | Body order. Meta accepts any order; this service sends body order for legibility |
| Header/footer/buttons | Assembled exactly as today. `header_text_named_params` is never sent (out of scope) |

### Preconditions enforced before this request is built

All are field-level rejections that produce **zero** local records and **zero** Meta calls (SC-004):

| Condition | Requirement |
| --- | --- |
| Body mixes `{{nome}}` and `{{1}}` | FR-022 |
| A parameter name repeats | FR-023 |
| A name fails `^[a-z_][a-z0-9_]*$` | FR-024 (leading-digit rejection is required for Flows compatibility) |
| A named parameter has no example | FR-025 |
| `WHATSAPP_NAMED_TEMPLATES_ENABLED` is `False` and the body is named | FR-027 |

### Responses

| Outcome | Handling |
| --- | --- |
| `200` with `{"id": ..., "status": ..., "category": ...}` | Translation created; `parameter_format` recorded from the submitted format, superseded by Meta's value on the first sync that reports it (FR-003) |
| `400` naming a body or parameter problem | Meta's reason surfaced verbatim, not reinterpreted; no local record (FR-024, Story 3 scenario 7) |
| `400` indicating `parameter_format` is unsupported | Surfaced as a **configuration** error naming the unsupported capability, not a template validation error (Edge Cases — Provider version) |

---

## `GET /{waba_id}/message_templates` — list

Request unchanged (`limit=9999`). The response gains fields this service now reads.

```json
{
  "data": [
    {
      "id": "1234567890",
      "name": "order_update",
      "language": "pt_BR",
      "status": "APPROVED",
      "category": "UTILITY",
      "parameter_format": "NAMED",
      "components": [
        { "type": "BODY", "text": "Olá {{nome}}, sua cota {{cota}} vence hoje",
          "example": {
            "body_text_named_params": [
              { "param_name": "nome", "example": "João" },
              { "param_name": "cota", "example": "3/12" }
            ]
          } }
      ]
    }
  ]
}
```

### Fields consumed

| Field | Use |
| --- | --- |
| `parameter_format` | Recorded case-insensitively. Absent → `POSITIONAL`. Unrecognised → `POSITIONAL` + `UNRECOGNISED_FORMAT` anomaly (FR-002) |
| BODY `text` | Source of the parameter **names** and their **order** for a named template (FR-004). Never used to infer the *format* of a template Meta has already described (FR-003) |
| BODY `example.body_text_named_params` | Source of the example values, cross-checked against the body (FR-011) |
| BODY `example.body_text` | Positional examples — handled exactly as today |
| `example.header_text_named_params` | **Ignored**, explicitly skipped rather than left to fall through (out of scope) |

**NFR-001**: no additional Meta request per template. Everything is read from this one list response, which
the sync already fetches once per WABA.

---

## `POST /{message_template_id}` — update

**Unchanged.** Payload remains `{"name": ..., "components": [...]}`.

`parameter_format` is **never** sent on this endpoint. FR-019 forbids attempting to change a template's
format at Meta or converting a template between formats, and the enforcement is that the method has no
parameter through which a format could be expressed. On an edit, the stored parameter names are re-derived
from the submitted body locally; Meta is told only about the components.

---

## `POST /{waba_id}/message_templates` — library create

**Request unchanged.** It carries `library_template_name` and button inputs, not body text, so no
`parameter_format` can be derived from it and none is sent.

**Response** carries only `id`, `status` and `category` — no `parameter_format`. The translation is
therefore created with `parameter_format = NULL` (format not yet known) rather than defaulted to
positional, and the existing post-creation `sync_pending_templates` task resolves it authoritatively
(FR-014, FR-015, SC-012).

---

## Meta facts this contract depends on

Verified against Meta's documentation on 2026-09-17:

- `parameter_format` accepts `named` / `positional`; the Graph API reference documents the enum as
  `{NAMED, POSITIONAL}` — hence case-insensitive recording.
- An omitted `parameter_format` means positional.
- Named parameters must be unique single strings of lowercase characters and underscores wrapped in double
  curly brackets, with one example value per parameter.
- Example values may appear in any order in the creation payload — only the body carries order.
- Body text maximum is 1024 characters (`TemplateTranslation.body` allows 2048).
- `v25.0` released 2026-02-18, expires 2028-07-29.
