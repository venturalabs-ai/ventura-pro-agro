from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api import routes
from app.infrastructure import db
from app.services import analysis as analysis_service


@pytest.mark.asyncio
async def test_api_routes_success_and_errors(monkeypatch):
    monkeypatch.setattr(routes.crops_domain, "get_crops", lambda: [{"slug": "cafe"}])
    monkeypatch.setattr(routes.locations, "_municipios", lambda: [{"ibge": "1"}])
    monkeypatch.setattr(routes, "climatempo_available", lambda: True)
    assert (await routes.health())["status"] == "ok"

    monkeypatch.setattr(routes.locations, "get_ufs", lambda: [{"uf": "RJ"}])
    assert await routes.ufs() == [{"uf": "RJ"}]

    monkeypatch.setattr(routes.locations, "search_municipios", lambda uf, q, limit: [{"uf": uf, "q": q, "limit": limit}])
    assert (await routes.municipios("RJ", "Macae", 5))[0]["limit"] == 5

    monkeypatch.setattr(routes.locations, "get_municipio", lambda ibge: {"ibge": ibge} if ibge == "1" else None)
    assert (await routes.municipio("1"))["ibge"] == "1"
    with pytest.raises(HTTPException) as exc:
        await routes.municipio("404")
    assert exc.value.status_code == 404

    monkeypatch.setattr(routes.crops_domain, "get_crop", lambda slug: {"slug": slug} if slug == "cafe" else None)
    assert (await routes.crop("cafe"))["slug"] == "cafe"
    with pytest.raises(HTTPException) as exc:
        await routes.crop("missing")
    assert exc.value.status_code == 404

    monkeypatch.setattr(routes.units_domain, "available_units", lambda: ["ha"])
    assert await routes.units() == {"units": ["ha"]}

    async def fake_analysis(ibge, crop, area, unit):
        return {"ibge": ibge, "crop": crop, "area": area, "unit": unit}

    monkeypatch.setattr(routes.analysis_service, "full_analysis", fake_analysis)
    result = await routes.analysis("1", "cafe", 2.0, "ha")
    assert result["crop"] == "cafe"

    with pytest.raises(HTTPException) as exc:
        await routes.analysis("1", None, None, "invalid-unit")
    assert exc.value.status_code == 422

    async def missing_analysis(*args, **kwargs):
        raise LookupError("missing")

    monkeypatch.setattr(routes.analysis_service, "full_analysis", missing_analysis)
    with pytest.raises(HTTPException) as exc:
        await routes.analysis("1", None, None, None)
    assert exc.value.status_code == 404

    monkeypatch.setattr(routes.db, "get_setting", lambda *args: "token")
    monkeypatch.setattr(routes, "_env_climatempo", lambda: False)
    config = await routes.get_config()
    assert config["climatempo_token"] is True
    assert "Open-Meteo" in config["fonte_previsao"]

    written = {}

    async def fake_set(key, value):
        written[key] = value

    monkeypatch.setattr(routes.db, "aset_setting", fake_set)
    with pytest.raises(HTTPException) as exc:
        await routes.put_config({"value": 1})
    assert exc.value.status_code == 422
    assert await routes.put_config({"key": "x", "value": 1}) == {"ok": True, "key": "x"}
    assert written == {"x": 1}

    async def fake_history(limit):
        return [{"limit": limit}]

    monkeypatch.setattr(routes.db, "recent_searches", fake_history)
    assert await routes.history(3) == [{"limit": 3}]


@pytest.mark.asyncio
async def test_db_roundtrip(tmp_path: Path, monkeypatch):
    path = tmp_path / "ventura-test.db"
    monkeypatch.setattr(db.settings, "db_path", str(path))

    assert db.get_setting("missing", "fallback") == "fallback"
    db.set_setting("theme", {"dark": True})
    assert db.get_setting("theme") == {"dark": True}

    await db.aset_setting("language", "pt-BR")
    assert db.get_setting("language") == "pt-BR"

    await db.record_search("RJ", "Macae", -22.37, -41.78, "cafe")
    await db.record_search("SP", "Campinas", -22.90, -47.06, None)
    rows = await db.recent_searches(2)
    assert len(rows) == 2
    assert rows[0]["city"] == "Campinas"
    assert rows[1]["crop_slug"] == "cafe"


