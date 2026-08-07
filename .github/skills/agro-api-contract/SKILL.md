---
name: agro-api-contract
description: Evolve Ventura Pro Agro FastAPI contracts without breaking existing routes schemas or documented behavior. Use when adding or changing API endpoints parameters or response models. Do not use when changing only internal data adapters with no API effect.
---

# Agro API contract

- Inspect current FastAPI routes Pydantic models and tests first.
- Preserve existing route paths and response fields unless the requested change requires a versioned break.
- Reuse repository validation and error patterns.
- Keep domain identifiers such as UF IBGE and crop slug explicit.
- Add contract tests for success invalid input not found and compatibility-sensitive behavior.
- Update OpenAPI-facing descriptions only when they match implemented behavior.
- Run Ruff and pytest from `backend/`.
