---
name: custo-safra
description: Calculate and present crop cost estimates from repository-supported inputs with explicit units and assumptions. Use when changing cost composition rural-unit conversion or estimate output. Do not use when the task is climate ZARC or municipality lookup.
---

# Custo safra

- Inspect current cost models conversion helpers and supported units before editing.
- Keep quantity unit unit-price and subtotal explicit for every component.
- Preserve currency and reference-date metadata when available.
- Separate user-provided values from repository reference values.
- Reject incompatible units instead of silently converting them.
- Make assumptions visible in the API or report output.
- Add tests for totals conversions missing values and rounding boundaries.
- Run Ruff and pytest from `backend/`.
