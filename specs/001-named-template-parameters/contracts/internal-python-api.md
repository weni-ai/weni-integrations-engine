# Contract — Internal Python interfaces

**Scope**: signatures that cross a layer boundary inside this service and must therefore stay in step.

---

## 1. `parameters.py` — the pure module

**Location**: `marketplace/wpp_templates/parameters.py`

**Hard constraints**: no Django import, no DRF import, no ORM access, no I/O, no logging of example values.
Every function is deterministic (NFR-008).

```python
PARAMETER_FORMAT_NAMED = "NAMED"
PARAMETER_FORMAT_POSITIONAL = "POSITIONAL"

NAMED_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
POSITIONAL_PLACEHOLDER_RE = re.compile(r"\{\{\s*(\d+)\s*\}\}")

# Leading letter or underscore required. Meta documents only "lowercase characters and underscores",
# so this stays looser than Meta's rule (FR-024) while remaining compatible with Flows, which
# validates names as ^[A-Za-z_][A-Za-z0-9_]*$ and SILENTLY SKIPS anything that fails.
PARAMETER_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass(frozen=True)
class TranslationParameters:
    """What the mirror records for one translation. Produced by build_translation_parameters()."""
    parameter_format: Optional[str]      # "NAMED" | "POSITIONAL" | None
    body_named_params: List[dict]        # [{"param_name": str, "example": Optional[str]}]
    variable_count: int
    anomaly: Optional[dict]              # see data-model.md


def normalize_parameter_format(raw: Optional[str]) -> Tuple[Optional[str], bool]:
    """Case-insensitively map Meta's value to NAMED/POSITIONAL.

    Returns (format, recognised). An absent value yields (POSITIONAL, True) per Meta's documented
    default; an unrecognised value yields (POSITIONAL, False) so the caller records an anomaly.
    Never inspects body text (FR-003).
    """


def extract_named_placeholders(body: str) -> List[str]:
    """Names in body order, duplicates preserved so the caller can detect them."""


def extract_positional_placeholders(body: str) -> List[str]:
    """Positional tokens in body order."""


def detect_authoring_format(body: str) -> Optional[str]:
    """Format implied by an author's body, BEFORE the template exists at Meta (FR-020).

    Returns NAMED, POSITIONAL, or None when the body has no placeholders. Must never be called for a
    template Meta has already described (FR-003).
    """


def validate_parameter_name(name: str) -> bool:
    """Meta's documented rule, loosened to admit digits but not as a leading character.

    Meta documents 'lowercase characters and underscores' while documenting template names as
    'lowercase alphanumeric characters and underscores', so digits are admitted rather than risk a
    false rejection (FR-024). A leading digit is rejected because Flows drops such names silently,
    which would yield a template whose parameters never resolve at send time.
    """


def build_named_example_payload(
    names: List[str], examples: Mapping[str, str]
) -> List[dict]:
    """Meta's body_text_named_params shape for an authoring submission."""


def build_translation_parameters(meta_template: dict) -> TranslationParameters:
    """Map one Meta list-response template to what the mirror records.

    The single source of truth for recording. Called by TemplateSyncUseCase and by
    TemplateParameterReconciliationUseCase so the two cannot diverge.
    """
```

### Callers

| Caller | Functions used |
| --- | --- |
| `TemplateTranslationSerializer` | `detect_authoring_format`, `extract_named_placeholders`, `extract_positional_placeholders`, `validate_parameter_name`, `build_named_example_payload` |
| `TemplateSyncUseCase` | `build_translation_parameters` |
| `TemplateParameterReconciliationUseCase` | `build_translation_parameters`, `extract_named_placeholders` (pre-state defect detection) |

### Regex notes

- `NAMED_PLACEHOLDER_RE` admits uppercase so that a name breaking Meta's rule is **detected and reported**
  rather than invisible. Validation then rejects it (FR-024). A regex that only matched valid names would
  silently treat `{{Nome}}` as literal text.
- Literal curly braces that are not a placeholder must not match — `{ not a param }` and `{{ }}` produce no
  parameters (Edge Cases — Authoring).
- A body containing both a named and a positional match is mixed-format and is rejected (FR-022).

