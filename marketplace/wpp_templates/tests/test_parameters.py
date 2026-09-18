from django.test import SimpleTestCase

from marketplace.wpp_templates.parameters import (
    PARAMETER_FORMAT_NAMED,
    PARAMETER_FORMAT_POSITIONAL,
    TranslationParameters,
    build_named_example_payload,
    build_translation_parameters,
    detect_authoring_format,
    extract_named_placeholders,
    extract_positional_placeholders,
    normalize_parameter_format,
    validate_parameter_name,
)


def _meta_template(
    parameter_format="NAMED",
    body="",
    named_examples=None,
    extra_example=None,
    omit_format=False,
):
    example = {}
    if named_examples is not None:
        example["body_text_named_params"] = named_examples
    if extra_example:
        example.update(extra_example)
    body_component = {"type": "BODY", "text": body}
    if example:
        body_component["example"] = example
    template = {
        "id": "1234567890",
        "name": "order_update",
        "language": "pt_BR",
        "components": [body_component],
    }
    if not omit_format:
        template["parameter_format"] = parameter_format
    return template


class NormalizeParameterFormatTestCase(SimpleTestCase):
    def test_normalises_across_casings_absence_and_unrecognised_values(self):
        cases = (
            ("named", PARAMETER_FORMAT_NAMED, True),
            ("NAMED", PARAMETER_FORMAT_NAMED, True),
            ("Named", PARAMETER_FORMAT_NAMED, True),
            ("positional", PARAMETER_FORMAT_POSITIONAL, True),
            ("POSITIONAL", PARAMETER_FORMAT_POSITIONAL, True),
            (" Positional ", PARAMETER_FORMAT_POSITIONAL, True),
            (None, PARAMETER_FORMAT_POSITIONAL, True),
            ("", PARAMETER_FORMAT_POSITIONAL, True),
            ("SOMETHING_ELSE", PARAMETER_FORMAT_POSITIONAL, False),
            ("json", PARAMETER_FORMAT_POSITIONAL, False),
        )
        for raw, expected_format, recognised in cases:
            with self.subTest(raw=raw):
                self.assertEqual(
                    normalize_parameter_format(raw),
                    (expected_format, recognised),
                )


class BodyGrammarTestCase(SimpleTestCase):
    def test_extracts_named_positional_mixed_duplicate_and_literal_bodies(self):
        cases = (
            ("Olá {{nome}}, sua cota {{cota}}", ["nome", "cota"], []),
            ("Olá {{1}}, seu pedido {{2}}", [], ["1", "2"]),
            ("Olá {{nome}}, pedido {{1}}", ["nome"], ["1"]),
            ("Olá {{nome}}, tudo bem {{nome}}?", ["nome", "nome"], []),
            ("Olá, tudo bem?", [], []),
            ("{ not a param }", [], []),
            ("{{ }}", [], []),
            ("Olá {{ nome }}", ["nome"], []),
        )
        for body, named, positional in cases:
            with self.subTest(body=body):
                self.assertEqual(extract_named_placeholders(body), named)
                self.assertEqual(extract_positional_placeholders(body), positional)

    def test_detect_authoring_format_for_exclusive_bodies(self):
        cases = (
            ("Olá {{nome}}, sua cota {{cota}}", PARAMETER_FORMAT_NAMED),
            ("Olá {{1}}, seu pedido {{2}}", PARAMETER_FORMAT_POSITIONAL),
            ("Olá, tudo bem?", None),
            ("{ not a param }", None),
            ("{{ }}", None),
            ("Olá {{nome}}, pedido {{1}}", None),
        )
        for body, expected in cases:
            with self.subTest(body=body):
                self.assertEqual(detect_authoring_format(body), expected)


class ParameterNameRuleTestCase(SimpleTestCase):
    def test_accepts_lowercase_and_digits_after_a_letter(self):
        cases = (
            ("item_2", True),
            ("nome", True),
            ("cota", True),
            ("_leading_underscore", True),
            ("Nome", False),
            ("2fa_code", False),
            ("nôme", False),
            ("nome-x", False),
            ("", False),
        )
        for name, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(validate_parameter_name(name), expected)


