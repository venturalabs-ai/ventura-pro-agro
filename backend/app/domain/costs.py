"""Custos: estimativa de gastos por unidade de área (alqueire/ha/acre/m²)."""

from __future__ import annotations

from typing import Any

from app.domain.units import AreaUnit, from_ha, to_ha

# Ordem de exibição das rubricas de custo.
COST_CATEGORIES = ("sementes", "sementes_mudas", "mudas", "manivas", "fertilizantes", "defensivos", "manejo", "total")


def cost_breakdown(
    crop: dict[str, Any],
    area: float,
    unit: AreaUnit,
) -> dict[str, Any]:
    """Custo total e por categoria para uma área, convertidos para a unidade escolhida.

    Retorna também produtividade e receita estimadas para a mesma área.
    """
    ref = crop.get("custos_ref_ha", {})
    if not ref:
        return {"disponivel": False, "note": "Sem tabela de custos de referência para esta cultura."}

    ha = to_ha(area, unit)
    per_unit_area = {k: round(from_ha(v, unit), 2) for k, v in ref.items() if isinstance(v, (int, float))}

    total_ref = ref.get("total", sum(v for k, v in ref.items() if k != "total" and isinstance(v, (int, float))))
    total_for_area = total_ref * ha

    prod = crop.get("produtividade", {})
    prod_val = prod.get("valor")
    prod_unit = prod.get("unidade", "")
    if prod_val is not None and "t/" in prod_unit:
        prod_scaled = prod_val * ha
    elif prod_val is not None:
        prod_scaled = prod_val * ha
    else:
        prod_scaled = None

    preco = crop.get("preco_ref")
    receita = round(prod_scaled * preco, 2) if prod_scaled is not None and preco else None

    margem = None
    margem_pct = None
    if receita is not None and total_for_area:
        margem = round(receita - total_for_area, 2)
        margem_pct = round((margem / total_for_area) * 100.0, 1)

    return {
        "disponivel": True,
        "area": area,
        "unit": unit,
        "unit_label": _unit_label(unit),
        "ha_equivalent": round(ha, 4),
        "per_unit": per_unit_area,
        "total": round(total_for_area, 2),
        "produtividade_estimada": round(prod_scaled, 2) if prod_scaled is not None else None,
        "produtividade_unidade": prod_unit,
        "preco_ref": preco,
        "receita_estimada": receita,
        "margem_estimada": margem,
        "margem_pct": margem_pct,
        "note": "Valores de referência aproximados do mercado brasileiro (2025/26). Ajuste com sua planilha real.",
    }


def _unit_label(unit: str) -> str:
    from app.domain.units import LABELS

    return LABELS.get(unit, unit)
