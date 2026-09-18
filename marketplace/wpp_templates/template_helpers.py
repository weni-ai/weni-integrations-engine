NAMED_EXAMPLE_KEYS = frozenset({"body_text_named_params", "header_text_named_params"})


def extract_body_example(example_data: dict) -> list:
    """Flatten positional example values. Named example keys are skipped, not stored."""
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
