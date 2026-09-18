# Phase 0 — Research: Named WhatsApp Template Parameters

**Feature**: `001-named-template-parameters` | **Date**: 2026-09-17

The specification carries zero `[NEEDS CLARIFICATION]` markers and zero open questions, so Phase 0 is not
about resolving ambiguity in the spec. It resolves the ten decisions the spec explicitly deferred to
planning, plus the provider facts those decisions depend on.

Every claim about current behaviour below was verified against the code at the paths and line numbers
given. Every claim about Meta was verified against Meta's live documentation on 2026-09-17.

---

## Provider facts established

### Meta's named-parameter contract

Verified against *Template fundamentals*, *Template components* and the Graph API reference for
`WhatsAppBusinessAccount/message_templates`.

**Creation payload** — `parameter_format` sits at the **template root**, not inside the BODY component:

```json
{
  "name": "order_confirmation",
  "language": "en_US",
  "category": "utility",
  "parameter_format": "named",
  "components": [
    {
      "type": "body",
      "text": "Thank you, {{first_name}}! Your order number is {{order_number}}.",
      "example": {
        "body_text_named_params": [
          { "param_name": "first_name",   "example": "Pablo" },
          { "param_name": "order_number", "example": "860198-230332" }
        ]
      }
    }
  ]
}
```

**Facts that drive the design:**

| Fact | Source | Consequence here |
| --- | --- | --- |
| `parameter_format` is documented as `named` / `positional` in creation docs, and as the enum `{NAMED, POSITIONAL}` in the Graph API reference | Both pages | Recording must be **case-insensitive** (FR-002). The spec's assumption is confirmed, not assumed. |
| "If the `parameter_format` property is omitted, the template will use positional formatting" | Custom marketing templates | Omitting the key on a positional create keeps today's request byte-identical (FR-026, SC-008). |
| Named parameters must be "unique, single strings, composed of lowercase characters and underscores, wrapped in double curly brackets" | Template fundamentals | The naming rule for FR-024. Note it says *characters and underscores* — see the digits decision below. |
| "Example values in template creation payloads and real values in template send payloads can appear in any order" | Template fundamentals | Meta does **not** treat `body_text_named_params` as ordered. Only the body carries order — which is exactly why FR-011 makes the body the declared set. |
| Body text maximum is 1024 characters | Template components | `TemplateTranslation.body` is `max_length=2048`, comfortably sufficient. No change needed. |
| `header_text_named_params` exists with the same `{param_name, example}` shape | Template components | Out of scope this release, but it must be **skipped explicitly** by `extract_body_example`, not merely unhandled. |

### Graph API version timeline

Verified against Meta's Graph API changelog and versions table on 2026-09-17.

