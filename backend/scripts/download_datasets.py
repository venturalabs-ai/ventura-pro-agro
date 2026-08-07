"""Gera os datasets locais (ufs.json, municipios.json) a partir de fontes públicas.

Fontes:
- UFs: API IBGE (servicodados.ibge.gov.br/api/v1/localidades/estados)
- Municípios com coordenadas: kelvins/Municipios-Brasileiros (GitHub, 5.570 cidades)

Re-execute sempre que quiser atualizar:  py scripts/download_datasets.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "app" / "data"

IBGE_UFS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
KELVINS_URL = "https://raw.githubusercontent.com/kelvins/Municipios-Brasileiros/main/json/municipios.json"

REGION_BY_SIGLA = {
    "AC": "N", "AM": "N", "AP": "N", "PA": "N", "RO": "N", "RR": "N", "TO": "N",
    "AL": "NE", "BA": "NE", "CE": "NE", "MA": "NE", "PB": "NE", "PE": "NE",
    "PI": "NE", "RN": "NE", "SE": "NE",
    "DF": "CO", "GO": "CO", "MT": "CO", "MS": "CO",
    "ES": "SE", "MG": "SE", "RJ": "SE", "SP": "SE",
    "PR": "S", "RS": "S", "SC": "S",
}
REGION_NAME = {
    "N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul",
}


def download_ufs(client: httpx.Client) -> None:
    resp = client.get(IBGE_UFS_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    ufs = []
    for uf in sorted(data, key=lambda x: x["sigla"]):
        sigla = uf["sigla"]
        region = REGION_BY_SIGLA.get(sigla, "")
        ufs.append(
            {
                "uf": sigla,
                "ibge": uf.get("id"),
                "nome": uf.get("nome"),
                "regiao": region,
                "regiao_nome": REGION_NAME.get(region, ""),
            }
        )
    target = DATA_DIR / "ufs.json"
    target.write_text(json.dumps(ufs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ufs.json: {len(ufs)} UFs -> {target}")


def download_municipios(client: httpx.Client) -> None:
    resp = client.get(KELVINS_URL, timeout=60)
    resp.raise_for_status()
    raw = resp.json()
    # codigo_uf -> sigla, usando os dados de UF já baixados do IBGE.
    uf_by_code = {}
    ufs_path = DATA_DIR / "ufs.json"
    if ufs_path.exists():
        for uf in json.loads(ufs_path.read_text(encoding="utf-8")):
            uf_by_code[int(uf["ibge"])] = uf["uf"]

    municipios = []
    skipped = 0
    for m in raw:
        code_uf = m.get("codigo_uf")
        uf = uf_by_code.get(int(code_uf), "") if code_uf is not None else ""
        lat = m.get("latitude")
        lng = m.get("longitude")
        if not uf or lat is None or lng is None:
            skipped += 1
            continue
        municipios.append(
            {
                "ibge": str(m.get("codigo_ibge")).zfill(7),
                "nome": m.get("nome"),
                "uf": uf,
                "lat": float(lat),
                "lng": float(lng),
            }
        )
    municipios.sort(key=lambda x: (x["uf"], x["nome"]))
    target = DATA_DIR / "municipios.json"
    target.write_text(json.dumps(municipios, ensure_ascii=False), encoding="utf-8")
    print(f"municipios.json: {len(municipios)} municípios (ignorados sem coords: {skipped}) -> {target}")


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True) as client:
        download_ufs(client)
        download_municipios(client)
    return 0


if __name__ == "__main__":
    sys.exit(main())
