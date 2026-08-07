"""Localidades: UFs (IBGE) e municípios com coordenadas, busca e geocodificação."""

from __future__ import annotations

import json
import re
from typing import Any

from app.config import settings

_REGION_BY_UF = {
    "AC": "N", "AM": "N", "AP": "N", "PA": "N", "RO": "N", "RR": "N", "TO": "N",
    "AL": "NE", "BA": "NE", "CE": "NE", "MA": "NE", "PB": "NE", "PE": "NE",
    "PI": "NE", "RN": "NE", "SE": "NE",
    "DF": "CO", "GO": "CO", "MT": "CO", "MS": "CO",
    "ES": "SE", "MG": "SE", "RJ": "SE", "SP": "SE",
    "PR": "S", "RS": "S", "SC": "S",
}


def _load_json(name: str) -> list[dict[str, Any]]:
    path = settings.data_dir / name
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def get_ufs() -> list[dict[str, str]]:
    """Lista de UFs (sigla, nome, região)."""
    ufs = _load_json("ufs.json")
    if ufs:
        return ufs
    # Fallback estático mínimo caso o dataset não tenha sido gerado.
    fallback = [
        ("AC", "Acre", "N"), ("AL", "Alagoas", "NE"), ("AP", "Amapá", "N"),
        ("AM", "Amazonas", "N"), ("BA", "Bahia", "NE"), ("CE", "Ceará", "NE"),
        ("DF", "Distrito Federal", "CO"), ("ES", "Espírito Santo", "SE"),
        ("GO", "Goiás", "CO"), ("MA", "Maranhão", "NE"), ("MT", "Mato Grosso", "CO"),
        ("MS", "Mato Grosso do Sul", "CO"), ("MG", "Minas Gerais", "SE"),
        ("PA", "Pará", "N"), ("PB", "Paraíba", "NE"), ("PR", "Paraná", "S"),
        ("PE", "Pernambuco", "NE"), ("PI", "Piauí", "NE"), ("RJ", "Rio de Janeiro", "SE"),
        ("RN", "Rio Grande do Norte", "NE"), ("RS", "Rio Grande do Sul", "S"),
        ("RO", "Rondônia", "N"), ("RR", "Roraima", "N"), ("SC", "Santa Catarina", "S"),
        ("SP", "São Paulo", "SE"), ("SE", "Sergipe", "NE"), ("TO", "Tocantins", "N"),
    ]
    return [{"uf": u, "nome": n, "regiao": r, "regiao_nome": _region_name(r)} for u, n, r in fallback]


def _region_name(sigla: str) -> str:
    return {
        "N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul",
    }.get(sigla, "")


def _municipios() -> list[dict[str, Any]]:
    return _load_json("municipios.json")


def search_municipios(uf: str, query: str, limit: int = 15) -> list[dict[str, Any]]:
    """Busca municípios por UF e trecho do nome (case/acento insensíveis)."""
    uf = uf.upper()
    q = _normalize(query).lower()
    results = []
    for m in _municipios():
        if m.get("uf") != uf:
            continue
        name = m.get("nome", "")
        if q and q not in _normalize(name).lower():
            continue
        results.append(_public_municipio(m))
        if len(results) >= limit:
            break
    return results


def get_municipio(ibge: str) -> dict[str, Any] | None:
    """Retorna um município pelo código IBGE (7 dígitos)."""
    ibge = ibge.zfill(7)
    for m in _municipios():
        if str(m.get("ibge")) == ibge:
            return _public_municipio(m)
    return None


def _public_municipio(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "ibge": str(m.get("ibge")),
        "nome": m.get("nome"),
        "uf": m.get("uf"),
        "regiao": _REGION_BY_UF.get(m.get("uf"), ""),
        "regiao_nome": _region_name(_REGION_BY_UF.get(m.get("uf"), "")),
        "lat": m.get("lat"),
        "lng": m.get("lng"),
    }


def _normalize(text: str) -> str:
    """Remove acentos para busca insensível a acentuação."""
    if not text:
        return text
    return re.sub(
        r"[\u0300-\u036f]",
        "",
        text.encode("latin-1", errors="ignore").decode("latin-1"),
    )
