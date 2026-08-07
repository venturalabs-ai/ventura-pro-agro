"""Testes de domínio: fases lunares, normais de chuva (totais mensais) e conversões."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.domain import astronomy
from app.domain import units as units_domain
from app.domain.climate import fetch_history
from app.domain.crops import get_crop, get_crops

PHASE_BOUNDARIES = [
    (0.0, "Lua Nova"),
    (10.0, "Lua Nova"),
    (22.4, "Lua Nova"),
    (22.5, "Lua Crescente"),
    (67.4, "Lua Crescente"),
    (67.5, "Quarto Crescente"),
    (90.0, "Quarto Crescente"),
    (112.4, "Quarto Crescente"),
    (112.5, "Lua Crescente Gibosa"),
    (157.4, "Lua Crescente Gibosa"),
    (157.5, "Lua Cheia"),
    (180.0, "Lua Cheia"),
    (202.4, "Lua Cheia"),
    (202.5, "Lua Minguante Gibosa"),
    (247.4, "Lua Minguante Gibosa"),
    (247.5, "Quarto Minguante"),
    (292.4, "Quarto Minguante"),
    (292.5, "Lua Minguante"),
    (337.4, "Lua Minguante"),
    (337.5, "Lua Nova"),
    (359.0, "Lua Nova"),
]


def test_phase_name_boundaries() -> None:
    for elong, expected in PHASE_BOUNDARIES:
        assert astronomy.phase_name(elong) == expected, f"elong={elong} -> {expected}"


def test_phase_name_wraps_mod_360() -> None:
    assert astronomy.phase_name(360.0 + 90.0) == "Quarto Crescente"
    assert astronomy.phase_name(-67.5) == "Lua Minguante"  # -67,5 ≡ 292,5


def test_moon_info_illumination_consistent_with_phase() -> None:
    # Lua Nova: iluminação ~0; Lua Cheia: ~100.
    dt = datetime(2026, 1, 20, 12, tzinfo=UTC)  # data arbitrária de referência
    info = astronomy.moon_info(dt)
    assert 0.0 <= info["illumination"] <= 100.0
    assert 0.0 <= info["phase_deg"] < 360.0
    assert info["phase_name"] == astronomy.phase_name(info["phase_deg"])


class _FakeResponse:
    def __init__(self, data: dict) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._data


class _FakeClient:
    def __init__(self, data: dict) -> None:
        self._data = data

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def get(self, url: str, **kwargs: object) -> _FakeResponse:
        assert url.endswith("/archive")
        return _FakeResponse(self._data)


def _archive_payload() -> dict:
    """Payload sintético: janeiro chuvoso (~300 mm/ano), julho seco (~20 mm/ano)."""
    times, rain, tmax, tmin, pressure = [], [], [], [], []
    for year in range(2016, 2026):
        for month in range(1, 13):
            for day in range(1, 29):
                times.append(f"{year}-{month:02d}-{day:02d}")
                if month == 1:
                    rain.append(10.0)
                elif month == 7:
                    rain.append(0.0)
                else:
                    rain.append(5.0)
                tmax.append(28.0)
                tmin.append(18.0)
                pressure.append(1013.0)
    return {
        "daily": {
            "time": times,
            "precipitation_sum": rain,
            "temperature_2m_max": tmax,
            "temperature_2m_min": tmin,
            "pressure_msl_mean": pressure,
        }
    }


def test_fetch_history_rain_normals_are_monthly_totals(monkeypatch, tmp_path) -> None:
    """A normal de chuva deve ser o total mensal (mm/mês), não a média diária."""
    import app.domain.climate as climate_mod

    monkeypatch.setattr(climate_mod.settings, "runtime_dir", tmp_path)
    monkeypatch.setattr(climate_mod, "client_pool", lambda: _FakeClient(_archive_payload()))
    hist = asyncio.run(fetch_history(-22.9053, -47.0659))

    normals = {n["month"]: n["rain_mm"]["mean"] for n in hist["monthly_normals"]}
    # 10 anos x 28 dias de janeiro x 10 mm = 280 mm/mês; julho = 0 mm/mês.
    assert normals[1] == 280.0
    assert normals[7] == 0.0
    assert hist["wettest_month"] == 1
    assert hist["driest_month"] == 7


def test_fetch_history_skips_null_precip(monkeypatch, tmp_path) -> None:
    """Valores nulos de precipitação contam como zero sem quebrar."""
    import app.domain.climate as climate_mod

    monkeypatch.setattr(climate_mod.settings, "runtime_dir", tmp_path)
    payload = _archive_payload()
    payload["daily"]["precipitation_sum"][5] = None  # 2016-01-06 vira 0 mm
    monkeypatch.setattr(climate_mod, "client_pool", lambda: _FakeClient(payload))
    hist = asyncio.run(fetch_history(-22.9053, -47.0659))
    assert hist["monthly_normals"][0]["rain_mm"]["mean"] == 279.0


def test_area_conversions() -> None:
    assert units_domain.to_m2(1.0, "ha") == 10_000.0
    assert units_domain.to_ha(1.0, "alq_paulista") == 2.42
    assert units_domain.to_ha(1.0, "alq_mineiro") == 4.84
    assert units_domain.convert(1.0, "alq_baiano", "ha") == 9.68
    assert units_domain.cost_per(10.0, "ha", 150_000.0) == 15_000.0


def test_crops_knowledge_base_loads() -> None:
    crops = get_crops()
    slugs = {c["slug"] for c in crops}
    for required in ("soja", "milho", "cafe", "cana", "arroz", "feijao"):
        assert required in slugs
    soja = get_crop("soja")
    assert soja is not None
    assert soja["saca_kg"] == 60
    assert {"N", "NE", "CO", "SE", "S"} <= set(soja["janelas_plantio"].keys())
