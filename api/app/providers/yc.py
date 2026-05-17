import csv
import gzip
import io
import logging
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import aioboto3
from botocore.config import Config as BotoConfig

from app.models.cluster import ProviderType
from app.providers.base import BaseProvider, CredentialFieldSpec
from app.providers.dto import BillingRecordDTO

logger = logging.getLogger(__name__)


_NAMESPACE_LABEL_KEYS = (
    "labels.k8s_namespace",
    "labels.kubernetes_namespace",
    "labels.namespace",
)
_SERVICE_LABEL_KEYS = ("labels.service", "labels.app", "labels.application")
_PREEMPTIBLE_PATTERN = re.compile(r"preemptible", re.IGNORECASE)
_DEFAULT_S3_ENDPOINT = "https://storage.yandexcloud.net"


class YCProvider(BaseProvider):
    PROVIDER_TYPE = ProviderType.YC
    DISPLAY_NAME = "Yandex Cloud"
    DESCRIPTION = "Yandex Cloud Managed Kubernetes cluster with billing CSV exports stored in Object Storage."
    REQUIRED_CREDENTIALS = [
        CredentialFieldSpec(
            name="access_key",
            label="S3 Access Key ID",
            is_secret=False,
            help_text="Static access key ID for the service account with read access to the billing bucket.",
        ),
        CredentialFieldSpec(
            name="secret_key",
            label="S3 Secret Access Key",
            is_secret=True,
        ),
        CredentialFieldSpec(
            name="bucket",
            label="Billing Bucket",
            is_secret=False,
            placeholder="finops-billing-export",
        ),
        CredentialFieldSpec(
            name="prefix",
            label="Billing Prefix",
            is_secret=False,
            required=False,
            placeholder="exports/",
            help_text="Optional path prefix inside the bucket where YC writes CSV exports.",
        ),
        CredentialFieldSpec(
            name="endpoint",
            label="S3 Endpoint",
            is_secret=False,
            required=False,
            placeholder=_DEFAULT_S3_ENDPOINT,
            help_text="Override only if you use a non-default S3 endpoint.",
        ),
    ]

    # ── Billing ETL ──────────────────────────────────────────────────────

    async def iter_billing_records(
        self,
        credentials: dict[str, str],
        *,
        since: datetime,
        until: datetime,
    ) -> AsyncIterator[BillingRecordDTO]:
        access_key = credentials["access_key"]
        secret_key = credentials["secret_key"]
        bucket = credentials["bucket"]
        prefix = credentials.get("prefix", "") or ""
        endpoint = credentials.get("endpoint") or _DEFAULT_S3_ENDPOINT

        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)

        logger.info(
            "YC billing ETL: bucket=%s prefix=%r since=%s until=%s",
            bucket,
            prefix,
            since.isoformat(),
            until.isoformat(),
        )

        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=BotoConfig(signature_version="s3v4", retries={"max_attempts": 3}),
        ) as s3:
            paginator = s3.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                contents = page.get("Contents", [])
                if not contents:
                    continue
                for obj in contents:
                    key = obj["Key"]
                    last_modified = obj.get("LastModified")
                    if last_modified is None:
                        continue
                    if last_modified < since or last_modified > until:
                        continue
                    if not (key.endswith(".csv") or key.endswith(".csv.gz")):
                        continue

                    logger.debug(
                        "YC billing ETL: reading object %s (%s bytes)",
                        key,
                        obj.get("Size"),
                    )
                    response = await s3.get_object(Bucket=bucket, Key=key)
                    body = await response[
                        "Body"
                    ].read()  # files are small (~MB), full read OK

                    try:
                        for dto in self._parse_csv_bytes(body, source_key=key):
                            yield dto
                    except Exception:  # noqa: BLE001
                        logger.exception(
                            "YC billing ETL: failed to parse %s, skipping", key
                        )
                        continue

    # ── CSV parsing ──────────────────────────────────────────────────────

    @classmethod
    def _parse_csv_bytes(
        cls, body: bytes, *, source_key: str
    ) -> list[BillingRecordDTO]:
        if source_key.endswith(".gz") or body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        text = body.decode("utf-8-sig")  # YC sometimes emits BOM
        reader = csv.DictReader(io.StringIO(text))
        out: list[BillingRecordDTO] = []
        for row in reader:
            dto = cls._row_to_dto(row)
            if dto is not None:
                out.append(dto)
        return out

    @classmethod
    def _row_to_dto(cls, row: dict[str, Any]) -> BillingRecordDTO | None:
        date_raw = (row.get("date") or "").strip()
        if not date_raw:
            return None
        try:
            day = datetime.strptime(date_raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                day = datetime.fromisoformat(date_raw).astimezone(timezone.utc)
            except ValueError:
                return None

        period_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = day.replace(hour=23, minute=59, second=59, microsecond=0)

        cost = cls._parse_decimal(row.get("cost"))
        if cost is None:
            return None
        # Negative costs (grants, credits) are intentionally kept — see iteration plan.

        sku_name = (row.get("sku_name") or "").strip()
        service_name = (row.get("service_name") or "").strip()
        if not sku_name or not service_name:
            return None

        resource_id = (row.get("resource_id") or "").strip() or None
        resource_name = (row.get("resource_name") or "").strip() or None
        currency = (row.get("currency") or "RUB").strip() or "RUB"

        return BillingRecordDTO(
            period_start=period_start,
            period_end=period_end,
            service_name=service_name,
            resource_id=resource_id,
            resource_name=resource_name,
            sku_name=sku_name,
            cost=cost,
            currency=currency,
            label_namespace=cls._first_nonempty_label(row, _NAMESPACE_LABEL_KEYS),
            label_service=cls._first_nonempty_label(row, _SERVICE_LABEL_KEYS),
            is_preemptible=bool(_PREEMPTIBLE_PATTERN.search(sku_name)),
            raw=None,  # raw payload omitted to save memory; flip to row dict if you want forensics
        )

    @staticmethod
    def _parse_decimal(value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value).strip())
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _first_nonempty_label(row: dict[str, Any], keys: tuple[str, ...]) -> str | None:
        for key in keys:
            value = row.get(key)
            if value is None:
                continue
            value = str(value).strip()
            if value:
                return value
        return None
