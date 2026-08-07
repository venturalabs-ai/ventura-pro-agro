from __future__ import annotations

import json
import os
import time
from datetime import date
from pathlib import Path

from app.domain import costs, crops, locations, recommendation, units, zarc
from app.infrastructure import cache


def test_units_and_cost_breakdown():
    assert units.to_m2(1, "ha") == 10_000
    assert units.from_m2(10_000, "ha") == 1
    assert units.to_ha(2, "alq_paulista") == 4.84
    assert round(units.from_ha(1, "acre"), 3) == round(10_000 / 4_046.8564224, 3)
    assert units.convert(1, "ha", "m2") == 10_000
    assert units.cost_per(2, "ha", 1000) == 500
    assert units.cost_for_area(100, "ha", "m2") > 0
    assert any(x["value"] == "ha" for x in units.available_units())

    assert costs.cost_breakdown({}, 1, "ha")["disponivel"] is False
    crop = {
        "custos_ref_ha": {"sementes": 100, "fertilizantes": 200, "total": 300},
        "produtividade": {"valor": 2, "unidade": "t/ha"},
        "preco_ref": 500,
    }
    result = costs.cost_breakdown(crop, 2, "ha")
    assert result["disponivel"] is True
    assert result["total"] == 600
    assert result["receita_estimada"] == 2000
    assert result["margem_estimada"] == 1400
    assert result["unit_label"] == "hectare (ha)"


def test_crops_helpers_and_status(tmp_path: Path, monkeypatch):
    data = {
        "culturas": [
            {
                "slug": "cafe",
                "nome": "Café",
                "janelas_plantio": {"SE": [8, 9]},
                "colheita_meses": {"SE": [5, 6]},
                "ciclo_dias": [100, 120],
            }
        ]
    }
    (tmp_path / "crops.json").write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(crops.settings, "data_dir", tmp_path)

    all_crops = crops.get_crops()
    assert len(all_crops) == 1
    assert all_crops[0]["janelas_por_regiao"]["SE"]["months_label"] == "ago, set"
    assert crops.get_crop("cafe")["nome"] == "Café"
    assert crops.get_crop("missing") is None
    assert crops._months_label([]) == "não indicado"
    assert crops._months_range(11, 2) == [11, 12, 1, 2]
    assert crops._months_range(4, 4) == [4]
    assert crops.region_for_uf("rj") == "SE"
    assert crops.region_for_uf("xx") == "SE"

    crop = data["culturas"][0]
    planting = crops.crop_status(crop, "SE", date(2026, 8, 10))
    assert planting["status"] == "plantio"
    harvesting = crops.crop_status(crop, "SE", date(2026, 5, 10))
    assert harvesting["status"] == "colheita"
    waiting = crops.crop_status(crop, "SE", date(2026, 1, 10))
    assert waiting["status"] == "aguarde"
    assert waiting["proxima_janela"]["month"] == 8

    estimate = crops.harvest_estimate(crop, "SE", date(2026, 8, 1))
    assert estimate["ciclo_medio_dias"] == 110
    assert crops.harvest_estimate({"slug": "perene"}, "SE", date.today()) is None


def test_locations_dataset_search(tmp_path: Path, monkeypatch):
    municipios = [
        {"ibge": "3302403", "nome": "Macae", "uf": "RJ", "lat": -22.37, "lng": -41.78},
        {"ibge": "3550308", "nome": "Sao Paulo", "uf": "SP", "lat": -23.55, "lng": -46.63},
    ]
    (tmp_path / "municipios.json").write_text(json.dumps(municipios), encoding="utf-8")
    (tmp_path / "ufs.json").write_text(json.dumps([{"uf": "RJ", "nome": "Rio de Janeiro", "regiao": "SE"}]), encoding="utf-8")
    monkeypatch.setattr(locations.settings, "data_dir", tmp_path)

    assert locations.get_ufs()[0]["uf"] == "RJ"
    found = locations.search_municipios("rj", "Mac", limit=3)
    assert len(found) == 1 and found[0]["regiao"] == "SE"
    assert locations.get_municipio("3302403")["nome"] == "Macae"
    assert locations.get_municipio("1") is None
    assert locations._region_name("SE") == "Sudeste"
    assert locations._normalize("") == ""

    (tmp_path / "ufs.json").unlink()
    assert len(locations.get_ufs()) == 27


