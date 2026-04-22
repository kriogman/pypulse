"""
checker.py — Lógica central: chequear un endpoint HTTP y devolver el resultado.

Aquí vive todo lo relacionado con asyncio y httpx.
Lee los comentarios para entender por qué async es natural para este caso.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum

import httpx

from pulse.config import Target


class Verdict(str, Enum):
    """
    Resultado final del check.

    Hereda de str para que json.dumps() lo serialice como "OK"/"FAIL"
    sin necesidad de un encoder custom.
    """

    OK = "OK"
    FAIL = "FAIL"


@dataclass
class CheckResult:
    """
    Resultado de chequear un Target.

    @dataclass genera automáticamente __init__, __repr__ y __eq__
    a partir de los campos declarados con type hints. Sin @dataclass
    tendríamos que escribir def __init__(self, name, url, ...) a mano.
    """

    name: str
    url: str
    status_code: int | None  # None si hubo timeout u otro error de red
    latency_ms: float | None
    verdict: Verdict
    reasons: list[str] = field(default_factory=list)  # Lista de motivos de fallo


async def check_target(client: httpx.AsyncClient, target: Target) -> CheckResult:
    """
    Chequea un único target y devuelve su CheckResult.

    Esta es una función ASYNC (async def). No ejecuta nada por sí sola:
    devuelve un objeto "coroutine" que el event loop ejecutará cuando
    hagamos `await check_target(...)`.

    Por qué async aquí:
    - Una llamada HTTP implica esperar la respuesta de la red (I/O bound).
    - Con await, mientras esperamos la red, el event loop puede ejecutar
      OTROS checks en paralelo. No bloqueamos el hilo.
    - Con threads haríamos lo mismo pero con overhead de memoria y
      sincronización. asyncio es más ligero para I/O.

    Args:
        client: Cliente httpx compartido entre todos los checks.
                Reutilizar el cliente es importante: gestiona connection pools,
                keeps-alive, y evita overhead de crear sockets nuevos.
        target: El endpoint a chequear.
    """
    reasons: list[str] = []
    status_code: int | None = None
    latency_ms: float | None = None

    try:
        # time.perf_counter() es el reloj de alta precisión de Python para medir
        # intervalos cortos. No uses time.time() para latencias (menos preciso).
        start = time.perf_counter()

        # `await` aquí significa: "lanza la petición HTTP y devuelve el control
        # al event loop hasta que llegue la respuesta". Mientras esperamos,
        # el event loop puede avanzar con otros checks.
        response = await client.get(target.url_str)

        # Una vez que llegó la respuesta, continuamos aquí.
        elapsed_s = time.perf_counter() - start
        latency_ms = elapsed_s * 1000  # Convertir segundos a milisegundos

        status_code = response.status_code

        # Verificamos las condiciones de éxito.
        if status_code != target.expected_status:
            reasons.append(
                f"status {status_code} != esperado {target.expected_status}"
            )

        if latency_ms > target.max_latency_ms:
            reasons.append(
                f"latencia {latency_ms:.0f}ms > máximo {target.max_latency_ms}ms"
            )

    except httpx.TimeoutException:
        # TimeoutException cubre: connect timeout, read timeout, pool timeout.
        # El timeout global viene del AsyncClient (configurado en cli.py).
        reasons.append("timeout")

    except httpx.RequestError as exc:
        # RequestError cubre errores de red: DNS no resuelve, conexión rechazada, etc.
        # exc es el objeto excepción; type(exc).__name__ da el nombre de la clase.
        reasons.append(f"error de red: {type(exc).__name__}")

    verdict = Verdict.OK if not reasons else Verdict.FAIL

    return CheckResult(
        name=target.name,
        url=target.url_str,
        status_code=status_code,
        latency_ms=latency_ms,
        verdict=verdict,
        reasons=reasons,
    )


async def run_checks(
    targets: list[Target], timeout: float
) -> list[CheckResult]:
    """
    Ejecuta todos los checks EN PARALELO y devuelve los resultados.

    asyncio.gather() es la clave: toma varias coroutines y las ejecuta
    de forma concurrente en el mismo event loop (mismo hilo).

    Diferencia con threads:
    - Threads: paralelismo real (varios hilos del SO), overhead de contexto,
      necesitas locks para datos compartidos.
    - asyncio: concurrencia cooperativa (un solo hilo), cada coroutine cede
      el control con `await`. Para I/O bound (HTTP) es igual de rápido
      y mucho más simple.

    Args:
        targets: Lista de endpoints a chequear.
        timeout: Segundos máximos por petición HTTP.
    """
    # httpx.Timeout() configura los timeouts por fase de la petición.
    # timeout=X aplica el mismo valor a connect, read, write y pool.
    # Lo usamos como context manager (async with) para que cierre
    # los sockets correctamente al salir.
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        follow_redirects=True,  # Seguir 301/302 automáticamente
    ) as client:
        # Creamos una lista de coroutines (tareas pendientes de ejecutar).
        # IMPORTANTE: esto NO ejecuta los checks todavía, solo los define.
        tasks = [check_target(client, target) for target in targets]

        # asyncio.gather() lanza todas las coroutines "a la vez" y espera
        # a que TODAS terminen. Devuelve los resultados en el mismo orden
        # que la lista de entrada.
        results: list[CheckResult] = await asyncio.gather(*tasks)

    return results