---

## 2. Meta template client, service and interface

The same signature in three files, which must change together.

```python
# marketplace/interfaces/facebook/interfaces.py
class TemplatesRequestsInterface(ABC):
    @abstractmethod
    def create_template_message(
        self,
        waba_id: str,
        name: str,
        category: str,
        components: list,
        language: str,
        parameter_format: Optional[str] = None,
    ) -> Dict[str, Any]: ...
```

```python
# marketplace/services/facebook/service.py
class TemplateService:
    def create_template_message(
        self, waba_id, name, category, components, language, parameter_format=None
    ) -> Dict[str, Any]:
        return self.client.create_template_message(
            waba_id=waba_id, name=name, category=category,
            components=components, language=language, parameter_format=parameter_format,
        )
```

```python
# marketplace/clients/facebook/client.py
class TemplatesRequests(FacebookAuthorization, RequestClient, TemplatesRequestsInterface):
    @property
    def template_api_url(self):
        return settings.WHATSAPP_TEMPLATE_API_URL

    def create_template_message(
        self, waba_id, name, category, components, language, parameter_format=None
    ) -> dict:
        payload = dict(name=name, category=category, components=components, language=language)
        if parameter_format:
            payload["parameter_format"] = parameter_format
        url = f"{self.template_api_url}/{waba_id}/message_templates"
        return self.make_request(url, method="POST", json=payload,
                                 headers=self._get_headers()).json()
```

| Rule | Reason |
| --- | --- |
| Trailing optional parameter defaulting to `None` | Every existing call site stays valid |
| Key omitted from the payload when `None` | A positional create stays byte-identical to today's request; Meta documents an omitted value as positional (FR-026, SC-008) |
| Value sent lowercase (`"named"`) | Matches Meta's creation documentation |
| URLs from `self.template_api_url`, never `self.get_url` or a `BASE_URL` override | `FacebookClient` MRO would leak a `BASE_URL` override onto catalogs and commerce (FR-039, SC-009) |
| `update_template_message` **unchanged** | FR-019 forbids changing a template's format at Meta; the strongest guarantee is having no parameter for it |
| `create_library_template_message` **unchanged** | Its payload carries `library_template_name`, not body text |

**Known test-double impact**: `marketplace/services/facebook/tests/test_services.py:73` defines a fake
`create_template_message(self, waba_id, name, category, components, language)` and gains the new parameter.

---

## 3. Recording call site in `TemplateSyncUseCase`

**Location**: `marketplace/wpp_templates/usecases/template_sync.py`

Replaces the unconditional `returned_translation.variable_count = 0` at line 223.

```python
parameters = build_translation_parameters(template)

returned_translation.body = body
returned_translation.body_example = body_example          # positional only, unchanged
returned_translation.footer = footer
returned_translation.status = template.get("status")
returned_translation.parameter_format = parameters.parameter_format
returned_translation.body_named_params = parameters.body_named_params
returned_translation.parameter_anomaly = parameters.anomaly
returned_translation.variable_count = parameters.variable_count
returned_translation.message_template_id = template.get("id")
returned_translation.save()
```

The existing `logger.info` immediately after `save()` (lines 226–229) interpolates
`body_example: {returned_translation.body_example}`. **Drop that interpolation** — remove the log or keep
only status and `message_template_id`. Do not log `body_named_params`. The `body_example` *assignment*
stays; only the log changes (FR-044, SC-011). T013 names this line; T014 asserts it is gone.

| Guarantee | How |
| --- | --- |
| In-place update, no duplicate rows (FR-012) | The existing `get_or_create` on `(template, language)` is unchanged |
| Positional unchanged | `parameters.variable_count` is `0` and `body_named_params` is `[]` for positional; `body_example` keeps its existing assignment |
| No extra Meta request (NFR-001) | `build_translation_parameters` reads the template dict already in hand |
| Anomalies observable (FR-043) | Logged with app UUID, project UUID, template name and `message_template_id`. **Example values are never logged** (FR-044, SC-011) |

---

## 4. `extract_body_example` — format-aware

**Location**: `marketplace/wpp_templates/template_helpers.py`