@pytest.mark.asyncio
async def test_analysis_orchestration(monkeypatch):
    muni = {"ibge": "1", "uf": "RJ", "nome": "Macae", "lat": -22.37, "lng": -41.78}
    monkeypatch.setattr(analysis_service.locations, "get_municipio", lambda ibge: muni if ibge == "1" else None)
    monkeypatch.setattr(analysis_service.locations, "_normalize", lambda value: value)
    monkeypatch.setattr(analysis_service.crops_domain, "region_for_uf", lambda uf: "sudeste")
    monkeypatch.setattr(analysis_service.crops_domain, "REGION_NAMES", {"sudeste": "Sudeste"})

    climate_payload = {
        "forecast": [{"date": "2026-08-08"}],
        "barometer": {},
        "history": {},
    }

    async def fake_climate(*args):
        return climate_payload

    async def fake_astro(*args, **kwargs):
        return {"lua_hoje": {}}

    async def fake_record(*args, **kwargs):
        return None

    monkeypatch.setattr(analysis_service.climate, "climate_bundle", fake_climate)
    monkeypatch.setattr(analysis_service, "_astronomy_payload", fake_astro)
    monkeypatch.setattr(analysis_service.db, "record_search", fake_record)

    crops = [{"slug": "cafe", "nome": "Cafe", "grupo": "graos"}]
    monkeypatch.setattr(analysis_service.crops_domain, "get_crops", lambda: crops)
    monkeypatch.setattr(
        analysis_service.crops_domain,
        "crop_status",
        lambda crop, region, today: {"status": "adequado", "plantio_meses_label": "ago"},
    )
    monkeypatch.setattr(analysis_service.crops_domain, "get_crop", lambda slug: crops[0] if slug == "cafe" else None)
    monkeypatch.setattr(analysis_service, "_crop_analysis", lambda *args, **kwargs: {"selected": True})

    result = await analysis_service.full_analysis("1")
    assert result["local"]["regiao_nome"] == "Sudeste"
    assert result["cultura_detalhe"] is None
    assert result["culturas_resumo"][0]["status"] == "adequado"

    selected = await analysis_service.full_analysis("1", "cafe", 1.0, "ha")
    assert selected["cultura_detalhe"] == {"selected": True}

    with pytest.raises(LookupError):
        await analysis_service.full_analysis("404")
    with pytest.raises(LookupError):
        await analysis_service.full_analysis("1", "missing")


def test_analysis_helpers(monkeypatch):
    assert analysis_service._tide_spring_range(0.0) == 1.5
    assert analysis_service._tide_spring_range(-22.0) == 1.2

    crop = {"slug": "cafe"}
    climate_payload = {"forecast": [], "barometer": {}, "history": {}}
    monkeypatch.setattr(analysis_service.crops_domain, "crop_status", lambda *a: {"status": "ok"})
    monkeypatch.setattr(analysis_service.zarc, "zarc_summary", lambda *a: {"zarc": True})
    monkeypatch.setattr(analysis_service.recommendation, "best_days", lambda *a: {"melhores": []})
    monkeypatch.setattr(analysis_service.recommendation, "harvest_window", lambda *a: {"harvest": True})
    monkeypatch.setattr(analysis_service.costs_domain, "cost_breakdown", lambda *a: {"cost": True})
    monkeypatch.setattr(analysis_service.crops_domain, "harvest_estimate", lambda *a: {"estimate": True})
    result = analysis_service._crop_analysis(
        crop, "sudeste", "RJ", "macae", {}, climate_payload, {}, 1.0, "ha"
    )
    assert result["zarc"] == {"zarc": True}
    assert result["custos"] == {"cost": True}