| Version | Released | Expires | Runway from today |
| --- | --- | --- | --- |
| `v16.0` (**current default**) | 2023-02-02 | **2025-05-14 — already expired** | none |
| `v23.0` (the spec's floor) | 2025-05-29 | 2027-10-08 | ~12.7 months |
| `v24.0` | 2025-10-08 | 2028-02-18 | ~17 months |
| `v25.0` | 2026-02-18 | 2028-07-29 | ~22.4 months |
| `v26.0` (latest) | 2026-07-29 | TBD | unknown |

Meta's rule: a version remains usable for at least two years, expiring two years after the *next* version
ships. Calls to an expired version are served by the next oldest usable version.

**The finding that matters most**: `v16.0` expired on 2025-05-14. This service's template calls are
therefore already being served by a version Meta chose, not one this service pinned. The version raise is
not only a missing-capability fix — it is re-pinning an unpinned production dependency.

---

## Decision 1 — Pin Graph API `v25.0`, scoped to template *methods*

**Decision**: `WHATSAPP_TEMPLATE_VERSION` defaults to `v25.0`. `TemplatesRequests` methods build URLs
from a `template_api_url` property that returns `settings.WHATSAPP_TEMPLATE_API_URL`. `BASE_URL` is
**not** overridden. Every other Meta client class, and every non-template method on `FacebookClient`,
keeps `FacebookAuthorization.BASE_URL` → `WHATSAPP_API_URL`.

**Rationale**:

- It clears the `v23.0` floor with room to spare, and Meta demonstrates `parameter_format` and
  `body_text_named_params` on `v23.0` and later, so the capability is unambiguously present.
- Its **expiry is already published** (2028-07-29), which `v26.0`'s is not. FR-040 requires the fleet-wide
  alignment to be tracked and owned; a tracked item needs a dated deadline, and only a version with a
  published expiry provides one.
- ~22 months of runway means this service will not need a second version change inside the rollout window
  of the five-repository product change.
- One release behind the latest is the deliberate stability position: `v26.0` is seven weeks old, and this
  is a defect fix on a live authoring path, not a place to absorb a new version's quirks.

**Alternatives considered**:

| Option | Rejected because |
| --- | --- |
| `v23.0` (the floor) | ~12.7 months of runway. The change would need repeating inside a year, on the same code, for no benefit. |
| `v24.0` | ~17 months. Strictly dominated by `v25.0` — same class of change, less runway, no stability advantage since both are past their initial-adoption period. |
| `v26.0` (latest) | Newest and least battle-tested, and its expiry is TBD so FR-040 could not be given a deadline. Revisit at the fleet-wide alignment, when a `v26`/`v27` expiry will be published. |
| Raise `WHATSAPP_VERSION` globally | Moves ~30 endpoints across catalogs, the VTEX product batch pipeline, commerce settings, phone numbers, profile, OAuth, credit sharing and onboarding in one step. Resolved against by the spec's Clarification Q1 (FR-039, FR-040). |

**Scoping mechanism** — verified by reading `marketplace/clients/facebook/client.py`:

`FacebookAuthorization.BASE_URL` (line 26) is a class attribute read through the `get_url` property
(line 35). Nine classes inherit it. `TemplatesRequests` (line 233) owns **every** template Graph endpoint
and nothing else:

| Method | Endpoint |
| --- | --- |
| `create_template_message` | `POST /{waba_id}/message_templates` |
| `create_library_template_message` | `POST /{waba_id}/message_templates` |
| `list_template_messages` | `GET /{waba_id}/message_templates` |
| `update_template_message` | `POST /{message_template_id}` |
| `delete_template_message` | `DELETE /{waba_id}/message_templates` |
| `get_template_namespace` | `GET /{waba_id}/message_templates?fields=message_template_namespace` |
| `get_template_analytics` | `GET /{waba_id}/template_analytics` |
| `enable_template_insights` | `POST /{waba_id}` |

Each of those methods currently interpolates `self.get_url`. They switch to `self.template_api_url`.
Catalog, phone, profile, OAuth and onboarding methods keep `self.get_url`. Template namespace, analytics
and insights move too: they are template surfaces and are *not* in the set SC-009 protects, so this is
consistent with the requirement rather than a side effect to apologise for.
`enable_template_insights` posts to the bare WABA node, which is version-stable.

**Why not override `BASE_URL` on `TemplatesRequests`.** `FacebookClient` (line 642) mixins
`CatalogsRequests` then `TemplatesRequests`. C3 linearization therefore finds `TemplatesRequests` before
`FacebookAuthorization`. A class-level `BASE_URL` on `TemplatesRequests` would make
`FacebookClient.BASE_URL` resolve to `v25.0`, and every production call constructed as
`FacebookClient(token)` — templates, catalogs, VTEX product batch, commerce, onboarding, photos — would
silently move. Production code uses `FacebookClient` for all of those. A distinct property is inherited
by `FacebookClient` but is only *read* by template methods, so catalog methods keep `get_url` → v16.

The eight sibling classes stay on `FacebookAuthorization.BASE_URL`: `CatalogsRequests`,
`CloudProfileRequests`, `CallingRequests`, `PhoneNumbersRequests`, `PhotoAPIRequests`,
`BusinessMetaRequests`, `BusinessVerificationRequests`, and `FacebookClient` itself for non-template
methods.

Also unchanged, verified: `core/types/channels/whatsapp/apis.py` and
`core/types/channels/whatsapp_base/requests/facebook.py` build WABA-info URLs from `WHATSAPP_VERSION`.
Those are on-premises WABA surfaces, not template create/update/list, so they stay where they are.

**Scoping alternatives rejected**:

| Option | Rejected because |
| --- | --- |
| Override `BASE_URL` on `TemplatesRequests` | `FacebookClient` MRO leaks it onto every mixed-in surface (FR-039, SC-009) |
| Override `get_url` on `TemplatesRequests` | Same MRO leak — `FacebookClient.get_url` would resolve there too |
| Pin `FacebookClient.BASE_URL` back to `WHATSAPP_API_URL` and still override `TemplatesRequests.BASE_URL` | Template methods on a `FacebookClient` instance would then stay on v16, undoing FR-038 |

**Failure mode required by the spec's edge case**: when Meta rejects a create because the configured
version does not support `parameter_format`, the error must surface as a configuration error naming the
unsupported capability, not as a template validation error. Handled in the authoring path by inspecting
Meta's error for the unsupported-parameter signature and re-raising with an explicit message.

---

## Decision 2 — Schema on `TemplateTranslation`

**Decision**: three columns — `parameter_format` (nullable `CharField`), `body_named_params`
(`JSONField(default=list)`), `parameter_anomaly` (nullable `JSONField`). `NULL` on `parameter_format` *is*
the "format not yet known" state. Migration `0014`, depending on `0013_auto_20260410_1837`.

Full field semantics, state machine and transitions are in [`data-model.md`](./data-model.md). The
research decisions behind them:

**Why `NULL` rather than a sentinel string or a separate boolean**

Three states are required (FR-014, FR-015). A nullable column expresses them in one field. `NULL` means
"this service has not been told the format by Meta", which is a true and useful statement about every
pre-existing row — so the migration needs no backfill, and reconciliation's job is exactly "turn NULLs into
values". A `"UNKNOWN"` sentinel would carry the same information at the cost of a data migration over the
whole table, which NFR-005 argues against. A separate `format_known` boolean would allow the illegal state
`(format_known=False, parameter_format="NAMED")`.

The rest of `TemplateTranslation` already uses `null=True` for `status`, `body`, `footer`,
`variable_count`, `language`, `country` and `message_template_id`, so this matches the file.

**Why one ordered JSON list rather than `ArrayField(names)` + `JSONField(examples)`**

FR-011 requires storing an example only for the names Meta actually supplied one for, which means the
name→example relation is partial. Two parallel fields make "names and examples out of sync" a
representable state that nothing prevents; one ordered list of `{param_name, example}` makes it
unrepresentable. It also reproduces Meta's `body_text_named_params` shape exactly, so
`extract_template_data` emits it with no transformation at all — which is the single most regression-prone
function in this change, and the less it transforms, the less it can break.

Using Meta's key names (`param_name`, `example`) rather than local names (`name`, `value`) is deliberate
for the same reason.

**Why `ArrayField` was rejected for the names**

`body_example` is already an `ArrayField(CharField(max_length=255))` and the spec identifies it as
structurally unable to hold named pairs. Adding a second `ArrayField` beside it would carry the same
255-character ceiling into example values for no benefit; `JSONB` has no such limit and satisfies NFR-007's
"full character range Meta accepts, without transformation" without a length trap.

**Why the anomaly is one `JSONField` rather than a code plus retained sets**

FR-011 requires the marking to *retain both observed name sets*. A `CharField` code alone loses the
evidence; a code plus two `ArrayField`s is three columns for one concept. One nullable `JSONB` object holds
the type and the evidence together, and `NULL` cleanly means "clean" — which is the check every read
surface and the reconciliation report performs.

**NFR-005 verification** (PostgreSQL 14):

- `ADD COLUMN` nullable with no default → catalog-only change, no table rewrite.
- `ADD COLUMN` with a **constant** default (`'[]'::jsonb`) → since PostgreSQL 11, stored in the catalog and
  materialised lazily; no table rewrite.
- No index is added, so no long-running build.
- The `ACCESS EXCLUSIVE` lock is held for the catalog update only — sub-millisecond on this table.
- No data migration, no `RunPython`. Existing rows read as
  `(parameter_format=None, body_named_params=[], parameter_anomaly=None)` the instant the migration lands.

**Alternative rejected**: a separate `TemplateParameter` model with a FK and an `order` column. It would
store an explicit ordinal per parameter, which is exactly the positional index FR-005 and SC-006 forbid
this service from computing or storing; it adds a join to every read and a cascade to every delete; and it
is a new model for data that is always read and written as a whole list. The constitution's simplicity
principle points the other way.

---

## Decision 3 — Where body parsing and validation live

**Decision**: a new pure module `marketplace/wpp_templates/parameters.py`. No Django, no DRF, no ORM, no
I/O, no logging of values. The serializer calls it for validation and payload assembly; the sync and
reconciliation use cases call it for recording.

**Rationale** — mapped to the constitution's layer table:

| Concern | Layer the constitution assigns it | Where it goes |
| --- | --- | --- |
| Body grammar, Meta's naming rule, format normalisation, FR-011 reconciliation | none of the four — it is pure domain knowledge with no I/O and no persistence | `parameters.py`, called from the layers below |
| Rejecting an invalid authoring submission with field-level errors | Input validation → **serializer** | `TemplateTranslationSerializer.validate_body()` etc., calling `parameters.py` |
| Deciding what gets written to the mirror for a synced template | Business logic → **use case** | `TemplateSyncUseCase`, calling `build_translation_parameters()` |
| Talking to Meta | **client** | `TemplatesRequests` (unchanged except for the signature) |

Putting the grammar in a pure module is what lets the same rule serve validation and recording without the
serializer importing a use case or the use case importing DRF. It is also the single highest-leverage
testing decision in the plan: the exhaustive accept/reject matrix for FR-022 through FR-025 runs as
`SimpleTestCase` with no database, no HTTP and no mocks.

**Why a new module rather than growing `template_helpers.py`**: `template_helpers.py` reads Meta's
`example` dict. `parameters.py` parses body text and enforces Meta's naming rule. Different inputs,
different reasons to change. `template_helpers.py` keeps its one existing function, made format-aware.

**Why not a use-case class for the mapping**: `build_translation_parameters()` performs no orchestration,
no ORM access and no I/O — it maps a Meta template dict to a value object. Wrapping it in a class with an
`execute()` would add a construction site and an injection point for nothing. The constitution's rule is
explicit: if a function suffices, a class must not be created.

**The digits question in Meta's naming rule** (FR-024)

Meta documents named parameters as "composed of lowercase characters and underscores" — which, read
literally, excludes digits. But the adjacent rule for *template names* says "lowercase alphanumeric
characters and underscores", so the omission may be loose prose rather than a constraint, and a name like
`item_2` is plausible in real templates.

FR-024 resolves this: the service must not impose a rule **stricter** than Meta's, and must surface Meta's
rejection when Meta proves stricter. The validation regex is therefore `^[a-z_][a-z0-9_]*$` —
deliberately *looser* than the literal documentation, so it cannot reject a name Meta would accept. If Meta
rejects `item_2`, FR-024's second clause carries Meta's reason back to the author unreinterpreted.

**The leading-character constraint comes from Flows, not from Meta.** Flows PR #876 validates names with
`NAMED_PARAM_RE = ^[A-Za-z_][A-Za-z0-9_]*$` and **silently skips** any name that fails it:

```python
for raw in PLACEHOLDER_RE.findall(text or ""):
    name = raw.strip()
    if not name or name.isdigit() or not NAMED_PARAM_RE.match(name):
        continue
```

A flat `^[a-z0-9_]+$` would accept `{{2fa_code}}`, which Meta may well accept too — and Flows would then
drop it from `parameter_names`, producing a short declared list and a parameter that never resolves at send
time. Requiring a leading letter or underscore closes that hole while staying looser than Meta's
documented rule, so FR-024 is satisfied in both directions.

**Character handling under NFR-007**: parameter names and example values are stored exactly as received.
Format strings are case-folded for comparison only (`"NAMED"` and `"named"` normalise to the same recorded
value); **parameter names are never case-folded, stripped or transformed**, and example values are never
validated for character range — only for presence.

---

## Decision 4 — `create_template_message` signature

**Decision**: add a trailing `parameter_format: Optional[str] = None` identically to all three layers. The
client includes the key in the payload only when it is not `None`.

**Rationale**: an optional trailing parameter keeps every existing call site valid, and omitting the key
for positional templates makes the positional request byte-identical to today's — which is what FR-026,
FR-041 and SC-008 actually demand. Meta documents an omitted `parameter_format` as positional, so sending
`"positional"` explicitly would change a live request for no behavioural gain and no way to verify the
change was harmless.

**`update_template_message` is deliberately not extended.** FR-019 forbids attempting to change a
template's format at Meta; the strongest enforcement is that the edit path has no parameter through which
to express one. This is worth stating in the plan because it is the kind of omission a later contributor
"fixes".

**Known test impact**: `marketplace/services/facebook/tests/test_services.py:73` defines a fake
`create_template_message(self, waba_id, name, category, components, language)`. It gains the new parameter.
This is a test double for an interface whose contract changed — legitimate and unavoidable, and distinct
from the tests Story 6 protects.

---

## Decision 5 — `extract_body_example` format-awareness

**Current behaviour** (`template_helpers.py`): iterates `example_data.values()` and flattens. Given
`{"body_text_named_params": [{"param_name": ..., "example": ...}, ...]}` it extends the list with **dict
objects**, which then hit `ArrayField(CharField(max_length=255))` — a write failure or a corrupted row, not
a graceful skip.

**Decision**: skip the named-parameter keys (`body_text_named_params`, `header_text_named_params`) by name;
leave every other key's handling byte-identical.

**Alternative rejected — an allowlist of `body_text`**: cleaner in the abstract, but the two call sites
pass different things. `template_sync.py:201` passes Meta's BODY `example` (keys `body_text` or
`body_text_named_params`), while `serializers.py:179` passes `validated_data["body"]["example"]`, an
author-supplied dict whose keys are not guaranteed. An allowlist would silently start dropping values that
are flattened today, which is exactly the class of positional behaviour change FR-041 and SC-008 forbid. A
denylist changes behaviour **only** for the keys that are broken today.

