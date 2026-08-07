---
name: clima-lua-mare
description: Combine repository-supported climate lunar and tidal signals while keeping each source and confidence separate. Use when building a composite planning view from these signals. Do not use when replacing official ZARC constraints or inventing missing environmental data.
---

# Clima lua mare

- Inspect the existing climate astronomy and tide data adapters before editing.
- Keep each signal labeled with its source timestamp and geographic scope.
- Normalize units only through existing domain helpers or explicit conversions.
- Never let lunar or tidal signals override official ZARC rules.
- Mark unavailable or stale data instead of fabricating a value.
- Keep heuristic interpretation visibly separate from sourced measurements.
- Add tests for complete partial stale and unavailable data combinations.
- Run Ruff and pytest from `backend/`.
