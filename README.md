![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-11b33d) ![Stars](https://img.shields.io/github/stars/chamseddinehiddoud/ventura-pro-agro) ![Forks](https://img.shields.io/github/forks/chamseddinehiddoud/ventura-pro-agro)

# Ventura Pro Agro

Planejamento da melhor época de plantio e colheita por município no Brasil, combinando **clima**, **fase da lua**, **maré**, **barômetro**, **ZARC** (Zoneamento Agrícola de Risco Climático) e **custos de produção**.

## Funcionalidades

- **Municípios**: cobertura completa do Brasil (27 UFs, 5.570 municípios) com dados do IBGE.
- **Culturas**: 22 culturas (soja, milho, feijão, café, cana, arroz, algodão, etc.) com janelas de plantio regionais, referências ZARC/MAPA e calendários Embrapa/Conab.
- **Clima**: normais mensais de chuva e temperatura a partir do Open-Meteo (sem chave) ou ClimaTempo (opcional, com token).
- **Astronomia**: fase da lua, iluminação e influência tradicional por cultura.
- **Maré e barômetro**: condições complementares para decisão de plantio.
- **Custos**: valores de referência de mercado (R$/ha) com conversão de unidades (hectare, alqueire paulista, mineiro e baiano).

## Stack

- Python ≥ 3.12
- FastAPI + Uvicorn (ASGI)
- Pydantic v2 + Pydantic Settings
- httpx (cliente assíncrono), aiosqlite (cache), tzdata
- pywebview (shell desktop, Windows)

## Estrutura

```
ventura-pro-agro/
├── backend/
│   ├── app/
│   │   ├── api/          # Rotas FastAPI (prefixo /api/v1)
│   │   ├── domain/       # Lógica de negócio: clima, astronomia, ZARC, custos...
│   │   ├── data/         # Dados embarcados: UFs, municípios, culturas
│   │   ├── config.py     # Configuração via pydantic-settings
│   │   └── main.py       # Bootstrap do app
│   ├── scripts/          # Gerador de datasets (IBGE + Municipios-Brasileiros)
│   └── tests/            # Testes de domínio (pytest + pytest-asyncio)
├── LICENSE
└── README.md
```

## Como executar

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8750
```

Documentação interativa em `http://127.0.0.1:8750/docs`.

## Endpoints principais

| Método | Rota | Descrição |
| ------ | ---- | --------- |
| GET | `/api/v1/health` | Health check do serviço |
| GET | `/api/v1/ufs` | Lista de UFs |
| GET | `/api/v1/municipios?uf=` | Municípios por UF |
| GET | `/api/v1/municipios/{ibge}` | Município por código IBGE |
| GET | `/api/v1/crops` | Culturas da base de conhecimento |
| GET | `/api/v1/crops/{slug}` | Detalhe de uma cultura |

## Testes

```bash
cd backend
pytest
```

## Fontes de dados

- **IBGE** — municípios e UFs.
- **kelvins/Municipios-Brasileiros** — dataset de municípios.
- **Open-Meteo** — normais climáticas (padrão, sem token).
- **ClimaTempo** — alternativa com token (`CLIMATEMPO_TOKEN`).
- **ZARC/MAPA** — janelas de plantio (link para Plantio Certo/Embrapa para janela oficial municipal).

## Licença

MIT — veja o arquivo [LICENSE](LICENSE).
