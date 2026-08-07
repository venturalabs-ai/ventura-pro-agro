"""Conversões de área e custo entre alqueires (variações), hectare, acre e m²."""

from __future__ import annotations

from typing import Literal

AreaUnit = Literal[
    "ha", "m2", "acre", "alq_paulista", "alq_mineiro", "alq_norte", "alq_baiano"
]

# Metros quadrados por unidade de área (valores legais/usuais brasileiros).
SQ_METERS: dict[AreaUnit, float] = {
    "m2": 1.0,
    "ha": 10_000.0,
    "acre": 4_046.8564224,
    "alq_paulista": 24_200.0,   # 2,42 ha
    "alq_mineiro": 48_400.0,    # 4,84 ha (também usado em Goiás)
    "alq_norte": 27_225.0,      # 2,7225 ha (norte/nordeste)
    "alq_baiano": 96_800.0,     # 9,68 ha
}

LABELS: dict[AreaUnit, str] = {
    "m2": "m²",
    "ha": "hectare (ha)",
    "acre": "acre",
    "alq_paulista": "alqueire paulista (2,42 ha)",
    "alq_mineiro": "alqueire mineiro (4,84 ha)",
    "alq_norte": "alqueire do norte (2,7225 ha)",
    "alq_baiano": "alqueire baiano (9,68 ha)",
}


def to_m2(area: float, unit: AreaUnit) -> float:
    """Converte uma área para metros quadrados."""
    return area * SQ_METERS[unit]


def from_m2(m2: float, unit: AreaUnit) -> float:
    """Converte metros quadrados para a unidade informada."""
    return m2 / SQ_METERS[unit]


def to_ha(area: float, unit: AreaUnit) -> float:
    """Converte uma área para hectares."""
    return to_m2(area, unit) / SQ_METERS["ha"]


def from_ha(ha: float, unit: AreaUnit) -> float:
    """Converte hectares para a unidade informada."""
    return ha * SQ_METERS["ha"] / SQ_METERS[unit]


def convert(area: float, from_unit: AreaUnit, to_unit: AreaUnit) -> float:
    """Converte área entre unidades."""
    return from_m2(to_m2(area, from_unit), to_unit)


def cost_per(area: float, unit: AreaUnit, total_cost_brl: float) -> float:
    """Custo total por unidade de área (R$/unidade)."""
    return total_cost_brl / area


def cost_for_area(per_unit_cost: float, per_unit: AreaUnit, target_unit: AreaUnit) -> float:
    """Converte um custo por unidade de área para outra unidade."""
    return per_unit_cost * convert(1.0, per_unit, target_unit)


def available_units() -> list[dict[str, str]]:
    """Lista de unidades disponíveis para a interface."""
    return [{"value": u, "label": LABELS[u]} for u in SQ_METERS]
