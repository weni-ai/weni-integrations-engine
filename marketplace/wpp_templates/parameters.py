import re
from dataclasses import dataclass
from typing import List, Mapping, Optional, Tuple

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

    parameter_format: Optional[str]
    body_named_params: List[dict]
    variable_count: int
    anomaly: Optional[dict]


def normalize_parameter_format(raw: Optional[str]) -> Tuple[Optional[str], bool]:
    """Case-insensitively map Meta's value to NAMED/POSITIONAL.

    Returns (format, recognised). An absent value yields (POSITIONAL, True) per Meta's documented
    default; an unrecognised value yields (POSITIONAL, False) so the caller records an anomaly.
    Never inspects body text (FR-003).
    """
    if raw is None:
        return PARAMETER_FORMAT_POSITIONAL, True
    normalised = raw.strip().lower()
    if not normalised:
        return PARAMETER_FORMAT_POSITIONAL, True
    if normalised == "named":
        return PARAMETER_FORMAT_NAMED, True
    if normalised == "positional":
        return PARAMETER_FORMAT_POSITIONAL, True
    return PARAMETER_FORMAT_POSITIONAL, False


def extract_named_placeholders(body: str) -> List[str]:
    """Names in body order, duplicates preserved so the caller can detect them."""
    if not body:
        return []
    names = []
    for token in NAMED_PLACEHOLDER_RE.findall(body):
        if token.isdigit():
            continue
        names.append(token)
    return names


def extract_positional_placeholders(body: str) -> List[str]:
    """Positional tokens in body order."""
    if not body:
        return []
    return POSITIONAL_PLACEHOLDER_RE.findall(body)


def detect_authoring_format(body: str) -> Optional[str]:
    """Format implied by an author's body, BEFORE the template exists at Meta (FR-020).

    Returns NAMED, POSITIONAL, or None when the body has no placeholders. Must never be called for a
    template Meta has already described (FR-003).
    """
    named = extract_named_placeholders(body or "")
    positional = extract_positional_placeholders(body or "")
    if named and not positional:
        return PARAMETER_FORMAT_NAMED
    if positional and not named:
        return PARAMETER_FORMAT_POSITIONAL
    return None


def validate_parameter_name(name: str) -> bool:
    """Meta's documented rule, loosened to admit digits but not as a leading character.

    Meta documents 'lowercase characters and underscores' while documenting template names as
    'lowercase alphanumeric characters and underscores', so digits are admitted rather than risk a
    false rejection (FR-024). A leading digit is rejected because Flows drops such names silently,
    which would yield a template whose parameters never resolve at send time.
    """
    return bool(name) and PARAMETER_NAME_RE.fullmatch(name) is not None


def build_named_example_payload(
    names: List[str], examples: Mapping[str, str]
) -> List[dict]:
    """Meta's body_text_named_params shape for an authoring submission."""
    return [{"param_name": name, "example": examples[name]} for name in names]


def build_translation_parameters(meta_template: dict) -> TranslationParameters:
    """Map one Meta list-response template to what the mirror records.

    The single source of truth for recording. Called by TemplateSyncUseCase and by
    TemplateParameterReconciliationUseCase so the two cannot diverge.
    """
    raw_format = meta_template.get("parameter_format")
    recorded_format, recognised = normalize_parameter_format(raw_format)
    body = _body_text(meta_template)
    if recorded_format == PARAMETER_FORMAT_NAMED:
        return _named_recording(body, meta_template)
    return _positional_recording(body, recognised, raw_format)


def _body_text(meta_template: dict) -> str:
    return _find_body_component(meta_template).get("text") or ""


def _find_body_component(meta_template: dict) -> dict:
    for component in meta_template.get("components") or []:
        if not isinstance(component, dict):
            continue
        if str(component.get("type", "")).upper() == "BODY":
            return component
    return {}


def _body_named_example_entries(meta_template: dict) -> List[dict]:
    example = _find_body_component(meta_template).get("example") or {}
    if not isinstance(example, dict):
        return []
    entries = example.get("body_text_named_params") or []
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _example_lookup(entries: List[dict]) -> Tuple[List[str], dict]:
    names = []
    by_name = {}
    for entry in entries:
        name = entry.get("param_name")
        if name is None:
            continue
        names.append(name)
        by_name[name] = entry.get("example")
    return names, by_name


def _stored_example(raw):
    if raw is None or raw == "":
        return None
    return raw


def _build_named_params(body_names: List[str], example_by_name: dict) -> List[dict]:
    return [
        {"param_name": name, "example": _stored_example(example_by_name.get(name))}
        for name in body_names
    ]


def _has_duplicate_names(names: List[str]) -> bool:
    return len(names) != len(set(names))


def _named_recording(body: str, meta_template: dict) -> TranslationParameters:
    body_names = extract_named_placeholders(body)
    example_entries = _body_named_example_entries(meta_template)
    example_param_names, example_by_name = _example_lookup(example_entries)
    body_named_params = _build_named_params(body_names, example_by_name)

    if not body_names:
        return TranslationParameters(
            parameter_format=PARAMETER_FORMAT_NAMED,
            body_named_params=[],
            variable_count=0,
            anomaly=None,
        )

    anomaly = None
    if _has_duplicate_names(body_names):
        anomaly = {
            "type": "DUPLICATE_BODY_PARAM_NAME",
            "body_param_names": list(body_names),
        }
    elif example_param_names and set(body_names) != set(example_param_names):
        anomaly = {
            "type": "BODY_EXAMPLE_NAME_MISMATCH",
            "body_param_names": list(body_names),
            "example_param_names": list(example_param_names),
            "reported_format": meta_template.get("parameter_format"),
        }
    elif any(_stored_example(example_by_name.get(name)) is None for name in body_names):
        anomaly = {
            "type": "MISSING_NAMED_EXAMPLE",
            "body_param_names": list(body_names),
        }

    return TranslationParameters(
        parameter_format=PARAMETER_FORMAT_NAMED,
        body_named_params=body_named_params,
        variable_count=len(body_named_params),
        anomaly=anomaly,
    )


def _positional_recording(
    body: str, recognised: bool, raw_format
) -> TranslationParameters:
    if not recognised:
        return TranslationParameters(
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
            body_named_params=[],
            variable_count=0,
            anomaly={
                "type": "UNRECOGNISED_FORMAT",
                "reported_format": raw_format,
            },
        )

    named = extract_named_placeholders(body)
    anomaly = None
    if named:
        anomaly = {
            "type": "POSITIONAL_FORMAT_NAMED_BODY",
            "body_param_names": named,
        }
    return TranslationParameters(
        parameter_format=PARAMETER_FORMAT_POSITIONAL,
        body_named_params=[],
        variable_count=0,
        anomaly=anomaly,
    )
