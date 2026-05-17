# app/services/yc_billing.py — обновлённая версия

import csv
import io
from collections import defaultdict
from typing import Any, TypedDict

import boto3

from app.config import settings


class _ResourceAgg(TypedDict):
    cost: float
    resource_id: str
    service_name: str
    is_preemptible: bool


class YCBillingService:
    def __init__(self) -> None:
        self.s3 = boto3.client(
            "s3",
            endpoint_url="https://storage.yandexcloud.net",
            aws_access_key_id=settings.yc_access_key,
            aws_secret_access_key=settings.yc_secret_key,
        )
        self.bucket = settings.yc_bucket
        self.prefix = settings.yc_prefix

    def _get_csv_keys(self, days: int = 30) -> list[str]:
        keys: list[str] = []
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return sorted(keys)[-days:]

    def _parse_resource_name(self, row: dict[str, str]) -> str:
        """Строит человекочитаемое имя ресурса из полей CSV."""
        svc_name = row.get("label.user_labels.service-name", "").strip()
        svc_ns = row.get("label.user_labels.service-namespace", "").strip()
        vol_name = row.get("label.user_labels.volume-name", "").strip()

        if vol_name:
            return f"PVC: {vol_name}"
        if svc_name and svc_ns:
            return f"{svc_ns}/{svc_name}"
        if svc_name:
            return svc_name

        service = row.get("service_name", "").strip()
        sku = row.get("sku_name", "").strip()
        resource_id = row.get("resource_id", "").strip()

        sku_short = sku
        if "Preemptible VM" in sku:
            sku_short = "Preemptible VM"
        elif "Standard disk drive" in sku:
            sku_short = "HDD"
        elif "Network Load Balancer" in sku:
            sku_short = "NLB"
        elif "Public IP address" in sku:
            sku_short = "Public IP"
        elif "Master" in sku and "Kubernetes" in service:
            return "K8s Master"
        elif "Zonal master" in sku:
            return "K8s Zonal Master"
        elif "Container Registry" in service:
            sku_short = "Container Registry"
        elif "Object Storage" in service:
            sku_short = "Object Storage"
        elif "Key Management" in service:
            sku_short = "KMS Key"
        elif "Cloud DNS" in service:
            sku_short = "Cloud DNS"

        if resource_id:
            short_id = resource_id[-8:]
            return f"{service} / {sku_short} (...{short_id})"
        return f"{service} / {sku_short}"

    def _is_preemptible(self, row: dict[str, str]) -> bool:
        return "Preemptible" in row.get("sku_name", "")

    def get_actual_costs(self, days: int = 30) -> dict[str, Any]:
        keys = self._get_csv_keys(days)
        total: float = 0.0
        by_service: dict[str, float] = defaultdict(float)
        by_namespace: dict[str, float] = defaultdict(float)
        resources: list[dict[str, Any]] = []
        has_preemptible = False

        for key in keys:
            obj = self.s3.get_object(Bucket=self.bucket, Key=key)
            content = obj["Body"].read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                cost = float(row.get("cost", 0) or 0)
                service = row.get("service_name", "Unknown")
                resource_id = row.get("resource_id", "")
                namespace = row.get("label.user_labels.service-namespace", "")

                if self._is_preemptible(row):
                    has_preemptible = True

                total += cost
                by_service[service] += cost
                if namespace:
                    by_namespace[namespace] += cost

                if cost > 0:
                    resources.append(
                        {
                            "resource_id": resource_id,
                            "resource_name": self._parse_resource_name(row),
                            "service_name": service,
                            "sku_name": row.get("sku_name", ""),
                            "cost": round(cost, 4),
                            "is_preemptible": self._is_preemptible(row),
                            "namespace": namespace or None,
                        }
                    )

        # Агрегируем по resource_name для дедупликации
        def _empty_agg() -> _ResourceAgg:
            return {
                "cost": 0.0,
                "resource_id": "",
                "service_name": "",
                "is_preemptible": False,
            }

        agg: dict[str, _ResourceAgg] = defaultdict(_empty_agg)
        for r in resources:
            key_name: str = r["resource_name"]
            agg[key_name]["cost"] += float(r["cost"])
            agg[key_name]["resource_id"] = str(r["resource_id"])
            agg[key_name]["service_name"] = str(r["service_name"])
            agg[key_name]["is_preemptible"] = bool(r["is_preemptible"])

        top_resources = [
            {
                "resource_name": k,
                "resource_id": v["resource_id"],
                "service_name": v["service_name"],
                "is_preemptible": v["is_preemptible"],
                "cost": round(v["cost"], 2),
            }
            for k, v in sorted(agg.items(), key=lambda kv: -kv[1]["cost"])[:15]
        ]

        return {
            "total": round(total, 2),
            "has_preemptible_nodes": has_preemptible,
            "by_service": {
                k: round(v, 2)
                for k, v in sorted(by_service.items(), key=lambda x: -x[1])
            },
            "by_namespace": {
                k: round(v, 2)
                for k, v in sorted(by_namespace.items(), key=lambda x: -x[1])
            },
            "top_resources": top_resources,
        }


yc_billing = YCBillingService()
