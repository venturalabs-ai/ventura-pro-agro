---
name: zarc-window
description: Interpret and expose ZARC planting windows from repository-supported official references with traceable constraints. Use when changing ZARC lookup window selection or presentation. Do not use when producing unsupported agronomic recommendations beyond available source data.
---

# ZARC window

- Inspect the current ZARC data model and source adapters before editing.
- Keep municipality crop soil or cycle constraints explicit when the data provides them.
- Preserve source provenance and update date with returned or stored records when available.
- Distinguish official ZARC windows from heuristic climate suggestions.
- Return no recommendation when required dimensions are missing rather than guessing.
- Add tests for a supported case unsupported combination and missing source data.
- Run Ruff and pytest from `backend/`.
