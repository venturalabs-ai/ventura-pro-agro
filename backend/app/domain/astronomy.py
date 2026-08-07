"""Astronomia: fase da lua (algoritmo de Meeus) e modelo simplificado de maré.

A fase lunar é calculada com o algoritmo clássico de Jean Meeus
("Astronomical Algorithms", cap. 47), com precisão de ~0,3°.

A maré é uma *estimativa simplificada* de equilíbrio semi-diurno (componentes
lunar e solar), ancorada no trânsito lunar local e na amplitude de referência
da cidade. NÃO substitui a tábua oficial de marés (Marinha do Brasil).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Mecânica celeste (Meeus)
# ---------------------------------------------------------------------------


def _julian_day(dt: datetime) -> float:
    """Julian Day (UTC)."""
    dt = dt.astimezone(UTC)
    y, m = dt.year, dt.month
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    day = dt.day + (dt.hour + (dt.minute + dt.second / 60.0) / 60.0) / 24.0
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + day + b - 1524.5


def _moon_ecliptic(jd: float) -> tuple[float, float]:
    """Longitude e latitude eclíptica geocêntricas da Lua (graus)."""
    T = (jd - 2451545.0) / 36525.0
    T2, T3, T4 = T * T, T * T * T, T * T * T * T

    lp = 218.3164477 + 481267.88123421 * T - 0.0015786 * T2 + T3 / 538841.0 - T4 / 65194000.0
    D = 297.8501921 + 445267.1114034 * T - 0.0018819 * T2 + T3 / 545868.0 - T4 / 113065000.0
    M = 357.5291092 + 35999.0502909 * T - 0.0001536 * T2 + T3 / 24490000.0
    Mp = 134.9633964 + 477198.8675055 * T + 0.0087414 * T2 + T3 / 69699.0 - T4 / 14712000.0
    F = 93.2720950 + 483202.0175233 * T - 0.0036539 * T2 - T3 / 3526000.0 + T4 / 863310000.0
    E = 1.0 - 0.002516 * T - 0.0000074 * T2

    def s(a: float) -> float:
        return math.sin(math.radians(a))

    # Série principal da longitude (Meeus, tab. 47.A) — ~0,3° de precisão.
    l1 = (
        6288774 * s(Mp)
        + 1274027 * s(2 * D - Mp)
        + 658314 * s(2 * D)
        + 213618 * s(2 * Mp)
        - 185116 * E * s(M)
        - 114332 * s(2 * F)
        + 58793 * s(2 * D - 2 * Mp)
        + 57066 * E * s(2 * D - M - Mp)
        + 53322 * s(2 * D + Mp)
        + 45758 * E * s(2 * D - M)
        - 40923 * s(M - Mp - 2 * F)
        - 34720 * s(D)
        - 30383 * E * s(M + Mp)
        + 15327 * s(2 * D - 2 * F)
        - 12528 * s(Mp + 2 * F)
        + 10980 * s(Mp - 2 * F)
        + 10675 * s(4 * D - Mp)
        + 10034 * s(3 * Mp)
        + 8548 * s(4 * D - 2 * Mp)
        - 7888 * s(2 * D + M - Mp)
        - 6766 * s(2 * D + M)
        - 5163 * s(D - 2 * Mp)
        + 4987 * s(D + M)
        + 4036 * s(2 * D - 2 * Mp + 2 * F)
        + 3994 * s(2 * D + 2 * Mp)
        + 3861 * s(4 * D)
        + 3665 * s(2 * D - 3 * Mp)
        - 2689 * E * s(M - 2 * Mp)
        - 2602 * s(2 * D - Mp + 2 * F)
        + 2390 * E * s(2 * D - M - 2 * Mp)
        - 2348 * s(D + 2 * Mp)
        + 2236 * E * s(2 * D - 2 * M)
        - 2120 * E * s(M + 2 * Mp)
        - 2069 * E * s(2 * M - Mp)
        + 2048 * E * E * s(2 * D - 2 * M - Mp)
        - 1773 * s(2 * D + M - 2 * Mp)
        - 1595 * s(2 * D + 2 * F)
    )
    lon = lp + l1 / 1_000_000.0

    # Latitude (termos principais da tab. 47.B).
    b1 = -52689 * s(F) - 4241 * s(Mp - 2 * F) + 2545 * s(Mp - 2 * D + 2 * F)
    lat = b1 / 1_000_000.0

    return lon % 360.0, lat


def moon_phase_angle(jd: float) -> float:
    """Alongamento geocêntrico Sol–Lua em graus [0, 360)."""
    lam_moon, _ = _moon_ecliptic(jd)
    T = (jd - 2451545.0) / 36525.0
    lam_sun = (280.46061837 + 36000.770053608 * T) % 360.0
    return (lam_moon - lam_sun) % 360.0


def _moon_ra_dec(jd: float) -> tuple[float, float]:
    """Ascensão reta e declinação da Lua (graus)."""
    lam, bet = _moon_ecliptic(jd)
    T = (jd - 2451545.0) / 36525.0
    eps = 23.43929111 - 0.013004167 * T
    lr, br, er = map(math.radians, (lam, bet, eps))
    ra = math.atan2(math.sin(lr) * math.cos(er) - math.tan(br) * math.sin(er), math.cos(lr))
    dec = math.asin(math.sin(br) * math.cos(er) + math.cos(br) * math.sin(er) * math.sin(lr))
    return math.degrees(ra) % 360.0, math.degrees(dec)


def _gmst(jd0: float) -> float:
    """Tempo sideral médio de Greenwich (graus) para 0h UT do dia jd0."""
    T = (jd0 - 2451545.0) / 36525.0
    return (
        280.46061837
        + 360.98564736629 * (jd0 - 2451545.0)
        + 0.000387933 * T * T
        - T * T * T / 38710000.0
    ) % 360.0


PHASE_NAMES_8 = [
    (337.5, "Lua Nova"),
    (22.5, "Lua Crescente"),
    (67.5, "Quarto Crescente"),
    (112.5, "Lua Crescente Gibosa"),
    (157.5, "Lua Cheia"),
    (202.5, "Lua Minguante Gibosa"),
    (247.5, "Quarto Minguante"),
    (292.5, "Lua Minguante"),
]


def phase_name(elong: float) -> str:
    """Nome das 8 fases a partir do alongamento (graus).

    As faixas têm largura de 45°; a Lua Nova ocupa as faixas [337,5°, 360°)
    e [0°, 22,5°) (entrada de "quebra" da lista).
    """
    e = elong % 360.0
    if e < 22.5 or e >= 337.5:
        return "Lua Nova"
    for i in range(1, len(PHASE_NAMES_8)):
        start = PHASE_NAMES_8[i][0]
        end = PHASE_NAMES_8[i + 1][0] if i + 1 < len(PHASE_NAMES_8) else 337.5
        if start <= e < end:
            return PHASE_NAMES_8[i][1]
    return "Lua Nova"


# ---------------------------------------------------------------------------
# Fases lunares
# ---------------------------------------------------------------------------


class MoonInfo(TypedDict):
    date: str
    phase_deg: float
    phase_name: str
    illumination: float
    age_days: float


def moon_info(dt: datetime) -> MoonInfo:
    jd = _julian_day(dt)
    elong = moon_phase_angle(jd)
    illum = (1.0 + math.cos(math.radians(elong))) / 2.0
    synodic = 29.530588853
    age = (elong / 360.0) * synodic
    return {
        "date": dt.date().isoformat(),
        "phase_deg": round(elong, 1),
        "phase_name": phase_name(elong),
        "illumination": round(illum * 100.0, 1),
        "age_days": round(age, 1),
    }


def _crossed(a: float, b: float, target: float) -> bool:
    """True se o alongamento (crescente) atinge `target` ao ir de a para b."""
    return ((target - a) % 360.0) < ((b - a) % 360.0)


def next_phase_after(dt: datetime, target_angle: float) -> datetime:
    """Instante (UTC) da próxima ocorrência de alongamento == target_angle."""
    target = target_angle % 360.0
    step = timedelta(hours=1)
    lo = dt.replace(minute=0, second=0, microsecond=0)
    prev = moon_phase_angle(_julian_day(lo))
    # Varredura horária até 45 dias.
    for _ in range(45 * 24):
        hi = lo + step
        cur = moon_phase_angle(_julian_day(hi))
        if _crossed(prev, cur, target):
            # Bissecção até ~15 s.
            for _ in range(16):
                mid = lo + (hi - lo) / 2
                mid_v = moon_phase_angle(_julian_day(mid))
                if _crossed(prev, mid_v, target):
                    hi = mid
                else:
                    lo, prev = mid, mid_v
            return lo
        prev = cur
        lo = hi
    raise ValueError("fase lunar não encontrada no horizonte de 45 dias")


def primary_phases_in_range(start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Fases principais (Nova, Quarto Crescente, Cheia, Quarto Minguante) em [start, end]."""
    out: list[dict[str, Any]] = []
    targets = (
        (0.0, "Lua Nova"),
        (90.0, "Quarto Crescente"),
        (180.0, "Lua Cheia"),
        (270.0, "Quarto Minguante"),
    )
    cur = start
    while cur < end:
        nxt_new = next_phase_after(cur, 0.0)
        if nxt_new > end:
            break
        for target, label in targets:
            ph = next_phase_after(nxt_new - timedelta(days=7), target)
            if start <= ph <= end:
                out.append({"datetime_utc": ph.isoformat(), "phase": label, "angle": target})
        cur = nxt_new + timedelta(days=1)
    out.sort(key=lambda x: x["datetime_utc"])
    dedup: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in out:
        key = (item["datetime_utc"][:10], item["phase"])
        if key not in seen:
            seen.add(key)
            dedup.append(item)
    return dedup


