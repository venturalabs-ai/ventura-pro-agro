"""Pool de clientes HTTP compartilhado (httpx) e utilitários de rede."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

import httpx

_USER_AGENT = "VenturaProAgro/0.1 (Windows desktop + mobile PWA)"


@contextlib.asynccontextmanager
async def client_pool(
    *,
    timeout: float = 30.0,
    retries: int = 2,
    retry_backoff: float = 1.0,
) -> AsyncIterator[httpx.AsyncClient]:
    """Cliente HTTP reutilizável com retry simples para falhas transientes.

    Uso:
        async with client_pool() as client:
            resp = await client.get(url, params=..., timeout=30)
    """
    transport = httpx.AsyncHTTPTransport(retries=retries)
    async with httpx.AsyncClient(
        transport=transport,
        timeout=httpx.Timeout(timeout),
        headers={"User-Agent": _USER_AGENT},
        follow_redirects=True,
    ) as client:
        yield client
