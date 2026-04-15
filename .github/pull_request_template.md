## Описание изменений

_Что изменено и зачем_

## Тип изменения
- [ ] Infrastructure (k8s/vmks, k8s/opencost)
- [ ] Dashboard (k8s/dashboards)
- [ ] Manifest (k8s/manifests)
- [ ] Application code (api/, frontend/)

## Чеклист
- [ ] YAML прошёл lint
- [ ] Helm values валидны (`helm template --dry-run`)
- [ ] Нет credentials/секретов в коде
- [ ] ArgoCD Application paths корректны
- [ ] README обновлён (если нужно)

## ArgoCD Preview
Сделать kubectl port-forward на 8080 порт
После мержа проверить: https://localhost:8080 
