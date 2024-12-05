from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class FacebookProductDTO:
    id: str
    title: str
    description: str
    availability: str
    status: str
    condition: str
    price: str
    link: str
    image_link: str
    brand: str
    sale_price: str
    product_details: dict  # TODO: Implement ProductDetailsDTO
    additional_image_link: Optional[str] = ""
    rich_text_description: Optional[str] = ""

    def to_meta_payload(self):
        """
        Returns a dictionary containing only the fields relevant to Meta,
        and excludes fields with empty or None values.
        """
        fields_for_meta = [
            "id",
            "title",
            "description",
            "availability",
            "status",
            "condition",
            "price",
            "link",
            "image_link",
            "brand",
            "sale_price",
            "additional_image_link",
            "rich_text_description",
        ]
        # Convert dataclass to dictionary and filter fields
        return {
            key: value
            for key, value in asdict(self).items()
            if key in fields_for_meta and value
        }


@dataclass
class VtexProductDTO:  # TODO: Implement This VtexProductDTO
    pass
