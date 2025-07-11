from enum import IntEnum


class ProductPriority(IntEnum):
    DEFAULT = 0  # Save and upload products
    ON_DEMAND = 1  # Save and upload products with most priority
    API_ONLY = 2  # Return products without saving or uploading