Also left alone deliberately: the existing `else: body_example.append(values)` branch, which appends
non-list values raw. It is untidy but it is today's positional behaviour, and this feature is not the place
to change it.

---

## Decision 6 — `variable_count` semantics

**Decision**:

| Format | `variable_count` |
| --- | --- |
| Named | number of declared parameter names |
| Positional | unchanged — literal `0` |
| Not yet known | `0` |

**Rationale**: FR-006 requires the declared-name count for named and "exactly as today" for positional.
"Today" is a literal `0` written unconditionally at three sites, verified: `serializers.py:189`,
`usecases/template_sync.py:223`, `usecases/template_library_creation.py:298`. Only the named branch
changes, and only in the sync and reconciliation paths.

The constant zero is not defended as correct — it is preserved because changing it is a positional
behaviour change this feature has no requirement to make, and the spec's assumptions note Flows computes
its own count from Meta's raw payload on the bulk path, so this value is consumed only by this service's
own read surfaces.

---

## Decision 7 — Read serializer shape

**Decision**: per translation, add `parameter_format`, `parameter_names` (ordered strings) and
`has_parameter_anomaly` (boolean). At template level, add a derived `parameter_format` that can be
`"NAMED"`, `"POSITIONAL"`, `"MIXED"` or `null`. Full response shapes in
[`contracts/read-surfaces.md`](./contracts/read-surfaces.md).

