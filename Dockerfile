# =============================================================================
# STAGE 1: builder
# =============================================================================
# Usamos una imagen con uv ya instalado. uv es mucho más rápido que pip
# para resolver dependencias (escrito en Rust).
#
# Por qué multi-stage:
# - El stage builder instala herramientas de build (uv, compiladores si los
#   hubiera, headers de C). Esas herramientas NO queremos en producción.
# - El stage final copia SOLO el resultado (el venv con las deps instaladas
#   y el código fuente). La imagen final es mucho más pequeña y tiene menor
#   superficie de ataque.
# =============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Directorio de trabajo dentro del contenedor para este stage.
WORKDIR /build

# Copiamos primero solo los ficheros de metadatos del proyecto.
# Docker cachea cada capa. Si pyproject.toml no cambia, Docker reutiliza
# la capa de instalación de deps aunque el código fuente haya cambiado.
# Esto hace los rebuilds mucho más rápidos.
COPY pyproject.toml ./

# Creamos el src/pulse/__init__.py vacío para que uv pueda instalar el paquete
# en modo editable sin necesitar todo el código fuente todavía.
# (uv necesita el paquete resoluble antes de instalar deps)
RUN mkdir -p src/pulse && touch src/pulse/__init__.py

# Instalamos las dependencias de producción en un venv.
# --no-dev: excluye el grupo [dependency-groups.dev] (pytest, ruff, etc.)
# --compile-bytecode: pre-compila los .py a .pyc para startup más rápido
# El venv queda en /build/.venv/
RUN uv sync --no-dev --compile-bytecode

# Ahora copiamos el código fuente real (reemplaza el __init__.py vacío).
COPY src/ src/

# =============================================================================
# STAGE 2: imagen final
# =============================================================================
# python:3.12-slim: imagen oficial de Python sin herramientas de build.
# ~150MB vs ~1GB de la imagen completa.
FROM python:3.12-slim AS final

# Crear un usuario no-root.
# Por qué: si hay una vulnerabilidad en el código o sus deps que permite
# RCE (ejecución remota de código), el atacante solo tiene permisos de
# este usuario, no de root en el host.
RUN useradd --create-home --shell /bin/bash pulse

# Directorio de trabajo en la imagen final.
WORKDIR /app

# Copiamos el venv completo del stage builder (deps instaladas).
# --from=builder especifica el stage fuente.
# No copiamos uv ni herramientas de build, solo las libs y el código.
COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/src /app/src

# Copiamos el pyproject.toml para que el paquete sea reconocible.
COPY pyproject.toml ./

# Añadimos el venv al PATH para que `pulse` (el entry point) sea ejecutable
# directamente sin necesitar activar el venv manualmente.
ENV PATH="/app/.venv/bin:$PATH"

# Cambiamos al usuario no-root antes del CMD.
USER pulse

# El comando por defecto: ejecutar `pulse` sin argumentos muestra el help.
# Los argumentos reales vendrán del CronJob en K8s.
CMD ["pulse", "--help"]
