def extract_body_example(example_data: dict) -> list:
    """
    Extract body example from Meta API response format or serializer data.

    This function processes the example data from Meta's API response or serializer
    and extracts the body examples in a format compatible with the TemplateTranslation model.

    Args:
        example_data: Dictionary containing example data from Meta API or serializer

    Returns:
        list: Flattened list of example values
    """
    body_example = []

    if not example_data:
        return body_example

    # Process the example data - flatten nested lists into a single list
    for values in example_data.values():
        if isinstance(values, list) and values:
            # If it's a list of lists, take the first inner list
            if isinstance(values[0], list):
                body_example.extend(values[0])
            else:
                body_example.extend(values)
        else:
            body_example.append(values)

    return body_example