**Rationale**:

- **Names as bare strings, never objects with an index** — FR-005, FR-037 and SC-006 forbid publishing a
  positional index or slot number beside a named parameter. A list of strings has no field in which one
  could appear. The ordering is JSON array order, which is display metadata as FR-005 permits; no `index`,
  `position`, `slot` or `order` key is emitted anywhere. A test asserts this by recursively scanning the
  response for those keys.
- **Examples are not published on the read surfaces.** No requirement asks for them, and they are template
  metadata the author already possesses. YAGNI.
- **A boolean anomaly flag rather than the evidence blob** — FR-011 and FR-015 require that an anomalous or
  not-yet-known translation is not presented as ready for named dispatch. Publishing
  `parameter_format` plus `has_parameter_anomaly` lets a consumer decide with
  `parameter_format == "NAMED" and not has_parameter_anomaly`. The evidence itself is operator-facing and
  belongs in the reconciliation report and the logs.
- **A `ready_for_named_dispatch` boolean was rejected.** Dispatch readiness also depends on the parameter
  policy, which the spec assigns to Flows. Publishing a readiness verdict would mean this service asserting
  a judgement it does not own and cannot keep correct. It publishes facts.
- **`"MIXED"` at template level** — Story 5 scenario 4 and FR-008 forbid collapsing a disagreement between
  translations into one arbitrary value. Derivation: consider only translations whose format is known; if
  they agree, that value; if they disagree, `"MIXED"`; if none is known, `null`. `"MIXED"` is derived on
  read only — never stored, never sent to Meta, never accepted as input.

