"""
test_config.py — Tests para la carga y validación del fichero YAML.

Usamos pytest, que descubre automáticamente los ficheros test_*.py
y las funciones test_*().

tmp_path es un "fixture" de pytest: inyecta automáticamente un directorio
temporal único por test. No necesitamos crearlo ni borrarlo.
"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from pulse.config import PulseConfig, Target, load_config


class TestTarget:
    """Agrupa los tests relacionados con el modelo Target."""

    def test_defaults(self) -> None:
        """Los campos opcionales deben tener sus valores por defecto."""
        target = Target(name="test", url="https://example.com")
        assert target.expected_status == 200
        assert target.max_latency_ms == 1000

    def test_invalid_url_raises(self) -> None:
        """Pydantic debe rechazar una URL que no sea HTTP/HTTPS."""
        with pytest.raises(ValidationError):
            Target(name="test", url="not-a-url")

    def test_negative_latency_raises(self) -> None:
        """El validator custom debe rechazar latencias no positivas."""
        with pytest.raises(ValidationError):
            Target(name="test", url="https://example.com", max_latency_ms=-1)

    def test_url_str_property(self) -> None:
        """url_str debe devolver un string plano usable con httpx."""
        target = Target(name="test", url="https://example.com/health")
        assert isinstance(target.url_str, str)
        assert target.url_str == "https://example.com/health"


class TestLoadConfig:
    """Tests para la función load_config()."""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """Debe cargar correctamente un YAML válido."""
        # Creamos un fichero YAML temporal con el formato esperado.
        config_data = {
            "targets": [
                {
                    "name": "google",
                    "url": "https://www.google.com",
                    "expected_status": 200,
                    "max_latency_ms": 500,
                }
            ]
        }
        config_file = tmp_path / "pulse.yaml"
        config_file.write_text(yaml.dump(config_data))

        config = load_config(config_file)

        assert isinstance(config, PulseConfig)
        assert len(config.targets) == 1
        assert config.targets[0].name == "google"

    def test_load_multiple_targets(self, tmp_path: Path) -> None:
        """Debe cargar una lista de múltiples targets."""
        config_data = {
            "targets": [
                {"name": "a", "url": "https://a.com"},
                {"name": "b", "url": "https://b.com"},
                {"name": "c", "url": "https://c.com"},
            ]
        }
        config_file = tmp_path / "pulse.yaml"
        config_file.write_text(yaml.dump(config_data))

        config = load_config(config_file)
        assert len(config.targets) == 3

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        """Debe propagar FileNotFoundError si el fichero no existe."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "no_existe.yaml")

    def test_missing_required_field_raises(self, tmp_path: Path) -> None:
        """Debe fallar si falta un campo requerido (url)."""
        # Target sin url: Pydantic debe lanzar ValidationError.
        config_data = {"targets": [{"name": "sin-url"}]}
        config_file = tmp_path / "pulse.yaml"
        config_file.write_text(yaml.dump(config_data))

        with pytest.raises(ValidationError):
            load_config(config_file)

    def test_empty_targets_list(self, tmp_path: Path) -> None:
        """Una lista vacía es válida según el esquema."""
        config_data = {"targets": []}
        config_file = tmp_path / "pulse.yaml"
        config_file.write_text(yaml.dump(config_data))

        config = load_config(config_file)
        assert config.targets == []
