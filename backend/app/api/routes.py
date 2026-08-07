"""Rotas da API v1 do Ventura Pro Agro."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.domain import crops as crops_domain
from app.domain import locations
from app.domain import units as units_domain
from app.domain.climatempo import available as climatempo_available
from app.infrastructure import db
from app.services import analysis as analysis_service

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "app": "Ventura Pro Agro",
        "culturas": len(crops_domain.get_crops()),
        "municipios": len(locations._municipios()),
        "climatempo": climatempo_available(),
    }


@router.get("/ufs")
async def ufs() -> list[dict[str, Any]]:
    return locations.get_ufs()


@router.get("/municipios")
async def municipios(
    uf: str = Query(..., min_length=2, max_length=2, description="Sigla da UF (ex.: SP)"),
    q: str = Query("", description="Trecho do nome do município"),
    limit: int = Query(15, ge=1, le=100),
) -> list[dict[str, Any]]:
    return locations.search_municipios(uf, q, limit=limit)


@router.get("/municipios/{ibge}")
async def municipio(ibge: str) -> dict[str, Any]:
    muni = locations.get_municipio(ibge)
    if muni is None:
        raise HTTPException(status_code=404, detail="Município não encontrado.")
    return muni


@router.get("/crops")
async def crops() -> list[dict[str, Any]]:
    return crops_domain.get_crops()


@router.get("/crops/{slug}")
async def crop(slug: str) -> dict[str, Any]:
    c = crops_domain.get_crop(slug)
    if c is None:
        raise HTTPException(status_code=404, detail="Cultura não encontrada.")
    return c


@router.get("/units")
async def units() -> dict[str, Any]:
    return {"units": units_domain.available_units()}


@router.get("/analysis")
async def analysis(
    ibge: str = Query(..., description="Código IBGE do município (7 dígitos)"),
    crop: str | None = Query(None, description="Slug da cultura (opcional)"),
    area: float | None = Query(None, gt=0, description="Área a orçar"),
    unit: str | None = Query(None, description="Unidade de área (ha, alq_paulista, ...)"),
) -> dict[str, Any]:
    if unit is not None and unit not in units_domain.SQ_METERS:
        raise HTTPException(status_code=422, detail=f"Unidade inválida: {unit}")
    try:
        return await analysis_service.full_analysis(ibge, crop, area, unit)  # type: ignore[arg-type]
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/config")
async def get_config() -> dict[str, Any]:
    return {
        "app_name": "Ventura Pro Agro",
        "versao": "0.1.0",
        "climatempo_token": bool(db.get_setting("climatempo_token", "") or _env_climatempo()),
        "fonte_previsao": "ClimaTempo" if _env_climatempo() else "Open-Meteo (sem chave)",
        "history_years": 10,
    }


@router.put("/config")
async def put_config(payload: dict[str, Any]) -> dict[str, Any]:
    key = payload.get("key")
    value = payload.get("value")
    if not key:
        raise HTTPException(status_code=422, detail="Campo 'key' obrigatório.")
    await db.aset_setting(key, value)
    return {"ok": True, "key": key}


@router.get("/history")
async def history(limit: int = Query(10, ge=1, le=50)) -> list[dict[str, Any]]:
    return await db.recent_searches(limit)


def _env_climatempo() -> bool:
    from app.config import settings

    return bool(settings.climatempo_token)