---

## Decision 8 — The authoring configuration flag

**Decision**: `WHATSAPP_NAMED_TEMPLATES_ENABLED = env.bool("WHATSAPP_NAMED_TEMPLATES_ENABLED", default=False)`.
It gates the authoring path only.

**Rationale**: FR-027 and the spec's assumption that downstream readiness gates authoring, not sync.
Recording a format Meta already assigned is additive — it makes the mirror more true and cannot make
delivery worse. *Creating* a named template at Meta is different: the moment it is approved it becomes
dispatchable into a pipeline whose delivery and channel layers may not yet substitute named placeholders,
which is the product spec's BD-016 rollout gate.

**Default `False`** so that deploying this service first is safe by construction. It is flipped to `True`
once Flows, mailroom, goflow and courier have shipped.

**Behaviour when off and a named body is submitted**: reject with a field-level error stating that named
templates are not enabled. Explicitly **not** a silent downgrade to positional — that would submit a
`{{nome}}` body under positional format, which Meta rejects with an opaque error, reproducing the exact
defect this feature exists to fix.

**Not gated**: sync, webhook, read surfaces, reconciliation, and positional authoring. Gating sync would
leave the mirror wrong for templates authored directly in Meta's panel, which Story 1 identifies as the
load-bearing path.

This is a configuration flag, which Constitution II warns against. It is justified because it is required
by FR-027, it has a defined removal condition (BD-016 satisfied), and it gates one branch of one code path
rather than threading through the design.

---

## Decision 9 — The two pre-existing defects

One **OUT**, one **IN**, after verification against Flows PR #876. Trade-offs are recorded in
[`plan.md`](./plan.md) §9 and Complexity Tracking #3.

**`extract_template_data` drops `body_example` — recommended OUT.** Verified at `utils.py:305–353`: the
function rebuilds the BODY component as `{"type": "BODY", "text": translation.body}` with no `example` key
at all, so the positional example array is dropped.

This was initially recommended IN, on the premise that Flows received examples from the daily bulk sync and
then had them cleared by the next status webhook. **The premise is false.** Flows'
`TemplateTranslation` model has no example field of any kind, and `update_local_templates` reads
`example` only inside `extract_parameter_names_from_components`, which looks exclusively at
`body_text_named_params`. Positional `example.body_text` is never read on either path.

Restoring it would therefore be a deliberate deviation from FR-041 and SC-008 in exchange for nothing. It
is dropped from this feature and recorded as debt. The function is still edited for FR-017 — only the
positional restoration is removed.

