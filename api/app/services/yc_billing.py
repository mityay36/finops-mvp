import io
import boto3
import pandas as pd
from datetime import datetime, timedelta
from app.config import settings

class YCBillingService:
    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=settings.yc_endpoint,
            aws_access_key_id=settings.yc_access_key,
            aws_secret_access_key=settings.yc_secret_key,
            region_name=settings.yc_region,
        )
        self.bucket = settings.yc_bucket

    def _list_recent_csvs(self, days: int = 30) -> list[str]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        keys = []
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix="billing/"):
                for obj in page.get("Contents", []):
                    if obj["LastModified"].replace(tzinfo=None) > cutoff:
                        keys.append(obj["Key"])
        except Exception:
            pass
        return keys

    def get_actual_costs(self, days: int = 30) -> dict:
        keys = self._list_recent_csvs(days)
        if not keys:
            return {"error": "No billing CSVs found", "total": 0, "by_service": []}

        dfs = []
        for key in keys:
            try:
                obj = self.s3.get_object(Bucket=self.bucket, Key=key)
                df = pd.read_csv(io.BytesIO(obj["Body"].read()))
                dfs.append(df)
            except Exception:
                continue

        if not dfs:
            return {"error": "Failed to parse CSVs", "total": 0, "by_service": []}

        combined = pd.concat(dfs, ignore_index=True)

        # YC billing CSV columns: service_name, cost, currency, usage_date
        cost_col = next((c for c in combined.columns if "cost" in c.lower()), None)
        svc_col = next((c for c in combined.columns
    if any(x in c.lower() for x in ["service_name", "product", "service"])), None)

        if not cost_col or not svc_col:
            return {"raw_columns": list(combined.columns), "total": 0, "by_service": []}

        combined[cost_col] = pd.to_numeric(combined[cost_col], errors="coerce").fillna(0)
        by_service = (
            combined.groupby(svc_col)[cost_col]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        return {
            "total": round(float(combined[cost_col].sum()), 2),
            "currency": "RUB",
            "period_days": days,
            "by_service": [
                {"service": k, "cost": round(float(v), 2)}
                for k, v in by_service.items()
            ],
        }

yc_billing = YCBillingService()
