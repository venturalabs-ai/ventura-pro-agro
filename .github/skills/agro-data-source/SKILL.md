---
name: agro-data-source
description: Add or refresh agricultural data sources with provenance freshness and failure behavior explicit. Use when integrating IBGE Open-Meteo ClimaTempo MAPA ZARC Embrapa or another approved source. Do not use when only presenting data already available through existing adapters.
---

# Agro data source

- Confirm the source is appropriate for the requested domain and geographic scope.
- Inspect existing adapters configuration and caching behavior before editing.
- Record source identity retrieval date and relevant license or usage constraints.
- Normalize source fields through existing domain models rather than leaking provider-specific shapes into API routes.
- Define timeout missing-data and provider-failure behavior.
- Keep optional provider credentials outside source control.
- Add fixture-based tests for success malformed data timeout and unavailable source.
- Run Ruff and pytest from `backend/`.
