# Threat Model — ventura-pro-agro

| Superficie | Ameaca | Mitigacao |
|------------|--------|-----------|
| API publica | abuso / scraping | rate limit futuro; auth em producao |
| Inputs municipio/cultura | injection | validacao Pydantic |
| Fontes climaticas externas | dados adulterados | timeout, schema check, nao confiar cegamente |
| Secrets de API | vazamento | so env; SECURITY.md |

Principio: recomendacoes agricolas sao apoio a decisao, nao substituem agronomo.
