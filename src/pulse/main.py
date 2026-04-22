"""
main.py — Punto de entrada del programa.

Este fichero es mínimo a propósito. Su único trabajo es importar el grupo
CLI y exponerlo como `main()`. El entry point en pyproject.toml apunta aquí:

    [project.scripts]
    pulse = "pulse.main:main"

Separar main.py de cli.py tiene una ventaja: en los tests podemos importar
`cli` directamente sin ejecutar nada, mientras que `main` es solo para
el ejecutable final.
"""

from pulse.cli import cli


def main() -> None:
    """
    Invoca el grupo de comandos Click.

    standalone_mode=True (defecto de Click) captura SystemExit y la convierte
    en un exit code real del proceso. Lo dejamos en True para que sys.exit()
    en cli.py funcione correctamente.
    """
    cli()


if __name__ == "__main__":
    # Permite correr directamente: python -m pulse.main
    # Útil para debugging sin necesidad de instalar el paquete.
    main()
