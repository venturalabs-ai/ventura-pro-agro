---
name: agro-municipio-query
description: Implement or repair municipality and UF queries using the repository's IBGE-backed domain contracts. Use when changing municipality lookup filtering or identification. Do not use when calculating planting windows costs or climate signals.
---

# Agro municipality query

- Inspect `backend/app/api/` and municipality data contracts before editing.
- Use IBGE codes as stable municipality identifiers where the repository already does so.
- Preserve current UF validation and response schema.
- Handle nonexistent UF municipality and IBGE values explicitly.
- Avoid fuzzy matching unless the current API contract requires it.
- Add tests for valid lookup empty result invalid UF and unknown IBGE code.
- Run Ruff and the focused API tests then the full suite from `backend/`.
