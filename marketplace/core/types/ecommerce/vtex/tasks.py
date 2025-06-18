from typing import Optional
from marketplace.celery import app as celery_app

from marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand import (
    SyncOnDemandData,
    SyncOnDemandUseCase,
)


@celery_app.task(name="task_sync_on_demand")
def task_sync_on_demand(
    project_uuid: str, sku_ids: list, seller: str, salles_channel: Optional[str] = None
):
    """
    Syncs products on demand for a VTEX app.
    """
    use_case = SyncOnDemandUseCase()
    data = SyncOnDemandData(
        sku_ids=sku_ids, seller=seller, salles_channel=salles_channel
    )
    use_case.execute(data, project_uuid)
