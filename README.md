# FinOps MVP — Yandex Cloud

GitOps-репозиторий для диссертации «Исследование и внедрение FinOps практик».

## Стек
| Компонент | Версия | Namespace |
|---|---|---|
| ArgoCD | stable | argocd |
| VictoriaMetrics K8s Stack | 0.72.6 | vmks |
| OpenCost | 2.5.10 | opencost |
| Grafana Dashboards | — | vmks |

## Структура репозитория
```
finops-mvp/
├── apps/               # ArgoCD Application манифесты
│   ├── root-app.yaml   # App-of-Apps корневой
│   ├── vmks-app.yaml
│   ├── opencost-app.yaml
│   └── dashboards-app.yaml
├── vmks/
│   └── values.yaml     # VictoriaMetrics Stack values
├── opencost/
│   └── values.yaml     # OpenCost values
├── manifests/
│   └── opencost/
│       └── vmservicescrape.yaml
├── dashboards/         # Grafana ConfigMaps (генерируются скриптом)
└── bootstrap.sh        # Первоначальная установка кластера
```

## Bootstrap (первый запуск)
```bash
chmod +x bootstrap.sh && ./bootstrap.sh
```

## После пуша в main
ArgoCD автоматически синхронизирует все изменения.