# ---------------------------------------------------------------------------
# Maré (estimativa simplificada de equilíbrio)
# ---------------------------------------------------------------------------


class TideEvent(TypedDict):
    time: str
    kind: str  # "high" | "low"
    height_m: float


def _moon_transit_utc(dt: datetime, longitude_east_deg: float) -> float:
    """Hora UTC (float 0-24) do trânsito superior da Lua no meridiano local."""
    jd0 = _julian_day(dt.replace(hour=0, minute=0, second=0, microsecond=0))
    ra, _ = _moon_ra_dec(jd0 + 0.5)
    g = _gmst(jd0)
    return (((ra - g - longitude_east_deg) % 360.0) / 360.98564736629) % 24.0


def tide_day_estimate(
    dt: datetime,
    longitude_east_deg: float,
    spring_range_m: float,
    tz: ZoneInfo | None = None,
) -> dict[str, Any]:
    """Estimativa da maré para um dia (nível médio do mar = 0).

    Modelo: componente semi-diurna lunar (período 12,4206 h) + pequena
    componente solar (12,0 h), amplitude modulada por sizígia/quadratura
    conforme a fase da lua.
    """
    dt_utc = dt.astimezone(UTC)
    elong = moon_phase_angle(_julian_day(dt_utc))
    tidal_factor = 0.5 + 0.5 * math.cos(math.radians(2 * elong))
    amplitude = (spring_range_m / 2.0) * tidal_factor

    transit = _moon_transit_utc(dt_utc, longitude_east_deg)

    def height_at_utc(ut: float) -> float:
        m2 = math.cos(2 * math.pi * (ut - transit) / 12.4206)
        s2 = 0.25 * math.cos(2 * math.pi * (ut - (transit + 6.0)) / 12.0)
        return amplitude * (m2 + s2)

    day_start = dt_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    events: list[TideEvent] = []
    for i in range(-3, 4):  # cobre o dia com folga
        ev_utc = day_start + timedelta(hours=transit + 6.2103 * i)
        if day_start <= ev_utc < day_start + timedelta(days=1):
            h = height_at_utc(ev_utc.hour + ev_utc.minute / 60.0 + ev_utc.second / 3600.0)
            ev_local = ev_utc.astimezone(tz) if tz else ev_utc
            events.append(
                {
                    "time": ev_local.strftime("%H:%M"),
                    "kind": "high" if i % 2 == 0 else "low",
                    "height_m": round(h, 2),
                }
            )
    events.sort(key=lambda e: e["time"])
    heights = [e["height_m"] for e in events]
    return {
        "date": dt.date().isoformat(),
        "spring_range_m": round(spring_range_m, 2),
        "tidal_factor": round(tidal_factor, 2),
        "regime": (
            "sizígia (maré ampliada)"
            if tidal_factor > 0.8
            else "quadratura (maré reduzida)"
            if tidal_factor < 0.4
            else "intermediário"
        ),
        "min_m": round(min(heights), 2) if heights else None,
        "max_m": round(max(heights), 2) if heights else None,
        "events": events,
        "source": "estimativa simplificada — consulte a tábua oficial da Marinha",
    }