**The webhook app lookup — recommended IN.** Verified: `utils.py:183` is
`App.objects.filter(config__wa_waba_id=waba_id)`, while `tasks.py:36–38` is
`filter(code__in=["wpp", "wpp-cloud"]).filter(Q(config__wa_waba_id=waba_id) | Q(config__waba__id=waba_id))`.
`wpp` apps store the WABA at `config.waba.id` — confirmed by `views.py:128`, which reads
`instance.app.config.get("waba").get("id")` for the `wpp` code path. Those apps are synced and can hold
named templates, but no webhook ever reaches them.

**Deliberately not extracted into a shared helper.** The two lookups differ in more than the `Q`: the sync
helper also filters by app code and excludes apps with `ignores_meta_sync`. A webhook is Meta telling this
service something, and it should not be dropped because scheduled sync was disabled after a token error.
Constitution III requires duplication to be real before extraction; here the two call sites want different
things, so mirroring the `Q` is correct and extracting would force a false commonality.

**Benefit revised downward.** Flows' `NAMED_TEMPLATE_CHANNEL_TYPES` is `{"WAC", "WCD"}`, which excludes
on-premises WhatsApp — exactly the `config.waba.id` population this fix reaches. Those apps therefore
cannot dispatch named templates downstream regardless of what this service records. The fix stays because
it corrects webhook coverage generally and keeps our own mirror and read surfaces true for that app
population, but it is no longer load-bearing for named dispatch.

---

## Decision 12 — Cross-repository verification against Flows

