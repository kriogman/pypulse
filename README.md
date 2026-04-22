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

## 🗺️ Roadmap

Proyecto de aprendizaje de Python moderno (async, type hints, packaging con uv)
y de despliegue en Kubernetes. Las versiones siguen [Semantic Versioning](https://semver.org/).

### ✅ v0.1.0 — MVP
- [x] CLI con Click y subcomando `check`
- [x] Lectura de targets desde YAML con validación via Pydantic
- [x] Chequeo paralelo con `asyncio` + `httpx`
- [x] Output en formato `text` y `json`
- [x] Exit codes útiles para CI
- [x] Tests con `pytest` + `pytest-asyncio` + `respx`
- [x] Dockerfile multi-stage
- [x] Despliegue como CronJob en Kubernetes con Kustomize

### 🚧 v0.2.0 — Observabilidad básica
- [ ] Logging estructurado con `structlog`
- [ ] Output JSON para logs (facilita ingesta en Loki / ELK)
- [ ] Niveles de log configurables (`--log-level`)

### 📋 v0.3.0 — Resiliencia
- [ ] Retries con backoff exponencial (`tenacity`)
- [ ] Configuración de reintentos por target en el YAML
- [ ] Timeout configurable por target además del global

### 📋 v0.4.0 — Modo daemon
- [ ] Subcomando `serve` con scheduler interno (`apscheduler` o asyncio puro)
- [ ] Endpoint `/metrics` con `prometheus-client`
- [ ] Endpoint `/healthz` con FastAPI o Starlette
- [ ] Graceful shutdown con signal handlers

### 📋 v0.5.0 — CI/CD y distribución
- [ ] GitHub Actions: lint (`ruff`), type check (`mypy`), tests (`pytest`)
- [ ] GitHub Actions: build y push de imagen a GHCR
- [ ] Publicación en PyPI con `uv publish`
- [ ] Helm chart para despliegue en Kubernetes

### 💡 Ideas futuras (sin versión asignada)
- [ ] Notificaciones a Slack / Discord / webhook en fallos
- [ ] Chequeos TCP, DNS y validación de certificados TLS
- [ ] Soporte para autenticación (Bearer token, mTLS)
- [ ] Dashboard web con FastAPI + HTMX
- [ ] Comparativa de rendimiento y tamaño de imagen vs la versión en Go
      (`pulse`), como ejercicio didáctico

---

Las contribuciones e ideas son bienvenidas vía issues.
