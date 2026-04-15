from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    opencost_url: str = "http://opencost.opencost.svc.cluster.local:9003"
    vm_url: str = "http://vmsingle-vmks-victoria-metrics-k8s-stack.vmks.svc.cluster.local:8428"
    yc_bucket: str = "finops-billing"
    yc_region: str = "ru-central1"
    yc_endpoint: str = "https://storage.yandexcloud.net"
    yc_access_key: str = ""
    yc_secret_key: str = ""
    cors_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()
