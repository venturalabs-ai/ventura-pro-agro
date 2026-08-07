"""ZARC: contextualização do Zoneamento Agrícola de Risco Climático.

A API municipal oficial da Embrapa exige token AgroAPI (fora do escopo local).
Aqui montamos o link para o Plantio Certo (fonte oficial municipal) e um
resumo de risco baseado no clima histórico + janela regional de referência.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.domain import crops as crops_domain


def plantio_certo_url(crop_slug: str, uf: str, city_slug: str) -> str:
    """Link direto para o Zoneamento Municipal no Plantio Certo (Embrapa)."""
    return (
        "https://plantio-certo.agr.br/"
        f"?cultura={crop_slug}&uf={uf.upper()}&municipio={city_slug}"
    )


def _rain_risk(month_normal_mm: float | None, ideal: dict[str, Any] | None) -> dict[str, Any]:
    if month_normal_mm is None or not ideal:
        return {"level": "sem dados", "note": "Normal pluviométrica não disponível."}
    low, high = ideal.get("precip_mm_min", 0), ideal.get("precip_mm_max", 999)
    if month_normal_mm < low:
        return {
            "level": "alto",
            "note": (
                f"Chuva esperada ({month_normal_mm:.0f} mm/mês) abaixo do ideal para a cultura "
                f"({low}-{high} mm). Risco de déficit hídrico."
            ),
        }
    if month_normal_mm > high:
        return {
            "level": "alto",
            "note": (
                f"Chuva esperada ({month_normal_mm:.0f} mm/mês) acima do ideal para a cultura "
                f"({low}-{high} mm). Risco de excesso/doenças."
            ),
        }
    return {
        "level": "baixo",
        "note": (
            f"Chuva esperada ({month_normal_mm:.0f} mm/mês) dentro da faixa ideal da cultura "
            f"({low}-{high} mm)."
        ),
    }


def zarc_summary(
    crop: dict[str, Any],
    region: str,
    uf: str,
    city_slug: str,
    history: dict[str, Any] | None,
    d: date | None = None,
) -> dict[str, Any]:
    """Resumo ZARC para a cultura + município: janela, risco climático e link oficial."""
    d = d or date.today()
    status = crops_domain.crop_status(crop, region, d)
    ideal = crop.get("clima_ideal")

    month_normal = None
    if history:
        month_normal = history["monthly_normals"][d.month - 1].get("rain_mm")
        if month_normal:
            month_normal = month_normal["mean"]
    rain = _rain_risk(month_normal, ideal)

    if status["status"] == "aguarde":
        risco = "moderado"
        nota = (
            f"Município fora da janela regional de referência. A próxima janela abre "
            f"em {status['proxima_janela']['month_label']}/{status['proxima_janela']['year']} "
            f"(aprox. {status['proxima_janela']['start_date']})."
        )
    else:
        risco = "baixo" if rain["level"] == "baixo" else "alto"
        nota = (
            f"{status['label']}. Condição climática mensal: risco {rain['level']} "
            f"({rain['note']})"
        )

    return {
        "fonte": "Referência regional (portarias ZARC/MAPA). Para o zoneamento municipal oficial, use o Plantio Certo.",
        "municipal_url": plantio_certo_url(crop["slug"], uf, city_slug),
        "regiao": {"sigla": region, "nome": crops_domain.REGION_NAMES.get(region, region)},
        "janela_regional": {
            "status": status["status"],
            "label": status["label"],
            "plantio_meses": status["plantio_meses"],
            "plantio_meses_label": status["plantio_meses_label"],
            "colheita_meses_label": status["colheita_meses_label"],
            "proxima_janela": status["proxima_janela"],
        },
        "risco_mensal": {"level": rain["level"], "note": rain["note"], "month_normal_mm": month_normal},
        "risco_geral": {"level": risco, "note": nota},
        "obs": crop.get("obs"),
    }