Verified against [`weni-ai/flows` PR #876](https://github.com/weni-ai/flows/pull/876), branch
`feat/named-template-variables`, head `6f0b9d9`, plus the Flows code that PR does not modify but our
payloads reach (`temba/templates/views.py`, `temba/templates/serializers.py`,
`temba/utils/whatsapp/tasks.py`).

### The FR-017 gate is closed

Both Flows endpoints funnel into the same parser, and the request serializer strips nothing:

```python
# temba/templates/serializers.py
class TemplateSyncSerializer(serializers.Serializer):
    webhook = serializers.DictField(required=False)
    template_data = serializers.DictField(required=True)   # plain DictField — nothing is stripped
    template_name = serializers.CharField(required=True)
```

```python
# temba/templates/views.py
def partial_update(self, request, pk):                       # bulk PATCH
    update_local_templates(channel, request.data.get("data"))

def _handle_template_sync(self, validated_data, channel):    # webhook POST
    update_local_templates(channel, [validated_data.get("template_data")], True)
```

No outstanding cross-repository confirmation remains for this feature.

### The webhook regression risk is smaller than the spec assumed

`_handle_template_sync` calls `update_local_templates` **only when the template does not already exist**
in the org. For an existing template it calls `update_template_sync`, which dispatches to
`update_template_status` or `update_template_category` — both of which write only `status` or
`category` and never re-read `template_data`.

So a routine status webhook cannot clear a recorded `parameter_format` or `parameter_names` in Flows, and
the product spec's BD-015 framing does not hold against this implementation. FR-017 remains required for a
narrower window: the **first** webhook for a template Flows has not yet seen does go through
`update_local_templates`, and without `parameter_format` that template lands positional in Flows until the
next daily bulk sync corrects it.

This changes the severity of Story 2, not its scope. The same code change is still needed and is still
worth testing across all three event types.

### Divergences owned by Flows

| Divergence | Evidence | Position |
| --- | --- | --- |
| Name ordering comes from examples, not the body | `extract_parameter_names_from_components` iterates `body_text_named_params` first, then appends body names not already seen. Meta documents example order as arbitrary | Cosmetic — resolution is name-keyed. We keep body order per FR-004 |
| FR-011 mismatch yields a union | Body `{{nome}} {{cota}}` + examples `nome`/`quota` → `["nome", "quota", "cota"]`. The phantom `quota` still passes `assert_named_template_ready` | Our webhook path omits the example block for anomalous translations, so Flows falls back to body names and agrees. The bulk path cannot be fixed here — FR-013 forbids reshaping Meta's payload |
| Format stored at template level | `Template.parameter_format` vs `TemplateTranslation.parameter_names`; `get_or_create` lets the last-synced translation overwrite the template-level format, and nothing guards format disagreement | Our per-translation model with derived `"MIXED"` is strictly more correct. No change here |
| No third format state | `Template.parameter_format` defaults to `"positional"` | Our omitted key flattens to positional downstream. Acceptable — the library path's format is resolved by our post-creation sync and converges on the next bulk sync |

---

## Decision 10 — Reconciliation design

**Decision**: management command `reconcile_template_parameters` driving
`TemplateParameterReconciliationUseCase`, running synchronously, reusing the existing per-WABA TTL locks,
pacing from the existing drain budget, storing progress in Redis, and emitting structured logs plus one CSV
artifact. Full CLI contract in [`contracts/reconciliation-cli.md`](./contracts/reconciliation-cli.md).

**Existing infrastructure it reuses** (verified):

| Facility | Location | Reused how |
| --- | --- | --- |
| Per-WABA TTL lock | `core/pacing/ttl.py` — `is_recently_synced(key)`, `mark_synced(key, ttl_seconds)`; key `sync-whatsapp-templates-lock-waba:{waba_id}` | Same key namespace. If the lock is held, reconciliation **skips** the WABA (does not write concurrently), does not mark it done, and records a WABA-level `skipped_recent_sync` (FR-032, Story 4 scenario 5) |
| Pace | `settings.META_SYNC_TEMPLATES_DRAIN_BUDGET`, default 30/minute | Inter-WABA sleep of `60 / budget` seconds, so Meta sees the same request rate as the scheduled path |
| Recording | `TemplateSyncUseCase.sync_templates(templates=...)` | Reconciliation applies Meta's list through the **same** code path as Story 1, so convergence, in-place name replacement and the absence of duplicate rows are structural, not re-implemented (FR-031, Story 4 scenarios 1/3) |
| Progress map | `TemplateLibraryStatusUseCase` pattern — `get_redis_connection()`, JSON value, `ex=60*60*24` | `template_param_reconcile:progress`, same shape and TTL, so an interrupted run resumes (FR-031, Story 4 scenario 4) |
| WABA→apps resolution | `tasks.py::_apps_for_waba` | Reused directly, including its `ignores_meta_sync` exclusion — which is what lets skipped apps be reported as unclassifiable rather than counted as classified |
| Command style | `event_driven/management/commands/edaconsume.py` — the repository's only precedent | `BaseCommand` with `add_arguments` and `handle`; the command is thin and delegates to the use case |

**Why synchronous rather than through the paced queue**: the beat entry at `settings.py:454` hardcodes
`item_task_name: "task_sync_whatsapp_templates_item"`, so the existing drain can only dispatch the sync
task. Routing reconciliation through a queue would require a second queue key plus a second permanent beat
schedule — standing infrastructure for a one-time capability, against FR-030's intent — and asynchronous
execution makes FR-033's single exportable artifact impossible, since the command would exit before the
work happened. The pacing and locking that FR-032 actually cares about are reused regardless of who calls
them.

**Report format: CSV, one row per translation.** An operator "acting on" this report means filtering by
category and counting, which is what SC-010 asks for — a measured count of the broken fleet. A fixed CSV
column set makes the size predictable for an account with thousands of templates (NFR-004) and opens in any
spreadsheet. JSON Lines was the alternative; it is richer but needs tooling to count, and the richness is
not needed because the anomaly evidence fits two delimited columns.

**Classification requires a pre-state snapshot.** FR-029's "recorded with a named body and no parameters"
is a statement about the row *before* reconciliation writes to it. The use case therefore captures
`(body, parameter_format, body_named_params, variable_count)` per translation, applies Meta's list, and
then classifies by comparing. The five categories FR-034 requires are kept in one `category` column, with
`previously_broken` as a **separate boolean column** — a template can be both broken-before and
corrected-now, and collapsing that into one column would conflate categories FR-034 requires kept apart.

---

## Decision 11 — Test strategy

**Decision**: weight the suite toward the pure module, mock Meta and Flows at the client boundary, inject a
fake Redis, and never touch a real provider.

**Coverage economics**: `.coveragerc` already omits `marketplace/clients/*`, `marketplace/interfaces/*`,
`*migrations/*`, `*urls.py*` and `marketplace/settings.py`. So the client signature change, the interface
change and the migration carry **no coverage cost**. The code that does count is `parameters.py` (pure,
exhaustively testable), the sync recording branch, `extract_template_data`, the serializer validation
branch, the read serializer, and the reconciliation use case. Every one of those is testable without a
network, which is why the 75% floor is comfortably clear rather than nervously met.

| Target | Base class | What it covers |
| --- | --- | --- |
| `parameters.py` | `SimpleTestCase` | Table-driven matrix: format detection, case normalisation, unrecognised values, mixed bodies, duplicates, naming rule incl. digits and non-ASCII rejection, missing examples, zero placeholders, literal braces, FR-011 body-vs-examples divergence, `MISSING_NAMED_EXAMPLE`, `DUPLICATE_BODY_PARAM_NAME`, `POSITIONAL_FORMAT_NAMED_BODY` |
| `extract_body_example` | existing `test_utils.py` class | Named keys skipped; positional output byte-identical to today (regression assertion) |
| `TemplateSyncUseCase` | `TestCase` (needs the DB for `get_or_create`) | Story 1 scenarios 1–10 plus the three remaining anomaly types: named, positional, absent key, `"NAMED"` case variant, unrecognised value, disagreement, zero placeholders, empty named example, duplicate body name from Meta, positional format with a named body, in-place name change, shared WABA. `TemplateService` and `FlowsClient` mocked. Capture INFO and assert no example string — including the positional `body_example` values currently interpolated by the post-save log at `template_sync.py:226-229` |
| `extract_template_data` | `test_utils.py` | Named format and examples carried; anomalous translations carry the format but no example block; positional payload gains only `parameter_format`; Story 2 scenarios 1–4 and 6 |
| Webhook processor | `test_utils.py` | Format and names preserved across all three event types; `template_data` asserted only on the two events that post to Flows; gallery re-sync (scenario 5) depends on Story 1 recording; widened lookup finds an app configured at `config.waba.id` |
| Authoring serializer | `test_serializers.py` | Accept: named payload asserts `create_template_message` called with `parameter_format="named"` and a correct `body_text_named_params`. Reject: mixed / duplicate / bad name / missing example each assert a field-level error, `create_template_message` **not called**, and zero rows created. Positional asserts no `parameter_format` kwarg |
| Read surfaces | `test_views.py` (`APIBaseTestCase`) | Named, positional, not-yet-known and mixed-translation templates; recursive assertion that no `index` / `position` / `slot` / `order` key appears anywhere in the response (SC-006) |
| Reconciliation use case | `TestCase`, injected fake Redis + mocked service | Five translation categories kept distinct, `previously_broken` detection, resume from partial progress, idempotent second run producing an identical report, TTL-lock skip (`skipped_recent_sync`, WABA not in `done_waba_ids`), pacing via injected `sleep`, unclassifiable WABA |
| Reconciliation command | `TestCase` via `call_command` with the use case patched | Argument parsing, artifact written, exit code |
| Authoring flag | `override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=...)` | Off rejects a named body with a field-level error and makes no Meta call; on permits it; positional unaffected either way |
| Version scoping | new `test_template_api_version.py` | On a `FacebookClient` instance, template methods hit `WHATSAPP_TEMPLATE_API_URL` and a catalog method hits `WHATSAPP_API_URL`; `"BASE_URL" not in TemplatesRequests.__dict__`; sibling classes still resolve to `WHATSAPP_API_URL` (SC-009) |

**Isolation rules applied**: Redis is injected (`redis_conn` constructor argument defaulting to
`get_redis_connection()`), never reached; `CACHES` is overridden to `LocMemCache` in any test that touches
the Django cache; Meta and Flows are patched at `TemplateService` / `FlowsClient`; no test constructs a
real HTTP session.

**A note on `BASE_URL` and `override_settings`**: `FacebookAuthorization.BASE_URL` is bound at
class-definition time, following the existing pattern at `client.py:26`. `override_settings` therefore will
not affect sibling class URLs. `template_api_url` is a property that reads `settings` at call time, so it
*is* override-friendly; T010 still asserts against `settings.WHATSAPP_TEMPLATE_API_URL` directly and must
not restructure the client around `BASE_URL` to make a test pass.

---

## Summary of resolved unknowns

| Unknown from the spec | Resolution |
| --- | --- |
| Exact Graph API version at or above `v23.0` (FR-038) | `v25.0` — expires 2028-07-29, ~22 months of runway, published expiry date, one release behind latest |
| How to scope the version (FR-039) | `template_api_url` property on `TemplatesRequests` methods. Do **not** override `BASE_URL` — `FacebookClient` MRO would leak it onto catalogs and commerce |
| Schema for format, names, examples, unknown state and anomaly | Three columns; `NULL` format is the third state; ordered JSON list in Meta's own shape; one JSON anomaly object |
| Where parsing and validation live | Pure `parameters.py`; serializer validates, use cases record |
| `create_template_message` signature | Trailing `parameter_format=None`; key omitted from the payload when `None`; `update_template_message` unchanged |
| `extract_body_example` format-awareness | Skip named keys by name; every other key byte-identical |
| `variable_count` semantics | Declared-name count for named; literal `0` preserved for positional and not-yet-known |
| Read shape | Per-translation format + ordered names + anomaly boolean; derived template-level format with `"MIXED"` |
| Authoring flag | `WHATSAPP_NAMED_TEMPLATES_ENABLED`, default `False`, authoring path only, rejects rather than downgrades |
| The two pre-existing defects | Webhook app lookup **IN**; the `body_example` restoration **OUT** — Flows has no consumer for it (Decision 12) |
| Alignment with Flows PR #876 | Wire contract confirmed; FR-017 gate closed; three plan corrections applied (Decision 12) |
| Test strategy | Pure-module-weighted, client-boundary mocks, injected Redis, 75% floor cleared with margin |
