"""
config.py — Carga y valida el fichero YAML de configuración.

Usamos Pydantic para definir los modelos de datos. Pydantic lee los type hints
(: str, : int, etc.) y valida automáticamente que los datos tengan el tipo correcto.
Si el YAML tiene un campo mal (falta url, latency es texto...), falla aquí,
no en mitad de los checks.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, HttpUrl, field_validator


class Target(BaseModel):
    """
    Representa un endpoint a chequear.

    BaseModel de Pydantic: al crear Target(name="x", url="http://...", ...),
    Pydantic valida que los tipos sean correctos antes de asignarlos.
    """

    name: str
    url: HttpUrl  # Pydantic valida que sea una URL HTTP/HTTPS válida
    expected_status: int = 200  # Valor por defecto: si no está en el YAML, usa 200
    max_latency_ms: int = 1000

    @field_validator("max_latency_ms")
    @classmethod
    def latency_must_be_positive(cls, v: int) -> int:
        """Los decoradores @field_validator añaden validaciones custom."""
        if v <= 0:
            raise ValueError("max_latency_ms debe ser mayor que 0")
        return v

    @property
    def url_str(self) -> str:
        """
        Devuelve la URL como string plano.

        Pydantic v2 convierte HttpUrl a un objeto especial; para httpx
        necesitamos un str normal. Los @property son getters calculados,
        no se guardan en el objeto.
        """
        return str(self.url)


class PulseConfig(BaseModel):
    """Modelo raíz del fichero YAML. Contiene la lista de targets."""

    targets: list[Target]  # list[Target] = lista de objetos Target


def load_config(path: Path) -> PulseConfig:
    """
    Lee el YAML del disco y lo convierte en un objeto PulseConfig validado.

    Args:
        path: Ruta al fichero .yaml

    Returns:
        PulseConfig con todos los targets ya validados.

    Raises:
        FileNotFoundError: si el fichero no existe.
        yaml.YAMLError: si el YAML está malformado.
        pydantic.ValidationError: si los datos no cumplen el esquema.
    """
    # Path.read_text() lee el fichero completo como string.
    # yaml.safe_load() lo convierte a dict de Python (seguro: no ejecuta código YAML).
    raw: dict = yaml.safe_load(path.read_text())

    # model_validate() es el constructor de Pydantic: recibe un dict y devuelve
    # un objeto PulseConfig validado. Si algo falla, lanza ValidationError con
    # un mensaje claro de qué campo está mal.
    return PulseConfig.model_validate(raw)
