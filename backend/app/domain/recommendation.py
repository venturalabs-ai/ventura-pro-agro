"""Recomendação: pontuação diária para plantio/colheita combinando lua, clima, ZARC e barômetro."""

from __future__ import annotations

from datetime import date
from typing import Any

_MOON_CATEGORY = {
    "Lua Nova": "nova",
    "Lua Crescente": "crescente",
    "Quarto Crescente": "crescente",
    "Lua Crescente Gibosa": "crescente",
    "Lua Cheia": "cheia",
    "Lua Minguante Gibosa": "minguante",
    "Quarto Minguante": "minguante",
    "Lua Minguante": "minguante",
}


def _moon_category(phase_name: str) -> str:
    return _MOON_CATEGORY.get(phase_name, "qualquer")


def _moon_score(phase_name: str, preference: str, transplante: bool = False) -> tuple[int, str]:
    cat = _moon_category(phase_name)
    if preference == "crescente":
        if cat == "crescente":
            return 3, "Lua crescente — favorece o desenvolvimento da parte aérea (tradição popular)"
        if cat in ("nova", "cheia"):
            return 1, "Fase de transição — aceitável para plantio"
        return 0, "Lua minguante — preferida apenas para raízes/tubérculos"
    if preference == "minguante":
        if cat == "minguante":
            return 3, "Lua minguante — favorece raízes e tubérculos (tradição popular)"
        return 0, "Fase não preferida para esta cultura"
    if preference == "cheia":
        if cat == "cheia" and transplante:
            return -2, "Evitar transplantes na lua cheia (tradição popular)"
        return 1, "Sem restrição lunar relevante"
    # "qualquer"
    return 1, "Sem preferência lunar para esta cultura"


def _window_score(months: list[int], d: date, future_days: int = 14) -> tuple[int, str]:
    if not months:
        return 0, "Sem janela regional definida"
    if d.month in months:
        return 2, "Dentro da janela regional de plantio (ZARC de referência)"
    # próximo mês de janela
    for offset in range(1, 62):
        nxt = _add_months(d, offset)
        if nxt.month in months:
            if offset <= 30:
                return 1, f"Janela regional abre em breve ({_add_months(d, offset).strftime('%m/%Y')})"
            return -2, f"Fora da janela regional (próxima: {_add_months(d, offset).strftime('%m/%Y')})"
    return -2, "Fora da janela regional de referência"


def _add_months(d: date, months: int) -> date:
    total = d.year * 12 + (d.month - 1) + months
    year, month = divmod(total, 12)
    return date(year, month + 1, 1)


def _rain_score(precip_prob: float | None, precip_mm: float | None) -> tuple[int, str]:
    prob = precip_prob if precip_prob is not None else 0.0
    mm = precip_mm if precip_mm is not None else 0.0
    if prob >= 70 or mm >= 15:
        return -2, "Chuva provável/forte — risco de erosão e apodrecimento de sementes"
    if prob >= 50:
        return -1, "Chuva possível — verifique a umidade do solo"
    if mm >= 5:
        return 0, "Chuva leve prevista"
    if prob < 20 and mm < 2:
        return 1, "Tempo seco — bom para plantio e aplicações"
    return 0, "Condições regulares"


def _baro_score(trend_3d_hpa: float | None) -> tuple[int, str]:
    if trend_3d_hpa is None:
        return 0, ""
    if trend_3d_hpa >= 2.0:
        return 1, "Pressão em alta — tempo firme favorece o plantio"
    if trend_3d_hpa <= -2.0:
        return -1, "Pressão em queda — frente chuvosa se aproximando"
    return 0, ""


def best_days(
    forecast: list[dict[str, Any]],
    crop: dict[str, Any],
    region: str,
    barometer: dict[str, Any] | None = None,
    horizon: int = 14,
) -> dict[str, Any]:
    """Pontua os próximos `horizon` dias e devolve os melhores para plantar."""
    months = list(crop.get("janelas_plantio", {}).get(region, []))
    preference = crop.get("lua_tradicao", "qualquer")
    trend = (barometer or {}).get("trend_3d_hpa")

    scored: list[dict[str, Any]] = []
    for day in forecast[:horizon]:
        try:
            d = date.fromisoformat(day["date"])
        except (ValueError, KeyError):
            continue
        phase = day.get("moon_phase_name") or "Lua Cheia"
        m_score, m_reason = _moon_score(phase, preference)
        w_score, w_reason = _window_score(months, d)
        r_score, r_reason = _rain_score(day.get("precip_prob"), day.get("precip_mm"))
        b_score, b_reason = _baro_score(trend)

        score = m_score + w_score + r_score + b_score
        reasons = [x for x in (m_reason, w_reason, r_reason, b_reason) if x]
        scored.append(
            {
                "date": day["date"],
                "date_label": d.strftime("%d/%m/%Y"),
                "score": score,
                "moon_phase": phase,
                "illumination": day.get("illumination"),
                "precip_prob": day.get("precip_prob"),
                "precip_mm": day.get("precip_mm"),
                "reasons": reasons,
                "verdict": _verdict(score),
            }
        )

    scored.sort(key=lambda x: (-x["score"], x["date"]))
    return {
        "horizon_dias": horizon,
        "melhores": scored[:5],
        "todos": scored,
        "note": "Pontuação heurística: lua (tradição), janela ZARC regional, chuva prevista e tendência de pressão.",
    }


def _verdict(score: int) -> str:
    if score >= 4:
        return "Excelente para plantio"
    if score >= 2:
        return "Bom para plantio"
    if score >= 0:
        return "Aceitável"
    return "Evitar"


def harvest_window(forecast: list[dict[str, Any]], crop: dict[str, Any], region: str, horizon: int = 14) -> dict[str, Any]:
    """Avalia a janela de colheita nos próximos dias (chuva é o principal risco)."""
    months = list(crop.get("colheita_meses", {}).get(region, []))
    harvest: list[dict[str, Any]] = []
    for day in forecast[:horizon]:
        try:
            d = date.fromisoformat(day["date"])
        except (ValueError, KeyError):
            continue
        in_window = d.month in months
        prob = day.get("precip_prob") or 0
        mm = day.get("precip_mm") or 0
        if prob >= 60 or mm >= 10:
            rain_ok = False
            note = "Chuva prevista — risco de perda de qualidade (grãos: umidade alta)"
        else:
            rain_ok = True
            note = "Tempo seco — favorável à colheita"
        harvest.append(
            {
                "date": day["date"],
                "date_label": d.strftime("%d/%m/%Y"),
                "in_window": in_window,
                "rain_ok": rain_ok,
                "precip_prob": prob,
                "precip_mm": mm,
                "note": note,
                "good": in_window and rain_ok,
            }
        )
    good = [h for h in harvest if h["good"]]
    return {
        "horizon_dias": horizon,
        "janela_regional_aberta": bool(months and date.fromisoformat(forecast[0]["date"]).month in months),
        "dias_favoraveis": good[:5],
        "todos": harvest,
        "note": "Colheita ideal: dentro da janela regional e com chuva baixa prevista.",
    }
