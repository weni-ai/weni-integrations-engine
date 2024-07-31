from django_redis import get_redis_connection

from django.core.cache import cache

from marketplace.wpp_products.models import ProductValidation


class SKUValidator:
    def __init__(self, service, domain, zeroshot_client):
        self.service = service
        self.domain = domain
        self.zeroshot_client = zeroshot_client
        self.redis_client = get_redis_connection()
        self.default_timeout = 3600

    def validate_product_details(self, sku_id, catalog):
        cache_key = f"{catalog.uuid}:{sku_id}"
        cached_validation = cache.get(cache_key)

        if cached_validation is not None:
            is_valid, classification = cached_validation
            if not is_valid:
                print(f"SKU:{sku_id} is invalid in cache for catalog: {catalog.name}")
                return None
            return self.service.get_product_details(sku_id, self.domain)

        is_valid = (
            ProductValidation.objects.filter(sku_id=sku_id, catalog=catalog)
            .values_list("is_valid", flat=True)
            .first()
        )

        if is_valid is not None:
            if not is_valid:
                print(
                    f"SKU:{sku_id} is invalid in the database for catalog: {catalog.name}"
                )
                cache.set(
                    cache_key,
                    (False, "Invalid from database"),
                    timeout=self.default_timeout,
                )
                return None

            product_details = self.service.get_product_details(sku_id, self.domain)
            cache.set(
                cache_key, (True, "Valid from database"), timeout=self.default_timeout
            )
            return product_details

        product_details = self.service.get_product_details(sku_id, self.domain)
        if not product_details:
            return None

        is_active = product_details.get("IsActive")
        if is_active is False:
            return product_details

        name = product_details["ProductName"]
        description = product_details["ProductDescription"]
        product_description = name
        if description:
            product_description = f"{name}. {description}"

        product_description = product_description[:9999]

        is_valid, classification = self.validate_with_ai(product_description)

        if not is_valid:
            ProductValidation.objects.create(
                catalog=catalog,
                sku_id=sku_id,
                is_valid=is_valid,
                classification=classification,
                description=product_description,
            )
            print(f"{classification} is not a valid category")
            return None

        cache.set(cache_key, (is_valid, classification), timeout=self.default_timeout)
        return product_details

    def validate_with_ai(self, product_description: str):
        try:
            response = self.zeroshot_client.validate_product_policy(product_description)
            response = response["output"]
            classification = response["classification"]
            # if ither comes false it means that the product is within some goal exclusion rule
            is_valid = response["other"]
        except Exception as e:
            print(f"An error ocurred on get policy on zeroshot {e}")
            is_valid = True
            classification = "Valid because exception"
            return is_valid, classification

        return is_valid, classification
