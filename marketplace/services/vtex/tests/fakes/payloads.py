"""
Faithful builders for raw VTEX API payloads used by test doubles.

These helpers mirror the JSON shapes returned by the real VTEX endpoints so fakes
and tests exercise the same parsing/normalization the production clients rely on.
"""

from typing import Any, Dict, List


def build_sku_detail(
    sku_id,
    *,
    product_id=None,
    name=None,
    product_name=None,
    description=None,
    brand="Arado",
    is_active=True,
    image_url=None,
    detail_url=None,
    sellers=None,
) -> Dict[str, Any]:
    """
    Build a payload shaped like VTEX `.../pvt/sku/stockkeepingunitbyid/{sku_id}`.

    Only the fields consumed by the product pipeline (ProductExtractor and
    SKUValidator) are guaranteed; the structure follows the real response.
    """
    sku_id = str(sku_id)
    product_id = str(product_id or sku_id)
    name = name or f"Product {sku_id}"
    sellers = [str(seller) for seller in (sellers or ["1"])]

    return {
        "Id": sku_id,
        "ProductId": product_id,
        "NameComplete": name,
        "ProductName": product_name or name,
        "ProductDescription": description if description is not None else name,
        "SkuName": name,
        "IsActive": is_active,
        "BrandId": "2000000",
        "BrandName": brand,
        "DetailUrl": detail_url or f"/{sku_id}/p",
        "Images": [
            {
                "ImageUrl": image_url or f"https://images.vtex.com/ids/{sku_id}.jpg",
                "IsMain": True,
            }
        ],
        "SkuSellers": [
            {"SellerId": seller, "StockKeepingUnitId": sku_id} for seller in sellers
        ],
    }


def build_order_form_simulation(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a payload shaped like VTEX `/api/checkout/pub/orderForms/simulation`.

    Prices follow the VTEX convention of integer cents (e.g. 10000 == 100.00).
    Each input item accepts: id, seller, available (bool), price, list_price,
    selling_price, quantity.
    """
    order_items = []
    for item in items:
        price = item.get("price", 10000)
        order_items.append(
            {
                "id": str(item["id"]),
                "seller": str(item["seller"]),
                "quantity": item.get("quantity", 1),
                "availability": (
                    "available" if item.get("available", True) else "cannotBeDelivered"
                ),
                "price": price,
                "listPrice": item.get("list_price", price),
                "sellingPrice": item.get("selling_price", price),
            }
        )
    return {"items": order_items}


def normalize_simulation_item(
    item: Dict[str, Any], full_response: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Normalize a raw VTEX simulation item to the shape returned by the VTEX clients.

    Mirrors the transformation performed by `VtexPrivateClient`/`VtexProxyClient`.
    """
    return {
        "is_available": item.get("availability") == "available",
        "price": item.get("price", 0),
        "list_price": item.get("listPrice", 0),
        "selling_price": item.get("sellingPrice", 0),
        "data": full_response,
    }
