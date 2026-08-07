"""Clima: previsão e normais históricas via Open-Meteo (sem chave), barômetro."""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from typing import Any

from app.config import settings
from app.infrastructure.http import client_pool

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

DAILY_FORECAST = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "pressure_msl_mean",
]
DAILY_ARCHIVE = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "pressure_msl_mean",
]

WEATHER_CODES: dict[int, tuple[str, str]] = {
    0: ("Céu limpo", "sun"),
    1: ("Predomínio de sol", "sun"),
    2: ("Parcialmente nublado", "cloud"),
    3: ("Encoberto", "cloud"),
    45: ("Nevoeiro", "fog"),
    48: ("Nevoeiro com geada", "fog"),
    51: ("Garoa fraca", "rain"),
    53: ("Garoa", "rain"),
    55: ("Garoa forte", "rain"),
    61: ("Chuva fraca", "rain"),
    63: ("Chuva", "rain"),
    65: ("Chuva forte", "rain"),
    66: ("Chuva congelante", "rain"),
    67: ("Chuva congelante forte", "rain"),
    71: ("Neve fraca", "snow"),
    73: ("Neve", "snow"),
    75: ("Neve forte", "snow"),
    80: ("Pancadas de chuva", "rain"),
    81: ("Pancadas de chuva fortes", "rain"),
    82: ("Tempestade", "storm"),
    95: ("Tempestade", "storm"),
    96: ("Tempestade com granizo", "storm"),
    99: ("Tempestade forte com granizo", "storm"),
}


def weather_label(code: int) -> str:
    return WEATHER_CODES.get(code, ("Condição desconhecida", "cloud"))[0]


def _round_dict(d: dict[str, Any], keys: tuple[str, ...], nd: int = 1) -> dict[str, Any]:
    out = dict(d)
    for k in keys:
        if out.get(k) is not None:
            out[k] = round(float(out[k]), nd)
    return out


def _last_10_full_years(today: date) -> tuple[str, str]:
    end_year = today.year - 1
    start_year = end_year - (settings.history_years - 1)
    return f"{start_year}-01-01", f"{end_year}-12-31"


