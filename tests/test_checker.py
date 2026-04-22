"""
test_checker.py — Tests para la lógica de checks HTTP.

Usamos respx para interceptar las llamadas de httpx SIN hacer peticiones
reales a internet. Esto hace los tests rápidos, deterministas y reproducibles.

respx funciona como un "proxy" entre httpx y la red:
  - Define qué URLs interceptar y qué respuesta devolver.
  - Si una URL no está interceptada y se usa respx.mock, lanza un error.
"""

import httpx
import pytest
import respx

from pulse.checker import CheckResult, Verdict, check_target, run_checks
from pulse.config import Target


# --- Fixtures: objetos reutilizables entre tests ---

@pytest.fixture
def target_google() -> Target:
    """Target de ejemplo con configuración realista."""
    return Target(
        name="google",
        url="https://www.google.com",
        expected_status=200,
        max_latency_ms=2000,
    )


@pytest.fixture
def target_strict() -> Target:
    """Target con latencia muy baja para testear el fallo por latencia."""
    return Target(
        name="strict",
        url="https://strict.example.com",
        expected_status=200,
        max_latency_ms=1,  # 1ms: casi imposible de cumplir incluso mockeado
    )


# --- Tests de check_target ---

class TestCheckTarget:
    """Tests unitarios de check_target() con mocks HTTP."""

    @respx.mock  # Activa el mock: httpx no sale a internet dentro de este test
    async def test_ok_response(self, target_google: Target) -> None:
        """Debe devolver Verdict.OK cuando status y latencia son correctos."""
        # Definimos que GET a esa URL devuelve 200.
        respx.get("https://www.google.com").mock(return_value=httpx.Response(200))

        async with httpx.AsyncClient(timeout=5.0) as client:
            result = await check_target(client, target_google)

        assert result.verdict == Verdict.OK
        assert result.status_code == 200
        assert result.reasons == []
        assert result.latency_ms is not None
        assert result.latency_ms >= 0

    @respx.mock
    async def test_unexpected_status(self, target_google: Target) -> None:
        """Debe devolver FAIL si el status code no coincide con el esperado."""
        # Simulamos que el servidor devuelve 503 Service Unavailable.
        respx.get("https://www.google.com").mock(return_value=httpx.Response(503))

        async with httpx.AsyncClient(timeout=5.0) as client:
            result = await check_target(client, target_google)

        assert result.verdict == Verdict.FAIL
        assert result.status_code == 503
        # La razón debe mencionar el status inesperado.
        assert any("503" in r for r in result.reasons)

    @respx.mock
    async def test_timeout(self, target_google: Target) -> None:
        """Debe devolver FAIL con razón 'timeout' si httpx lanza TimeoutException."""
        # side_effect hace que la llamada lance una excepción en vez de responder.
        respx.get("https://www.google.com").mock(
            side_effect=httpx.TimeoutException("timeout simulado")
        )

        async with httpx.AsyncClient(timeout=5.0) as client:
            result = await check_target(client, target_google)

        assert result.verdict == Verdict.FAIL
        assert result.status_code is None
        assert result.latency_ms is None
        assert "timeout" in result.reasons

    @respx.mock
    async def test_network_error(self, target_google: Target) -> None:
        """Debe devolver FAIL si hay un error de red (DNS, conexión rechazada...)."""
        respx.get("https://www.google.com").mock(
            side_effect=httpx.ConnectError("conexión rechazada")
        )

        async with httpx.AsyncClient(timeout=5.0) as client:
            result = await check_target(client, target_google)

        assert result.verdict == Verdict.FAIL
        assert any("error de red" in r for r in result.reasons)

    @respx.mock
    async def test_result_fields(self, target_google: Target) -> None:
        """El resultado debe incluir nombre y URL del target."""
        respx.get("https://www.google.com").mock(return_value=httpx.Response(200))

        async with httpx.AsyncClient(timeout=5.0) as client:
            result = await check_target(client, target_google)

        assert result.name == "google"
        assert "google.com" in result.url


# --- Tests de run_checks ---

class TestRunChecks:
    """Tests de la función de orquestación."""

    @respx.mock
    async def test_all_ok(self) -> None:
        """run_checks debe devolver OK para todos si todos responden bien."""
        targets = [
            Target(name="a", url="https://a.example.com"),
            Target(name="b", url="https://b.example.com"),
        ]
        respx.get("https://a.example.com/").mock(return_value=httpx.Response(200))
        respx.get("https://b.example.com/").mock(return_value=httpx.Response(200))

        results = await run_checks(targets, timeout=5.0)

        assert len(results) == 2
        assert all(r.verdict == Verdict.OK for r in results)

    @respx.mock
    async def test_partial_failure(self) -> None:
        """Si uno falla, el resto sigue ejecutándose y aparece en los resultados."""
        targets = [
            Target(name="ok", url="https://ok.example.com"),
            Target(name="fail", url="https://fail.example.com"),
        ]
        respx.get("https://ok.example.com/").mock(return_value=httpx.Response(200))
        respx.get("https://fail.example.com/").mock(return_value=httpx.Response(500))

        results = await run_checks(targets, timeout=5.0)

        assert len(results) == 2
        ok_result = next(r for r in results if r.name == "ok")
        fail_result = next(r for r in results if r.name == "fail")
        assert ok_result.verdict == Verdict.OK
        assert fail_result.verdict == Verdict.FAIL

    @respx.mock
    async def test_empty_targets(self) -> None:
        """Con lista vacía debe devolver lista vacía sin errores."""
        results = await run_checks([], timeout=5.0)
        assert results == []

    @respx.mock
    async def test_preserves_order(self) -> None:
        """Los resultados deben mantener el mismo orden que los targets de entrada."""
        targets = [
            Target(name=f"target-{i}", url=f"https://t{i}.example.com")
            for i in range(5)
        ]
        for i in range(5):
            respx.get(f"https://t{i}.example.com/").mock(
                return_value=httpx.Response(200)
            )

        results = await run_checks(targets, timeout=5.0)

        # asyncio.gather() garantiza el orden, igual que los targets de entrada.
        for i, result in enumerate(results):
            assert result.name == f"target-{i}"
