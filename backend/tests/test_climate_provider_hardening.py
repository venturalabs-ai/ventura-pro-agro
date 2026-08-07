"""Offline regression coverage for climate providers, caching and fallbacks."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

import app.domain.climate as climate
import app.domain.climatempo as climatempo


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


@asynccontextmanager
async def pool_for(client):
    yield client


def install_pool(monkeypatch: pytest.MonkeyPatch, module, client: FakeClient):
    monkeypatch.setattr(module, "client_pool", lambda: pool_for(client))


def configure_cache(monkeypatch: pytest.MonkeyPatch, module, tmp_path: Path):
    # Pydantic BaseModel intercepts setattr before a property setter. Override the
    # declared PrivateAttr instead so every test uses an isolated cache directory.
    monkeypatch.setattr(module.settings, "_cache_dir_override", tmp_path)
    if module is climate:
        monkeypatch.setattr(module.settings, "cache_forecast_ttl", 3600)
        monkeypatch.setattr(module.settings, "cache_history_ttl", 3600)
    else:
        monkeypatch.setattr(module.settings, "cache_ttempo_ttl", 3600)


def test_weather_helpers_and_year_window(monkeypatch: pytest.MonkeyPatch):
    assert climate.weather_label(0) == "Céu limpo"
    assert climate.weather_label(999) == "Condição desconhecida"
    assert climate._round_dict({"x": 1.234, "y": None}, ("x", "y")) == {"x": 1.2, "y": None}
    monkeypatch.setattr(climate.settings, "history_years", 10)
    assert climate._last_10_full_years(date(2026, 8, 7)) == ("2016-01-01", "2025-12-31")


@pytest.mark.asyncio
async def test_open_meteo_forecast_network_normalization_and_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    configure_cache(monkeypatch, climate, tmp_path)
    payload = {
        "daily": {
            "time": ["2026-08-07", "2026-08-08"],
            "weather_code": [0, None],
            "temperature_2m_max": [28.5, 27.0],
            "temperature_2m_min": [18.0, 19.0],
            "precipitation_sum": [0.0, 3.2],
            "precipitation_probability_max": [5, 70],
            "wind_speed_10m_max": [11.0, 20.0],
            "pressure_msl_mean": [1018.0, 1013.0],
        }
    }
    client = FakeClient([FakeResponse(payload)])
    install_pool(monkeypatch, climate, client)

    result = await climate.fetch_forecast(-22.4, -41.8, days=2)
    assert result[0]["weather"] == "Céu limpo"
    assert result[1]["weather_code"] == -1
    assert result[1]["weather"] == "Condição desconhecida"
    assert client.calls[0][1]["params"]["forecast_days"] == 2

    cached = await climate.fetch_forecast(-22.4, -41.8, days=2)
    assert cached == result
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_open_meteo_forecast_propagates_http_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    configure_cache(monkeypatch, climate, tmp_path)
    client = FakeClient([FakeResponse({}, status_code=503)])
    install_pool(monkeypatch, climate, client)
    with pytest.raises(RuntimeError, match="503"):
        await climate.fetch_forecast(0, 0)


@pytest.mark.asyncio
async def test_history_builds_normals_and_uses_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    configure_cache(monkeypatch, climate, tmp_path)
    monkeypatch.setattr(climate.settings, "history_years", 2)
    payload = {
        "daily": {
            "time": ["2024-01-01", "2024-01-02", "2024-02-01", "2025-01-01", "2025-02-01"],
            "precipitation_sum": [5.0, 0.0, 10.0, 15.0, 2.0],
            "pressure_msl_mean": [1010.0, 1012.0, None, 1014.0, 1011.0],
            "temperature_2m_max": [30.0, 31.0, 29.0, 32.0, 28.0],
            "temperature_2m_min": [20.0, 21.0, 19.0, 22.0, 18.0],
            "weather_code": [0, 0, 61, 1, 2],
        }
    }
    client = FakeClient([FakeResponse(payload)])
    install_pool(monkeypatch, climate, client)

    result = await climate.fetch_history(-22.4, -41.8)
    assert result["years"] == 2
    assert result["total_rain_mm"] == 32.0
    assert result["rain_days"] == 4
    assert len(result["monthly_normals"]) == 12
    assert result["monthly_normals"][0]["rain_mm"] is not None

    cached = await climate.fetch_history(-22.4, -41.8)
    assert cached == result
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_history_rejects_empty_provider_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    configure_cache(monkeypatch, climate, tmp_path)
    client = FakeClient([FakeResponse({"daily": {"time": []}})])
    install_pool(monkeypatch, climate, client)
    with pytest.raises(RuntimeError, match="não retornou histórico"):
        await climate.fetch_history(1, 2)


def test_barometer_all_statuses():
    assert climate.barometer_analysis([], None)["status"] == "sem dados"

    falling = [{"pressure_hpa": value} for value in [1015, 1014, 1013, 1012, 1011]]
    assert climate.barometer_analysis(falling, None)["status"] == "em queda"

    rising = [{"pressure_hpa": value} for value in [1010, 1011, 1012, 1013, 1014]]
    assert climate.barometer_analysis(rising, None)["status"] == "em alta"

    stable = [{"pressure_hpa": value} for value in [1012, 1012.1, 1012.0]]
    month = datetime.now().month
    normals = [{"pressure_hpa": None} for _ in range(12)]
    normals[month - 1] = {"pressure_hpa": {"mean": 1010.0}}
    result = climate.barometer_analysis(stable, {"monthly_normals": normals})
    assert result["status"] == "estável"
    assert result["normal_hpa"] == 1010.0
    assert result["delta_normal_hpa"] == 2.0


@pytest.mark.asyncio
async def test_climate_bundle_parallel_aggregation(monkeypatch: pytest.MonkeyPatch):
    forecast = [{"pressure_hpa": 1012.0}]
    history = {"start": "2016-01-01", "end": "2025-12-31", "monthly_normals": [{"pressure_hpa": None}] * 12}
    monkeypatch.setattr(climate, "fetch_forecast", AsyncMock(return_value=forecast))
    monkeypatch.setattr(climate, "fetch_history", AsyncMock(return_value=history))
    bundle = await climate.climate_bundle(-22, -41, days=7)
    assert bundle["forecast"] == forecast
    assert bundle["history"] == history
    assert bundle["source_forecast"] == "Open-Meteo"
    assert "ERA5" in bundle["source_history"]


def test_climatempo_cache_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    configure_cache(monkeypatch, climatempo, tmp_path)
    assert climatempo._cache_key("search", "missing") is None
    climatempo._cache_set("search", "city", {"id": 10})
    assert climatempo._cache_key("search", "city") == {"id": 10}


@pytest.mark.asyncio
async def test_climatempo_without_token_is_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    configure_cache(monkeypatch, climatempo, tmp_path)
    monkeypatch.setattr(climatempo.settings, "climatempo_token", None)
    assert climatempo.available() is False
    assert await climatempo.search_city("Macae", "RJ") is None
    assert await climatempo.fetch_forecast(-22, -41, "Macae", "RJ") is None


@pytest.mark.asyncio
async def test_climatempo_search_success_cache_and_error_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    configure_cache(monkeypatch, climatempo, tmp_path)
    monkeypatch.setattr(climatempo.settings, "climatempo_token", "token")
    assert climatempo.available() is True

    client = FakeClient([FakeResponse([{"id": 1, "state": "SP"}, {"id": 2, "state": "RJ"}])])
    install_pool(monkeypatch, climatempo, client)
    chosen = await climatempo.search_city("Macae", "RJ")
    assert chosen["id"] == 2
    assert (await climatempo.search_city("Macae", "RJ"))["id"] == 2
    assert len(client.calls) == 1

    install_pool(monkeypatch, climatempo, FakeClient([FakeResponse({}, status_code=500)]))
    assert await climatempo.search_city("Outra", "RJ") is None
    install_pool(monkeypatch, climatempo, FakeClient([FakeResponse(ValueError("bad json"))]))
    assert await climatempo.search_city("Invalid", "RJ") is None
    install_pool(monkeypatch, climatempo, FakeClient([FakeResponse({"unexpected": True})]))
    assert await climatempo.search_city("Shape", "RJ") is None


@pytest.mark.asyncio
async def test_climatempo_forecast_normalization_cache_and_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    configure_cache(monkeypatch, climatempo, tmp_path)
    monkeypatch.setattr(climatempo.settings, "climatempo_token", "token")
    monkeypatch.setattr(climatempo, "search_city", AsyncMock(return_value={"id": 77}))
    payload = {
        "data": [
            {
                "date": "2026-08-07",
                "text_icon": {"text": {"pt": "Sol"}, "icon": "1"},
                "temperature": {"max": 30, "min": 20},
                "rain": {"precipitation": 1.5},
                "probability": {"precipitation": 40},
                "wind": {"velocity": 12},
            }
        ]
    }
    client = FakeClient([FakeResponse(payload)])
    install_pool(monkeypatch, climatempo, client)
    result = await climatempo.fetch_forecast(-22, -41, "Macae", "RJ", days=15)
    assert result[0] == {
        "date": "2026-08-07",
        "weather": "Sol",
        "icon": "1",
        "tmax": 30,
        "tmin": 20,
        "precip_mm": 1.5,
        "precip_prob": 40,
        "wind_kmh": 12,
        "pressure_hpa": None,
        "source": "ClimaTempo",
    }
    assert await climatempo.fetch_forecast(-22, -41, "Macae", "RJ") == result
    assert len(client.calls) == 1

    monkeypatch.setattr(climatempo, "search_city", AsyncMock(return_value=None))
    assert await climatempo.fetch_forecast(-22, -41, "Other", "RJ") is None

    monkeypatch.setattr(climatempo, "search_city", AsyncMock(return_value={"id": 99}))
    install_pool(monkeypatch, climatempo, FakeClient([FakeResponse({}, status_code=503)]))
    assert await climatempo.fetch_forecast(-22, -41, "Fail", "RJ") is None
