from typing import Optional
from marketplace.celery import app as celery_app
from marketplace.core.types.ecommerce.dtos.sync_on_demand_dto import SyncOnDemandDTO
from marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand import (
    SyncOnDemandUseCase,
)


@celery_app.task(name="task_sync_on_demand")
def task_sync_on_demand(
    project_uuid: str,
    sku_ids: list,
    seller: str,
    sales_channel: Optional[list[str]] = None,
):
    """
    Syncs products on demand for a VTEX app.
    """
    use_case = SyncOnDemandUseCase()
    dto = SyncOnDemandDTO(sku_ids=sku_ids, seller=seller, sales_channel=sales_channel)
    use_case.execute(dto, project_uuid)
