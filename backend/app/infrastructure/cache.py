"""Cache em disco simples (JSON) com TTL, compartilhado entre módulos."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.config import settings


def cache_get(
    kind: str,
    key: str,
    ttl: int | None = None,
    *,
    cache_dir: Path | None = None,
) -> Any | None:
    """Lê um payload JSON do cache. Retorna None se ausente/expirado."""
    ttl = settings.cache_forecast_ttl if ttl is None else ttl
    cache_file = (cache_dir or settings.cache_dir) / f"{kind}_{_safe(key)}.json"
    if not cache_file.exists():
        return None
    age = time.time() - cache_file.stat().st_mtime
    if age >= ttl:
        return None
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def cache_set(kind: str, key: str, payload: Any, *, cache_dir: Path | None = None) -> Path:
    """Grava um payload JSON no cache e retorna o arquivo criado."""
    cache_file = (cache_dir or settings.cache_dir) / f"{kind}_{_safe(key)}.json"
    cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return cache_file


def cache_or_fetch(
    kind: str,
    key: str,
    fetch: Callable[[], Any],
    ttl: int | None = None,
    *,
    cache_dir: Path | None = None,
) -> Any:
    """Cache-aside síncrono: usa o valor em cache ou chama `fetch` e grava."""
    cached = cache_get(kind, key, ttl, cache_dir=cache_dir)
    if cached is not None:
        return cached
    payload = fetch()
    cache_set(kind, key, payload, cache_dir=cache_dir)
    return payload


def _safe(key: str) -> str:
    """Sanitiza chave para uso como nome de arquivo."""
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in key)
