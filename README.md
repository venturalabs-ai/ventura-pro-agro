# Ventura Pro Agro

[![CI](https://github.com/venturalabs-ai/ventura-pro-agro/actions/workflows/ci.yml/badge.svg)](https://github.com/venturalabs-ai/ventura-pro-agro/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/venturalabs-ai/ventura-pro-agro)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-ASGI-009688)](https://fastapi.tiangolo.com/)

Aplicação para apoiar o **planejamento de plantio e colheita por município no Brasil**, combinando dados climáticos, referências ZARC, astronomia e estimativas de custo.

> O sistema é uma ferramenta de apoio à decisão. Recomendações agronômicas oficiais e regras de seguro/crédito devem ser confirmadas nas fontes governamentais e técnicas aplicáveis.

## Funcionalidades

- municípios e UFs do Brasil;
- catálogo inicial de culturas;
- clima via Open-Meteo e integração opcional com ClimaTempo;
- fase da lua e informações astronômicas complementares;
- referências de ZARC/MAPA;
- custos de referência e conversão de unidades rurais;
- API REST documentada automaticamente pelo FastAPI.

## Stack

- Python 3.12+
- FastAPI + Uvicorn
- Pydantic v2 + Pydantic Settings
- httpx
- aiosqlite
- pytest + pytest-asyncio
- Ruff
- pywebview no shell desktop para Windows

## Estrutura

```text
ventura-pro-agro/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── domain/
│   │   ├── data/
│   │   ├── config.py
│   │   └── main.py
│   ├── scripts/
│   ├── tests/
│   └── pyproject.toml
├── .github/workflows/ci.yml
├── LICENSE
└── README.md
```

## Executar

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8750
```

Documentação interativa: `http://127.0.0.1:8750/docs`.

## Qualidade

```bash
cd backend
ruff check app tests
pytest -q
```

O CI executa lint e testes automaticamente em pushes e pull requests para `main`.

## Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/health` | health check |
| GET | `/api/v1/ufs` | lista de UFs |
| GET | `/api/v1/municipios?uf=` | municípios por UF |
| GET | `/api/v1/municipios/{ibge}` | município por código IBGE |
| GET | `/api/v1/crops` | culturas disponíveis |
| GET | `/api/v1/crops/{slug}` | detalhe de uma cultura |

## Fontes e integrações

- IBGE — municípios e UFs;
- Open-Meteo — dados climáticos;
- ClimaTempo — integração opcional;
- MAPA/ZARC e Embrapa — referências oficiais para zoneamento e calendários.

## Segurança e configuração

Segredos e tokens opcionais devem ser fornecidos por variáveis de ambiente. Não versione credenciais no repositório.

## Licença

MIT — consulte [LICENSE](LICENSE).

## Autor

Wemerson Mota de Oliveira — Ventura Labs AI

[GitHub](https://github.com/venturalabs-ai) · [LinkedIn](https://www.linkedin.com/in/wemerson-mota-de-oliveira-81aa8226/)
