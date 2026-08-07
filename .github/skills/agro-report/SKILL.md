---
name: agro-report
description: Produce a producer-facing planning report from Ventura Pro Agro outputs with sources assumptions and uncertainty visible. Use when assembling municipality crop climate ZARC and cost results into one report. Do not use when changing the underlying calculations or source adapters.
---

# Agro report

- Gather only outputs produced by existing domain and API contracts.
- Lead with municipality crop reference period and decision context.
- Separate official ZARC constraints from climate observations and heuristic signals.
- Show cost assumptions units and reference values clearly.
- Include source names timestamps or provenance fields already available.
- Mark missing stale or unavailable data instead of filling gaps.
- Keep recommendations framed as decision support rather than guaranteed agronomic outcomes.
- Add a fixture-based report test for required sections and missing-data handling.
