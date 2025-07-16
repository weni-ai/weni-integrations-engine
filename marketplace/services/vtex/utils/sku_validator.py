import logging

from django.conf import settings
from django_redis import get_redis_connection
from django.core.cache import cache
from marketplace.wpp_products.models import Catalog, ProductValidation


logger = logging.getLogger(__name__)


class SKUValidator:
    def __init__(self, service, domain, zeroshot_client):
        self.service = service
        self.domain = domain
        self.zeroshot_client = zeroshot_client
        self.redis_client = get_redis_connection()
        self.default_timeout = settings.SKU_VALIDATOR_TIMEOUT
        self.cache_prefix = "sku_validator"

    def _get_cache_key(self, catalog: Catalog, sku_id: str) -> str:
        """Generate a cache key with prefix for easier searching"""
        return f"{self.cache_prefix}:{str(catalog.uuid)}:{sku_id}"

    def _get_cached_validation(self, cache_key: str):
        """Get cached validation and renew timeout if found"""
        cached_validation = cache.get(cache_key)
        if cached_validation is not None:
            # Renew the cache timeout when accessed
            cache.set(cache_key, cached_validation, timeout=self.default_timeout)
        return cached_validation

    def validate_product_details(self, sku_id: str, catalog: Catalog):
        # Ensure SKU ID is a non-empty string
        if not isinstance(sku_id, str) or not sku_id.strip():
            logger.error(
                f"Invalid sku_id: Expected non-empty string, got {sku_id} (type: {type(sku_id).__name__})"
            )
            return None

        cache_key = self._get_cache_key(catalog, sku_id)
        cached_validation = self._get_cached_validation(cache_key)

        if cached_validation is not None:
            is_valid, classification = cached_validation
            if not is_valid:
                logger.info(
                    f"SKU:{sku_id} is invalid in cache for catalog: {catalog.name}"
                )
                return None
            return self.service.get_product_details(sku_id, self.domain)

        is_valid = (
            ProductValidation.objects.filter(sku_id=sku_id, catalog=catalog)
            .values_list("is_valid", flat=True)
            .first()
        )

        if is_valid is not None:
            if not is_valid:
                logger.info(
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
            logger.info(f"{classification} is not a valid category")
            return None

        cache.set(cache_key, (is_valid, classification), timeout=self.default_timeout)
        return product_details

    def validate_with_ai(self, product_description: str):
        try:
            response = self.zeroshot_client.validate_product_policy(product_description)
            response = response["output"]
            classification = response["classification"]
            # if other comes false it means that the product is within some goal exclusion rule
            is_valid = response["other"]
        except Exception as e:
            logger.info(f"An error occurred on get policy on zeroshot {e}")
            is_valid = True
            classification = "Valid because exception"
            return is_valid, classification

        return is_valid, classification