class BuildNamedExamplePayloadTestCase(SimpleTestCase):
    def test_emits_meta_shape_in_body_order(self):
        payload = build_named_example_payload(
            ["nome", "cota"],
            {"cota": "3/12", "nome": "João"},
        )
        self.assertEqual(
            payload,
            [
                {"param_name": "nome", "example": "João"},
                {"param_name": "cota", "example": "3/12"},
            ],
        )


class BuildTranslationParametersTestCase(SimpleTestCase):
    def test_records_named_examples_in_body_order(self):
        result = build_translation_parameters(
            _meta_template(
                parameter_format="named",
                body="Olá {{nome}}, sua cota {{cota}}",
                named_examples=[
                    {"param_name": "cota", "example": "3/12"},
                    {"param_name": "nome", "example": "João"},
                ],
            )
        )
        self.assertEqual(
            result,
            TranslationParameters(
                parameter_format=PARAMETER_FORMAT_NAMED,
                body_named_params=[
                    {"param_name": "nome", "example": "João"},
                    {"param_name": "cota", "example": "3/12"},
                ],
                variable_count=2,
                anomaly=None,
            ),
        )

    def test_normalises_named_casings_and_defaults_absent_to_positional(self):
        cases = (
            ("named", PARAMETER_FORMAT_NAMED, True),
            ("NAMED", PARAMETER_FORMAT_NAMED, True),
            ("Named", PARAMETER_FORMAT_NAMED, True),
            ("positional", PARAMETER_FORMAT_POSITIONAL, False),
        )
        body = "Olá {{nome}}"
        examples = [{"param_name": "nome", "example": "João"}]
        for raw, expected_format, is_named in cases:
            with self.subTest(raw=raw):
                result = build_translation_parameters(
                    _meta_template(
                        parameter_format=raw,
                        body=body,
                        named_examples=examples if is_named else None,
                    )
                )
                self.assertEqual(result.parameter_format, expected_format)
                if is_named:
                    self.assertEqual(result.variable_count, 1)
                    self.assertIsNone(result.anomaly)
                else:
                    self.assertEqual(result.body_named_params, [])
                    self.assertEqual(result.variable_count, 0)

        omitted = build_translation_parameters(
            _meta_template(body="Olá {{1}}", omit_format=True)
        )
        self.assertEqual(omitted.parameter_format, PARAMETER_FORMAT_POSITIONAL)
        self.assertEqual(omitted.body_named_params, [])
        self.assertEqual(omitted.variable_count, 0)
        self.assertIsNone(omitted.anomaly)

    def test_unrecognised_format_never_inspects_the_body(self):
        result = build_translation_parameters(
            _meta_template(
                parameter_format="SOMETHING_ELSE",
                body="Olá {{nome}}, sua cota {{cota}}",
                named_examples=[
                    {"param_name": "nome", "example": "João"},
                    {"param_name": "cota", "example": "3/12"},
                ],
            )
        )
        self.assertEqual(result.parameter_format, PARAMETER_FORMAT_POSITIONAL)
        self.assertEqual(result.body_named_params, [])
        self.assertEqual(result.variable_count, 0)
        self.assertEqual(result.anomaly["type"], "UNRECOGNISED_FORMAT")
        self.assertEqual(result.anomaly["reported_format"], "SOMETHING_ELSE")

    def test_named_body_with_zero_placeholders_is_valid(self):
        result = build_translation_parameters(
            _meta_template(parameter_format="NAMED", body="Olá, tudo bem?")
        )
        self.assertEqual(result.parameter_format, PARAMETER_FORMAT_NAMED)
        self.assertEqual(result.body_named_params, [])
        self.assertEqual(result.variable_count, 0)
        self.assertIsNone(result.anomaly)

    def test_body_example_name_mismatch_keeps_body_names_and_both_sets(self):
        result = build_translation_parameters(
            _meta_template(
                parameter_format="NAMED",
                body="Olá {{nome}}, sua cota {{cota}}",
                named_examples=[
                    {"param_name": "nome", "example": "João"},
                    {"param_name": "quota", "example": "3/12"},
                ],
            )
        )
        self.assertEqual(result.parameter_format, PARAMETER_FORMAT_NAMED)
        self.assertEqual(
            result.body_named_params,
            [
                {"param_name": "nome", "example": "João"},
                {"param_name": "cota", "example": None},
            ],
        )
        self.assertEqual(result.variable_count, 2)
        self.assertEqual(result.anomaly["type"], "BODY_EXAMPLE_NAME_MISMATCH")
        self.assertEqual(result.anomaly["body_param_names"], ["nome", "cota"])
        self.assertEqual(result.anomaly["example_param_names"], ["nome", "quota"])

    def test_missing_named_example_stores_null(self):
        cases = (
            ("absent block", None, [{"param_name": "nome", "example": None}]),
            (
                "empty example value",
                [{"param_name": "nome", "example": ""}],
                [{"param_name": "nome", "example": None}],
            ),
        )
        for label, named_examples, expected_params in cases:
            with self.subTest(label=label):
                result = build_translation_parameters(
                    _meta_template(
                        parameter_format="NAMED",
                        body="Olá {{nome}}",
                        named_examples=named_examples,
                    )
                )
                self.assertEqual(result.parameter_format, PARAMETER_FORMAT_NAMED)
                self.assertEqual(result.body_named_params, expected_params)
                self.assertEqual(result.anomaly["type"], "MISSING_NAMED_EXAMPLE")
                self.assertIsNone(result.body_named_params[0]["example"])

    def test_duplicate_body_param_name_is_not_deduplicated(self):
        result = build_translation_parameters(
            _meta_template(
                parameter_format="NAMED",
                body="Olá {{nome}}, tudo bem {{nome}}?",
                named_examples=[{"param_name": "nome", "example": "João"}],
            )
        )
        self.assertEqual(result.parameter_format, PARAMETER_FORMAT_NAMED)
        self.assertEqual(
            result.body_named_params,
            [
                {"param_name": "nome", "example": "João"},
                {"param_name": "nome", "example": "João"},
            ],
        )
        self.assertEqual(result.variable_count, 2)
        self.assertEqual(result.anomaly["type"], "DUPLICATE_BODY_PARAM_NAME")
        self.assertEqual(result.anomaly["body_param_names"], ["nome", "nome"])

    def test_positional_format_with_named_body_does_not_infer_named(self):
        cases = (
            ("positional", False),
            (None, True),
        )
        for raw, omit_format in cases:
            with self.subTest(raw=raw, omit_format=omit_format):
                result = build_translation_parameters(
                    _meta_template(
                        parameter_format=raw,
                        body="Olá {{nome}}, sua cota {{cota}}",
                        omit_format=omit_format,
                    )
                )
                self.assertEqual(result.parameter_format, PARAMETER_FORMAT_POSITIONAL)
                self.assertEqual(result.body_named_params, [])
                self.assertEqual(result.variable_count, 0)
                self.assertEqual(result.anomaly["type"], "POSITIONAL_FORMAT_NAMED_BODY")
                self.assertEqual(result.anomaly["body_param_names"], ["nome", "cota"])

    def test_header_text_named_params_are_ignored(self):
        result = build_translation_parameters(
            _meta_template(
                parameter_format="NAMED",
                body="Olá {{nome}}",
                named_examples=[{"param_name": "nome", "example": "João"}],
                extra_example={
                    "header_text_named_params": [
                        {"param_name": "titulo", "example": "Promo"}
                    ]
                },
            )
        )
        self.assertEqual(
            result.body_named_params,
            [{"param_name": "nome", "example": "João"}],
        )
        self.assertIsNone(result.anomaly)
        header_only = build_translation_parameters(
            _meta_template(
                parameter_format="NAMED",
                body="Olá {{nome}}",
                extra_example={
                    "header_text_named_params": [
                        {"param_name": "nome", "example": "João"}
                    ]
                },
            )
        )
        self.assertEqual(
            header_only.body_named_params,
            [{"param_name": "nome", "example": None}],
        )
        self.assertEqual(header_only.anomaly["type"], "MISSING_NAMED_EXAMPLE")

    def test_mapping_is_deterministic(self):
        template = _meta_template(
            parameter_format="NAMED",
            body="Olá {{nome}}, sua cota {{cota}}",
            named_examples=[
                {"param_name": "nome", "example": "João"},
                {"param_name": "quota", "example": "3/12"},
            ],
        )
        first = build_translation_parameters(template)
        second = build_translation_parameters(template)
        self.assertEqual(first, second)
