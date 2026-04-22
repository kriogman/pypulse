# pulse

CLI que chequea endpoints HTTP en paralelo usando `asyncio` + `httpx`.

## Requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Instalación y uso local

```bash
# Instalar dependencias y crear el venv automáticamente
uv sync

# Correr el check con el pulse.yaml de ejemplo
uv run pulse check

# Con opciones
uv run pulse check -c /ruta/a/config.yaml -t 10 --format json

# Ver ayuda
uv run pulse --help
uv run pulse check --help
```

## Tests

```bash
# Correr todos los tests
uv run pytest

# Con output detallado
uv run pytest -v

# Solo un fichero
uv run pytest tests/test_checker.py -v
```

## Linting

```bash
# Verificar
uv run ruff check src/ tests/

# Formatear
uv run ruff format src/ tests/
```

## Docker

```bash
# Build
docker build -t pulse:latest .

# Correr montando tu pulse.yaml local
docker run --rm -v $(pwd)/pulse.yaml:/etc/pulse/pulse.yaml pulse:latest \
  pulse check -c /etc/pulse/pulse.yaml

# Formato JSON
docker run --rm -v $(pwd)/pulse.yaml:/etc/pulse/pulse.yaml pulse:latest \
  pulse check -c /etc/pulse/pulse.yaml --format json
```

## Kubernetes

```bash
# Aplicar todos los manifiestos (ConfigMap + CronJob)
kubectl apply -k k8s/

# Ver el CronJob
kubectl get cronjob pulse-checker

# Lanzar un Job manualmente para probar sin esperar los 5 minutos
kubectl create job pulse-test --from=cronjob/pulse-checker

# Ver el resultado
kubectl get jobs
kubectl logs job/pulse-test
```

### Probar con kind (cluster local)

```bash
# Instalar kind: https://kind.sigs.k8s.io/
kind create cluster --name pulse-test

# Cargar la imagen local en kind (no necesita registry)
kind load docker-image pulse:latest --name pulse-test

# Desplegar
kubectl apply -k k8s/

# Editar cronjob para probar: cambia */5 por */1 (cada minuto)
kubectl patch cronjob pulse-checker -p '{"spec":{"schedule":"*/1 * * * *"}}'

# Limpiar
kind delete cluster --name pulse-test
```