def test_recommendation_scoring_paths():
    assert recommendation._moon_score("Lua Crescente", "crescente")[0] == 3
    assert recommendation._moon_score("Lua Nova", "crescente")[0] == 1
    assert recommendation._moon_score("Lua Minguante", "minguante")[0] == 3
    assert recommendation._moon_score("Lua Cheia", "cheia", transplante=True)[0] == -2
    assert recommendation._moon_score("Desconhecida", "qualquer")[0] == 1

    assert recommendation._window_score([], date(2026, 1, 1))[0] == 0
    assert recommendation._window_score([1], date(2026, 1, 1))[0] == 2
    assert recommendation._rain_score(80, 0)[0] == -2
    assert recommendation._rain_score(55, 0)[0] == -1
    assert recommendation._rain_score(10, 0)[0] == 1
    assert recommendation._baro_score(3)[0] == 1
    assert recommendation._baro_score(-3)[0] == -1
    assert recommendation._baro_score(None)[0] == 0
    assert recommendation._verdict(5) == "Excelente para plantio"
    assert recommendation._verdict(3) == "Bom para plantio"
    assert recommendation._verdict(1) == "Aceitável"
    assert recommendation._verdict(-1) == "Evitar"

    forecast = [
        {"date": "2026-08-08", "moon_phase_name": "Lua Crescente", "precip_prob": 10, "precip_mm": 0},
        {"date": "2026-08-09", "moon_phase_name": "Lua Minguante", "precip_prob": 80, "precip_mm": 20},
        {"date": "bad-date"},
    ]
    crop = {"janelas_plantio": {"SE": [8]}, "colheita_meses": {"SE": [8]}, "lua_tradicao": "crescente"}
    best = recommendation.best_days(forecast, crop, "SE", {"trend_3d_hpa": 3})
    assert len(best["todos"]) == 2
    assert best["melhores"][0]["date"] == "2026-08-08"

    harvest = recommendation.harvest_window(forecast[:2], crop, "SE")
    assert len(harvest["todos"]) == 2
    assert harvest["todos"][0]["good"] is True
    assert harvest["todos"][1]["rain_ok"] is False


def test_zarc_risk_paths(monkeypatch):
    assert "cultura=cafe" in zarc.plantio_certo_url("cafe", "rj", "macae")
    assert zarc._rain_risk(None, {})["level"] == "sem dados"
    assert zarc._rain_risk(10, {"precip_mm_min": 50, "precip_mm_max": 100})["level"] == "alto"
    assert zarc._rain_risk(150, {"precip_mm_min": 50, "precip_mm_max": 100})["level"] == "alto"
    assert zarc._rain_risk(75, {"precip_mm_min": 50, "precip_mm_max": 100})["level"] == "baixo"

    base_status = {
        "status": "plantio",
        "label": "janela aberta",
        "plantio_meses": [8],
        "plantio_meses_label": "ago",
        "colheita_meses_label": "mai",
        "proxima_janela": {"month_label": "ago", "year": 2026, "start_date": "2026-08-01"},
    }
    monkeypatch.setattr(zarc.crops_domain, "crop_status", lambda *args: base_status)
    crop = {"slug": "cafe", "clima_ideal": {"precip_mm_min": 50, "precip_mm_max": 100}}
    history = {"monthly_normals": [{"rain_mm": {"mean": 75}} for _ in range(12)]}
    result = zarc.zarc_summary(crop, "SE", "RJ", "macae", history, date(2026, 8, 1))
    assert result["risco_geral"]["level"] == "baixo"

    waiting = dict(base_status)
    waiting["status"] = "aguarde"
    monkeypatch.setattr(zarc.crops_domain, "crop_status", lambda *args: waiting)
    result = zarc.zarc_summary(crop, "SE", "RJ", "macae", None, date(2026, 1, 1))
    assert result["risco_geral"]["level"] == "moderado"


def test_disk_cache_paths(tmp_path: Path):
    assert cache._safe("a/b:c") == "a_b_c"
    assert cache.cache_get("forecast", "missing", 10, cache_dir=tmp_path) is None

    path = cache.cache_set("forecast", "rio", {"ok": True}, cache_dir=tmp_path)
    assert path.exists()
    assert cache.cache_get("forecast", "rio", 60, cache_dir=tmp_path) == {"ok": True}

    old = time.time() - 120
    os.utime(path, (old, old))
    assert cache.cache_get("forecast", "rio", 10, cache_dir=tmp_path) is None

    path.write_text("not-json", encoding="utf-8")
    assert cache.cache_get("forecast", "rio", 60, cache_dir=tmp_path) is None

    calls = []
    result = cache.cache_or_fetch("x", "one", lambda: calls.append(1) or {"v": 1}, cache_dir=tmp_path)
    assert result == {"v": 1} and calls == [1]
    result = cache.cache_or_fetch("x", "one", lambda: calls.append(2) or {"v": 2}, cache_dir=tmp_path)
    assert result == {"v": 1} and calls == [1]
