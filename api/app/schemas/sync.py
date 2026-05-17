from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import SyncRunStatus


class BillingSyncRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cluster_id: UUID
    status: SyncRunStatus
    window_start: datetime
    window_end: datetime
    started_at: datetime
    finished_at: datetime | None = None
    records_imported: int
    error_message: str | None = None


class AllocationsSnapshotRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cluster_id: UUID
    status: str
    trigger: str
    window_start: datetime
    window_end: datetime
    days_processed: int
    rows_upserted: int
    error: str | None
    started_at: datetime
    finished_at: datetime | None


class LatestAllocationsSnapshotRun(AllocationsSnapshotRunRead):
    """Same shape — used by /runs/latest for parity with billing API."""

    pass
