"""Análise completa de uma localidade: clima + lua + maré + ZARC + custos + recomendação."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.domain import astronomy, climate, locations, recommendation, zarc
from app.domain import costs as costs_domain
from app.domain import crops as crops_domain
from app.domain.units import AreaUnit
from app.infrastructure import db


def _tide_spring_range(lat: float) -> float:
    """Amplitude de sizígia de referência (m). Costeiro ~1,5 m; interior ~0,2 m."""
    # Heurística simples: latitude baixa + litorânea não detectável aqui —
    # usamos o padrão configurável e avisamos quando for baixo.
    return 1.5 if abs(lat) < 8 else 1.2


async def _astronomy_payload(
    lat: float, lng: float, forecast: list[dict[str, Any]], days: int = 5
) -> dict[str, Any]:
    try:
        tz = ZoneInfo("America/Sao_Paulo")
    except Exception:
        tz = None  # fallback: horário local como UTC (sem tzdata instalado)
    now = datetime.now(tz) if tz else datetime.now()

    moon_today = astronomy.moon_info(now)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # Fases principais sempre dentro do horizonte de 60 dias (a janela da
    # previsão é curta demais para capturar o ciclo de ~29,5 dias).
    phases = astronomy.primary_phases_in_range(start, start + timedelta(days=60))

    tides = []
    for i in range(days):
        day = (now + timedelta(days=i)).replace(hour=12, minute=0, second=0)
        tides.append(
            astronomy.tide_day_estimate(
                day, longitude_east_deg=lng, spring_range_m=_tide_spring_range(lat), tz=tz
            )
        )

    # Enriquece a previsão com a fase lunar de cada dia (para a recomendação).
    for day in forecast:
        try:
            d = date.fromisoformat(day["date"])
            moon = astronomy.moon_info(datetime(d.year, d.month, d.day, 12, tzinfo=tz))
            day["moon_phase_name"] = moon["phase_name"]
            day["illumination"] = moon["illumination"]
        except (ValueError, KeyError):
            day["moon_phase_name"] = "Lua Cheia"
            day["illumination"] = None

    return {
        "lua_hoje": moon_today,
        "fases_principais_proximas": phases[:8],
        "mare_proximos_dias": tides,
        "mare_note": (
            "Estimativa simplificada de equilíbrio. Para o litoral consulte a tábua "
            "da Marinha; no interior a maré não afeta as operações agrícolas."
        ),
    }


def _crop_analysis(crop: dict[str, Any], region: str, uf: str, city_slug: str, muni: dict[str, Any],
                   climate_payload: dict[str, Any], astro: dict[str, Any],
                   area: float | None, unit: AreaUnit | None) -> dict[str, Any]:
    forecast = climate_payload["forecast"]
    barometer = climate_payload["barometer"]
    history = climate_payload["history"]

    status = crops_domain.crop_status(crop, region, date.today())
    zarc_summary = zarc.zarc_summary(crop, region, uf, city_slug, history)
    best = recommendation.best_days(forecast, crop, region, barometer)
    harvest = recommendation.harvest_window(forecast, crop, region)
    cost = costs_domain.cost_breakdown(crop, area, unit) if area is not None and unit else None

    planting = date.today()
    for b in best["melhores"]:
        planting = date.fromisoformat(b["date"])
        break
    harvest_est = crops_domain.harvest_estimate(crop, region, planting)

    return {
        "crop": crop,
        "status": status,
        "zarc": zarc_summary,
        "melhores_dias": best,
        "colheita": harvest,
        "colheita_estimada": harvest_est,
        "custos": cost,
    }


async def full_analysis(
    ibge: str,
    crop_slug: str | None = None,
    area: float | None = None,
    unit: AreaUnit | None = None,
) -> dict[str, Any]:
    """Orquestra a análise completa de um município."""
    muni = locations.get_municipio(ibge)
    if muni is None:
        raise LookupError(f"Município IBGE {ibge} não encontrado.")

    uf = muni["uf"]
    region = crops_domain.region_for_uf(uf)
    city_slug = locations._normalize(muni["nome"]).lower().replace(" ", "-")

    climate_payload = await climate.climate_bundle(muni["lat"], muni["lng"])
    astro = await _astronomy_payload(muni["lat"], muni["lng"], climate_payload["forecast"])

    await db.record_search(uf, muni["nome"], muni["lat"], muni["lng"], crop_slug)

    crops = crops_domain.get_crops()
    summary = [
        {
            "slug": c["slug"],
            "nome": c["nome"],
            "grupo": c["grupo"],
            "status": crops_domain.crop_status(c, region, date.today())["status"],
            "janela_label": crops_domain.crop_status(c, region, date.today())["plantio_meses_label"],
        }
        for c in crops
    ]

    selected = None
    if crop_slug:
        crop = crops_domain.get_crop(crop_slug)
        if crop is None:
            raise LookupError(f"Cultura '{crop_slug}' não encontrada.")
        selected = _crop_analysis(crop, region, uf, city_slug, muni, climate_payload, astro, area, unit)

    return {
        "local": {**muni, "regiao_nome": crops_domain.REGION_NAMES.get(region, region)},
        "region": region,
        "clima": climate_payload,
        "astronomia": astro,
        "culturas_resumo": summary,
        "cultura_detalhe": selected,
        "fonte_pressao": "Open-Meteo (sem chave). ClimaTempo não expõe pressão no plano padrão.",
    }