async def fetch_forecast(lat: float, lng: float, days: int = 16) -> list[dict[str, Any]]:
    """Previsão diária (Open-Meteo), com cache em disco."""
    cache_file = settings.cache_dir / f"forecast_{lat:.3f}_{lng:.3f}.json"
    if cache_file.exists():
        age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if age < settings.cache_forecast_ttl:
            return json.loads(cache_file.read_text(encoding="utf-8"))

    params = {
        "latitude": lat,
        "longitude": lng,
        "daily": ",".join(DAILY_FORECAST),
        "timezone": "auto",
        "forecast_days": days,
    }
    async with client_pool() as client:
        resp = await client.get(FORECAST_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

    daily = data.get("daily", {})
    days_list: list[dict[str, Any]] = []
    for i, day in enumerate(daily.get("time", [])):
        raw_code = daily["weather_code"][i]
        code = int(raw_code) if raw_code is not None else -1
        label, icon = WEATHER_CODES.get(code, ("Condição desconhecida", "cloud"))
        days_list.append(
            {
                "date": day,
                "weather_code": code,
                "weather": label,
                "icon": icon,
                "tmax": daily["temperature_2m_max"][i],
                "tmin": daily["temperature_2m_min"][i],
                "precip_mm": daily["precipitation_sum"][i],
                "precip_prob": daily["precipitation_probability_max"][i],
                "wind_kmh": daily["wind_speed_10m_max"][i],
                "pressure_hpa": daily["pressure_msl_mean"][i],
            }
        )
    cache_file.write_text(json.dumps(days_list, ensure_ascii=False), encoding="utf-8")
    return days_list


async def fetch_history(lat: float, lng: float) -> dict[str, Any]:
    """Histórico diário dos últimos 10 anos + normais mensais (cache longo)."""
    cache_file = settings.cache_dir / f"history_{lat:.3f}_{lng:.3f}.json"
    if cache_file.exists():
        age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if age < settings.cache_history_ttl:
            return json.loads(cache_file.read_text(encoding="utf-8"))

    start, end = _last_10_full_years(date.today())
    params = {
        "latitude": lat,
        "longitude": lng,
        "start_date": start,
        "end_date": end,
        "daily": ",".join(DAILY_ARCHIVE),
        "timezone": "auto",
    }
    async with client_pool() as client:
        resp = await client.get(ARCHIVE_URL, params=params, timeout=90)
        resp.raise_for_status()
        data = resp.json()

    daily = data.get("daily", {})
    times = daily.get("time", [])
    if not times:
        raise RuntimeError("Open-Meteo não retornou histórico")

    # Chuva agrupada por (ano, mês) para normal em mm/mês (total mensal,
    # não média diária); pressão/temperatura seguem como médias diárias.
    rain_buckets: dict[tuple[int, int], list[float]] = {}
    pressure_by_month: dict[str, list[float]] = {f"{m:02d}": [] for m in range(1, 13)}
    temp_max_by_month: dict[str, list[float]] = {f"{m:02d}": [] for m in range(1, 13)}
    temp_min_by_month: dict[str, list[float]] = {f"{m:02d}": [] for m in range(1, 13)}
    rain_days = 0
    total_rain = 0.0
    for i, day in enumerate(times):
        d = datetime.fromisoformat(day)
        month = f"{d.month:02d}"
        p = float(daily["precipitation_sum"][i] or 0.0)
        rain_buckets.setdefault((d.year, d.month), []).append(p)
        total_rain += p
        if p >= 1.0:
            rain_days += 1
        if daily.get("pressure_msl_mean") and daily["pressure_msl_mean"][i] is not None:
            pressure_by_month[month].append(float(daily["pressure_msl_mean"][i]))
        if daily.get("temperature_2m_max") and daily["temperature_2m_max"][i] is not None:
            temp_max_by_month[month].append(float(daily["temperature_2m_max"][i]))
        if daily.get("temperature_2m_min") and daily["temperature_2m_min"][i] is not None:
            temp_min_by_month[month].append(float(daily["temperature_2m_min"][i]))

    month_rain_totals: dict[str, list[float]] = {f"{m:02d}": [] for m in range(1, 13)}
    for (_, mo), vals in sorted(rain_buckets.items()):
        month_rain_totals[f"{mo:02d}"].append(sum(vals))

    def stats(values: list[float]) -> dict[str, float] | None:
        if not values:
            return None
        values.sort()
        n = len(values)
        def q(p: float) -> float:
            idx = max(0, min(n - 1, int(p * n)))
            return values[idx]
        return {
            "mean": round(sum(values) / n, 1),
            "p10": round(q(0.10), 1),
            "p90": round(q(0.90), 1),
        }

    normals = []
    for m in range(1, 13):
        key = f"{m:02d}"
        normals.append(
            {
                "month": m,
                "rain_mm": stats(month_rain_totals[key]),
                "pressure_hpa": stats(pressure_by_month[key]),
                "tmax": stats(temp_max_by_month[key]),
                "tmin": stats(temp_min_by_month[key]),
            }
        )

    months_mean = [stats(month_rain_totals[f"{m:02d}"]) for m in range(1, 13)]
    wettest = max(range(1, 13), key=lambda m: (months_mean[m - 1] or {"mean": 0})["mean"])
    driest = min(range(1, 13), key=lambda m: (months_mean[m - 1] or {"mean": 0})["mean"])

    result = {
        "start": start,
        "end": end,
        "years": settings.history_years,
        "total_rain_mm": round(total_rain, 1),
        "rain_days": rain_days,
        "wettest_month": wettest,
        "driest_month": driest,
        "monthly_normals": normals,
    }
    cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def barometer_analysis(
    forecast: list[dict[str, Any]], history: dict[str, Any] | None
) -> dict[str, Any]:
    """Análise de pressão: tendência recente + comparação com a normal do mês."""
    pressures = [d["pressure_hpa"] for d in forecast[:5] if d.get("pressure_hpa") is not None]
    if not pressures:
        return {"status": "sem dados", "trend": 0.0, "note": "Pressão não disponível."}

    latest = pressures[0]
    slope = (pressures[-1] - pressures[0]) / max(1, len(pressures) - 1)
    trend_hpa_3d = slope * 3

    month = datetime.now().month
    normal = None
    if history:
        norm = history["monthly_normals"][month - 1].get("pressure_hpa")
        if norm:
            normal = norm["mean"]

    if trend_hpa_3d <= -2.0:
        status = "em queda"
        note = "Pressão caindo: frente fria/chuvosa se aproximando. Evite aplicar defensivos em dias de chuva iminente."
    elif trend_hpa_3d >= 2.0:
        status = "em alta"
        note = "Pressão subindo: tempo firme tendendo a seco. Janela favorável para plantio, colheita e aplicações."
    else:
        status = "estável"
        note = "Pressão estável: condições meteorológicas sem mudança brusca prevista."

    delta_normal = (latest - normal) if normal else None
    return {
        "status": status,
        "latest_hpa": round(latest, 1),
        "trend_3d_hpa": round(trend_hpa_3d, 1),
        "normal_hpa": round(normal, 1) if normal else None,
        "delta_normal_hpa": round(delta_normal, 1) if delta_normal is not None else None,
        "note": note,
    }


async def climate_bundle(lat: float, lng: float, days: int = 16) -> dict[str, Any]:
    """Agrega previsão + histórico + barômetro em uma chamada (com paralelismo)."""
    forecast_task = asyncio.create_task(fetch_forecast(lat, lng, days=days))
    history_task = asyncio.create_task(fetch_history(lat, lng))
    forecast, history = await asyncio.gather(forecast_task, history_task)
    barometer = barometer_analysis(forecast, history)
    return {
        "forecast": forecast,
        "history": history,
        "barometer": barometer,
        "source_forecast": "Open-Meteo",
        "source_history": f"Open-Meteo ERA5 ({history['start']} a {history['end']})",
    }
