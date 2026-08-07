"""Culturas: base de conhecimento (crops.json) e janelas regionais de plantio/colheita."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from app.config import settings

# Região IBGE de cada UF (usada para selecionar a janela regional ZARC de referência).
UF_REGION: dict[str, str] = {
    "AC": "N", "AM": "N", "AP": "N", "PA": "N", "RO": "N", "RR": "N", "TO": "N",
    "AL": "NE", "BA": "NE", "CE": "NE", "MA": "NE", "PB": "NE", "PE": "NE",
    "PI": "NE", "RN": "NE", "SE": "NE",
    "DF": "CO", "GO": "CO", "MT": "CO", "MS": "CO",
    "ES": "SE", "MG": "SE", "RJ": "SE", "SP": "SE",
    "PR": "S", "RS": "S", "SC": "S",
}

REGION_NAMES = {"N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul"}


def _load_crops() -> list[dict[str, Any]]:
    path = settings.data_dir / "crops.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("culturas", [])


def get_crops() -> list[dict[str, Any]]:
    """Todas as culturas com campos de exibição prontos."""
    return [_public_crop(c) for c in _load_crops()]


def get_crop(slug: str) -> dict[str, Any] | None:
    for crop in _load_crops():
        if crop["slug"] == slug:
            return _public_crop(crop)
    return None


def _public_crop(crop: dict[str, Any]) -> dict[str, Any]:
    out = dict(crop)
    # Deriva janela mensal legível para cada região.
    windows = {}
    for region, months in crop.get("janelas_plantio", {}).items():
        windows[region] = {
            "name": REGION_NAMES.get(region, region),
            "months": months,
            "months_label": _months_label(months),
        }
    out["janelas_por_regiao"] = windows
    out["region_names"] = REGION_NAMES
    return out


def _months_label(months: list[int]) -> str:
    names = [
        "jan", "fev", "mar", "abr", "mai", "jun",
        "jul", "ago", "set", "out", "nov", "dez",
    ]
    return ", ".join(names[m - 1] for m in months) if months else "não indicado"


def _months_range(a: int, b: int) -> list[int]:
    """Meses de a até b (inclusive), sem repetição (a==b -> [a])."""
    if a == b:
        return [a]
    out = []
    m = a
    while True:
        out.append(m)
        if m == b:
            break
        m = m % 12 + 1
    return out


def region_for_uf(uf: str) -> str:
    """Região IBGE de uma UF. Fallback: 'SE'."""
    return UF_REGION.get(uf.upper(), "SE")


def _in_window(months: list[int], d: date) -> bool:
    return d.month in months


def crop_status(crop: dict[str, Any], region: str, d: date) -> dict[str, Any]:
    """Status atual (plantio/colheita/aguarde) e próximas janelas para a região."""
    janelas = crop.get("janelas_plantio", {})
    colheita = crop.get("colheita_meses", {})
    months = list(janelas.get(region, []))
    harvest = list(colheita.get(region, []))
    ciclo = crop.get("ciclo_dias")

    if _in_window(months, d):
        status = "plantio"
        label = f"Janela de plantio aberta em {REGION_NAMES.get(region, region)}"
    elif _in_window(harvest, d):
        status = "colheita"
        label = f"Janela de colheita aberta em {REGION_NAMES.get(region, region)}"
    else:
        status = "aguarde"
        label = "Fora da janela regional de referência"

    next_window = _next_window(months, d)
    next_harvest = _next_window(harvest, d)

    return {
        "status": status,
        "label": label,
        "plantio_meses": months,
        "plantio_meses_label": _months_label(months),
        "colheita_meses": harvest,
        "colheita_meses_label": _months_label(harvest),
        "proxima_janela": next_window,
        "proxima_colheita": next_harvest,
        "ciclo_dias": ciclo,
        "ciclo_label": f"{ciclo[0]}-{ciclo[1]} dias" if ciclo else "Perene",
    }


def _next_window(months: list[int], d: date) -> dict[str, Any] | None:
    """Próxima abertura de janela (mês futuro mais próximo) e data típica de início."""
    if not months:
        return None
    current = d.year * 12 + (d.month - 1)
    opens = [(year, m) for year in (d.year, d.year + 1) for m in months if year * 12 + (m - 1) >= current]
    if not opens:
        return None
    year, m = min(opens, key=lambda ym: ym[0] * 12 + (ym[1] - 1))
    return {"year": year, "month": m, "month_label": _months_label([m]), "start_date": f"{year:04d}-{m:02d}-01"}


def harvest_estimate(crop: dict[str, Any], region: str, planting: date) -> dict[str, Any] | None:
    """Estima colheita a partir do plantio (média do ciclo em dias)."""
    ciclo = crop.get("ciclo_dias")
    if not ciclo:
        return None
    from datetime import timedelta

    mid = round((ciclo[0] + ciclo[1]) / 2)
    harvest_date = planting + timedelta(days=mid)
    return {
        "plantio": planting.isoformat(),
        "ciclo_medio_dias": mid,
        "colheita_estimada": harvest_date.isoformat(),
        "colheita_estimada_label": harvest_date.strftime("%d/%m/%Y"),
        "janela_regional": _in_window(crop.get("colheita_meses", {}).get(region, []), harvest_date),
    }
