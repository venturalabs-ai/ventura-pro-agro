"""Conector da API oficial ClimaTempo (apiadvisor.climatempo.com.br).

Requer token (plano ClimaTempo for Partners). Sem token, o sistema usa
Open-Meteo como fonte de previsão (ver `app.domain.climate`).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.config import settings
from app.infrastructure.http import client_pool

API_BASE = "https://apiadvisor.climatempo.com.br/api/v1"
SEARCH_URL = f"{API_BASE}/search/locale"
FORECAST_URL = f"{API_BASE}/forecast/locale"


def _cache_key(kind: str, key: str) -> Any:
    cache_file = settings.cache_dir / f"ttempo_{kind}_{key}.json"
    if cache_file.exists():
        age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if age < settings.cache_ttempo_ttl:
            return json.loads(cache_file.read_text(encoding="utf-8"))
    return None


def _cache_set(kind: str, key: str, payload: Any) -> None:
    cache_file = settings.cache_dir / f"ttempo_{kind}_{key}.json"
    cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


async def search_city(city_name: str, uf: str) -> dict[str, Any] | None:
    """Busca o id da cidade na base ClimaTempo."""
    token = settings.climatempo_token
    if not token:
        return None
    cached = _cache_key("search", f"{city_name.lower()}_{uf}")
    if cached is not None:
        return cached or None
    params = {"city": city_name, "token": token}
    async with client_pool() as client:
        resp = await client.get(SEARCH_URL, params=params, timeout=20)
        if resp.status_code != 200:
            return None
        try:
            data = resp.json()
        except Exception:
            return None
    # data é lista de cidades
    if not isinstance(data, list):
        return None
    matches = [c for c in data if str(c.get("state")) == uf]
    chosen = matches[0] if matches else (data[0] if data else None)
    _cache_set("search", f"{city_name.lower()}_{uf}", chosen)
    return chosen


async def fetch_forecast(lat: float, lng: float, city_name: str, uf: str, days: int = 15) -> list[dict[str, Any]] | None:
    """Previsão 15 dias ClimaTempo normalizada. Retorna None se não houver token."""
    token = settings.climatempo_token
    if not token:
        return None
    locale = await search_city(city_name, uf)
    if not locale or not locale.get("id"):
        return None
    locale_id = locale["id"]
    cached = _cache_key("forecast", str(locale_id))
    if cached is not None:
        return cached

    params = {"token": token}
    async with client_pool() as client:
        resp = await client.get(f"{FORECAST_URL}/{locale_id}/days/{days}", params=params, timeout=25)
        if resp.status_code != 200:
            return None
        data = resp.json()

    out: list[dict[str, Any]] = []
    for item in data.get("data", []):
        rain = item.get("rain", {})
        prob = item.get("probability", {})
        out.append(
            {
                "date": item.get("date"),
                "weather": item.get("text_icon", {}).get("text", {}).get("pt", ""),
                "icon": item.get("text_icon", {}).get("icon"),
                "tmax": item.get("temperature", {}).get("max"),
                "tmin": item.get("temperature", {}).get("min"),
                "precip_mm": rain.get("precipitation"),
                "precip_prob": prob.get("precipitation"),
                "wind_kmh": item.get("wind", {}).get("velocity"),
                "pressure_hpa": None,  # ClimaTempo não expõe pressão no plano padrão
                "source": "ClimaTempo",
            }
        )
    _cache_set("forecast", str(locale_id), out)
    return out


def available() -> bool:
    return bool(settings.climatempo_token)
