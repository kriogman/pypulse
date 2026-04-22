"""
cli.py — Definición de la interfaz de línea de comandos con Click.

Click usa decoradores (@click.command, @click.option) para declarar
la estructura del CLI. Es más idiomático que argparse y genera
automáticamente el texto de ayuda (--help).
"""

import asyncio
import json
import sys
from pathlib import Path

import click

from pulse.checker import CheckResult, Verdict, run_checks
from pulse.config import load_config


# @click.group() define un comando "grupo" que puede tener subcomandos.
# Así podemos tener: pulse check, pulse version, pulse validate, etc.
@click.group()
def cli() -> None:
    """pulse — Chequea endpoints HTTP en paralelo."""


@cli.command()
@click.option(
    "-c",
    "--config",
    "config_path",  # Nombre de la variable Python (evita conflicto con builtin `config`)
    default="pulse.yaml",
    show_default=True,
    type=click.Path(exists=True, path_type=Path),  # Click verifica que el fichero exista
    help="Ruta al fichero de configuración YAML.",
)
@click.option(
    "-t",
    "--timeout",
    default=5.0,
    show_default=True,
    type=float,
    help="Timeout global por petición en segundos.",
)
@click.option(
    "--format",
    "output_format",  # `format` es builtin de Python, usamos nombre alternativo
    default="text",
    show_default=True,
    type=click.Choice(["text", "json"]),  # Solo acepta estos dos valores
    help="Formato de salida.",
)
def check(config_path: Path, timeout: float, output_format: str) -> None:
    """
    Chequea todos los endpoints definidos en el fichero de configuración.

    Ejemplos:
        pulse check
        pulse check -c /etc/pulse/pulse.yaml --format json
        pulse check -t 10
    """
    # Cargamos y validamos el YAML. Si hay errores, Pydantic lanza una
    # excepción clara antes de hacer ninguna petición HTTP.
    try:
        config = load_config(config_path)
    except Exception as exc:
        # click.echo() escribe en stdout (o stderr con err=True).
        # click.style() añade color ANSI si el terminal lo soporta.
        click.echo(click.style(f"Error cargando config: {exc}", fg="red"), err=True)
        sys.exit(1)

    # asyncio.run() es el punto de entrada al mundo async.
    # Crea un nuevo event loop, ejecuta la coroutine hasta que termina,
    # y cierra el loop limpiamente.
    # Solo debe llamarse UNA vez en el programa (aquí, en el entry point del CLI).
    results = asyncio.run(run_checks(config.targets, timeout))

    # Renderizamos según el formato pedido.
    if output_format == "json":
        _print_json(results)
    else:
        _print_text(results)

    # Exit code: 0 = todo OK, 1 = al menos un fallo.
    # Esto permite usar pulse en CI: `pulse check && deploy.sh`
    all_ok = all(r.verdict == Verdict.OK for r in results)
    sys.exit(0 if all_ok else 1)


def _print_text(results: list[CheckResult]) -> None:
    """Imprime los resultados en formato texto legible por humanos."""
    for result in results:
        # Colores: verde para OK, rojo para FAIL
        color = "green" if result.verdict == Verdict.OK else "red"
        verdict_str = click.style(result.verdict.value, fg=color, bold=True)

        latency_str = (
            f"{result.latency_ms:.0f}ms" if result.latency_ms is not None else "—"
        )
        status_str = str(result.status_code) if result.status_code is not None else "—"

        # Línea principal
        click.echo(
            f"[{verdict_str}] {result.name:20s}  "
            f"status={status_str:3s}  latency={latency_str:>8s}  {result.url}"
        )

        # Si hay razones de fallo, las mostramos indentadas
        for reason in result.reasons:
            click.echo(f"       └─ {click.style(reason, fg='yellow')}")


def _print_json(results: list[CheckResult]) -> None:
    """Imprime los resultados como JSON (útil para pipelines y log aggregators)."""
    # Construimos una lista de dicts serializables.
    # dataclasses no se serializa directamente con json.dumps, por eso
    # lo convertimos a dict manualmente.
    output = [
        {
            "name": r.name,
            "url": r.url,
            "status_code": r.status_code,
            "latency_ms": round(r.latency_ms, 2) if r.latency_ms is not None else None,
            "verdict": r.verdict.value,  # .value porque Verdict es un Enum
            "reasons": r.reasons,
        }
        for r in results
    ]
    # indent=2 hace el JSON legible; ensure_ascii=False mantiene caracteres UTF-8.
    click.echo(json.dumps(output, indent=2, ensure_ascii=False))
