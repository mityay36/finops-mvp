#!/bin/bash
# Генерирует ConfigMap YAML из JSON-файлов дашбордов
# Запускать из корня репозитория: ./dashboards/generate.sh
set -e

DASH_DIR="$(dirname "$0")"

for JSON_FILE in "$DASH_DIR"/*.json; do
  DASH_ID=$(basename "$JSON_FILE" .json | sed 's/dashboard_//')
  OUT_FILE="$DASH_DIR/configmap-${DASH_ID}.yaml"

  echo "Generating $OUT_FILE..."

  cat > "$OUT_FILE" << YAML
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-${DASH_ID}
  namespace: vmks
  labels:
    grafana_dashboard: "1"
data:
  dashboard_${DASH_ID}.json: |
YAML

  # Indent JSON content by 4 spaces
  cat "$JSON_FILE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
lines = json.dumps(data, indent=2).split('\n')
for line in lines:
    print('    ' + line)
" >> "$OUT_FILE"

  echo "  Done: $OUT_FILE"
done

echo "All ConfigMaps generated!"
