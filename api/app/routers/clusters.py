from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import (
    ClusterCreate,
    ClusterDetailedRead,
    ClusterRead,
    ClusterUpdate,
    CredentialMaskedRead,
    CredentialUpsert,
    Page,
)
from app.services.cluster_service import (
    ClusterAlreadyExistsError,
    ClusterNotFoundError,
    ClusterService,
    CredentialValidationError,
)
from app.services.factory import ServiceFactory
from app.core.dependencies import get_service_factory

from app.services.clients import ClientError  # noqa: F401  (used in future iterations)

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> ClusterService:
    return ClusterService(session)


@router.get("/clusters", response_model=Page[ClusterRead])
async def list_clusters(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: ClusterService = Depends(_service),
) -> Page[ClusterRead]:
    items, total = await service.list_clusters(limit=limit, offset=offset)
    return Page[ClusterRead](
        items=[ClusterRead.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/clusters",
    response_model=ClusterRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_cluster(
    payload: ClusterCreate,
    service: ClusterService = Depends(_service),
) -> ClusterRead:
    try:
        cluster = await service.create_cluster(payload)
    except ClusterAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ClusterRead.model_validate(cluster)


@router.get("/clusters/{cluster_id}", response_model=ClusterDetailedRead)
async def get_cluster(
    cluster_id: UUID,
    service: ClusterService = Depends(_service),
) -> ClusterDetailedRead:
    try:
        cluster = await service.get_cluster(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    creds = await service.list_credentials(cluster_id)
    base = ClusterRead.model_validate(cluster).model_dump()
    return ClusterDetailedRead(**base, credential_keys=[c.key_name for c in creds])


@router.patch("/clusters/{cluster_id}", response_model=ClusterRead)
async def update_cluster(
    cluster_id: UUID,
    payload: ClusterUpdate,
    service: ClusterService = Depends(_service),
) -> ClusterRead:
    try:
        cluster = await service.update_cluster(cluster_id, payload)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClusterAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ClusterRead.model_validate(cluster)


@router.delete("/clusters/{cluster_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cluster(
    cluster_id: UUID,
    service: ClusterService = Depends(_service),
) -> None:
    try:
        await service.delete_cluster(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/clusters/{cluster_id}/credentials",
    response_model=list[CredentialMaskedRead],
)
async def list_cluster_credentials(
    cluster_id: UUID,
    service: ClusterService = Depends(_service),
) -> list[CredentialMaskedRead]:
    try:
        creds = await service.list_credentials(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [CredentialMaskedRead(key_name=c.key_name) for c in creds]


@router.put(
    "/clusters/{cluster_id}/credentials",
    response_model=list[CredentialMaskedRead],
)
async def upsert_cluster_credentials(
    cluster_id: UUID,
    payload: CredentialUpsert,
    service: ClusterService = Depends(_service),
) -> list[CredentialMaskedRead]:
    try:
        creds = await service.upsert_credentials(cluster_id, payload.values)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CredentialValidationError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return [CredentialMaskedRead(key_name=c.key_name) for c in creds]


@router.get("/clusters/{cluster_id}/diagnostics")
async def cluster_diagnostics(
    cluster_id: UUID,
    service: ClusterService = Depends(_service),
    factory: ServiceFactory = Depends(get_service_factory),
) -> dict:
    """Probe upstream OpenCost and VictoriaMetrics endpoints for a cluster."""
    try:
        cluster = await service.get_cluster(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    opencost_client = await factory.opencost(cluster)
    vm_client = await factory.vm(cluster)

    opencost_ok = await opencost_client.healthcheck()
    vm_ok = await vm_client.healthcheck()

    return {
        "cluster_id": str(cluster.id),
        "cluster_name": cluster.name,
        "opencost": {
            "base_url": opencost_client.base_url,
            "reachable": opencost_ok,
        },
        "victoria_metrics": {
            "base_url": vm_client.base_url,
            "reachable": vm_ok,
        },
    }