```python
NAMED_EXAMPLE_KEYS = frozenset({"body_text_named_params", "header_text_named_params"})


def extract_body_example(example_data: dict) -> list:
    body_example = []
    if not example_data:
        return body_example

    for key, values in example_data.items():
        if key in NAMED_EXAMPLE_KEYS:
            continue
        if isinstance(values, list) and values:
            if isinstance(values[0], list):
                body_example.extend(values[0])
            else:
                body_example.extend(values)
        else:
            body_example.append(values)

    return body_example
```

The loop changes from `.values()` to `.items()` purely so the key can be tested. Every non-named key is
handled byte-identically to today, including the `else: append(values)` branch. An allowlist of `body_text`
was rejected because the authoring path passes an author-supplied dict whose keys are not guaranteed, so
an allowlist would silently change today's positional behaviour (FR-041, SC-008).

Named examples never enter `body_example`, and positional examples never enter `body_named_params`
(FR-007).

---

## 5. Reconciliation use case

**Location**: `marketplace/wpp_templates/usecases/template_parameter_reconciliation.py`

```python
class TemplateParameterReconciliationUseCase:
    def __init__(
        self,
        redis_conn=None,                  # injected for tests; defaults to get_redis_connection()
        sync_use_case_factory=None,       # defaults to TemplateSyncUseCase
        apps_for_waba=None,               # defaults to tasks._apps_for_waba
        sleep=time.sleep,                 # injected so tests do not actually pace
        logger=None,
    ): ...

    def execute(
        self,
        waba_ids: Optional[List[str]] = None,
        app_uuids: Optional[List[str]] = None,
        dry_run: bool = False,
        restart: bool = False,
        limit: Optional[int] = None,
    ) -> ReconciliationResult: ...


@dataclass(frozen=True)
class ReconciliationResult:
    run_id: str
    rows: List[dict]                 # one per translation; see reconciliation-cli.md
    counters: Dict[str, int]         # per category
    resumed: bool

    def to_dict(self) -> dict: ...
```

| Constraint | Reason |
| --- | --- |
| Framework-agnostic — no `rest_framework` import | Constitution I |
| Every dependency injectable | Constitution IV; lets tests run with a fake Redis and no real sleeping |
| Applies Meta's list through `TemplateSyncUseCase.sync_templates(templates=...)` | Convergence, in-place updates and the absence of duplicates are structural, not reimplemented (FR-031) |
| Reuses `TTL_WHATSAPP_TEMPLATES` lock keys | Cannot double-hit Meta with the scheduled sync (FR-032) |
| Paces from `settings.META_SYNC_TEMPLATES_DRAIN_BUDGET` | Same request rate as the scheduled path (FR-032) |
| Progress at `template_param_reconcile:progress`, JSON, `ex=86400` | Mirrors `template_status:{app_uuid}`; makes a run resumable (FR-031) |

---

## 6. Settings

```python
# Template-scoped Graph API version — see contracts/meta-graph-templates.md
WHATSAPP_TEMPLATE_VERSION = env.str("WHATSAPP_TEMPLATE_VERSION", default="v25.0")
WHATSAPP_TEMPLATE_API_URL = urllib.parse.urljoin(
    env.str("WHATSAPP_API_URL", default="https://graph.facebook.com/"), WHATSAPP_TEMPLATE_VERSION
)

# Gates the named AUTHORING path only (FR-027). Sync, webhook, read and reconciliation are never
# gated: recording what Meta already reported is additive. Default off so this service can ship
# before Flows, mailroom, goflow and courier.
WHATSAPP_NAMED_TEMPLATES_ENABLED = env.bool("WHATSAPP_NAMED_TEMPLATES_ENABLED", default=False)
```

`WHATSAPP_VERSION` and `WHATSAPP_API_URL` are unchanged.

### Also to clean up in the files this feature touches

- `marketplace/wpp_templates/views.py:42` — `WHATSAPP_VERSION = settings.WHATSAPP_VERSION`, assigned and
  never read.
- `marketplace/wpp_templates/serializers.py:26` — the same dead assignment.
- `.coveragerc` — omits `marketplace/wpp_templates/requests.py`, a file that does not exist.
