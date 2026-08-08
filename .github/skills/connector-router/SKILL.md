---
name: connector-router
description: Select the smallest trusted connector set from the repository agent manifest before a skill uses external tools. Use when a task may require APIs databases MCP servers models observability or runtime tools. Do not use when the task is fully local and needs no connector selection.
---

# Connector router

- Read `.github/agent/connectors.json` before exposing external tools to the agent.
- Identify the domain skill that owns the requested task and use its declared route.
- Activate only the connectors needed for the current step and never exceed `max_active_connectors_per_skill`.
- Start read-only and least-privilege; elevate only for the exact required action.
- Require human approval for every action category listed in `defaults.human_approval_for`.
- Prefer `official` connectors, then `native`, then `local` when capabilities overlap.
- Treat catalog membership as supported/configurable capability, not proof that credentials are installed.
- If a required high-impact connector is unavailable, fail closed instead of silently substituting an untrusted service.
- Keep connector schemas out of model context until selected to reduce token cost and tool confusion.
- Parallelize independent reads; serialize conflicting writes.
- Apply bounded timeout, retry with exponential backoff, idempotency, and circuit-breaker behavior where supported.
- After execution, verify the result independently when practical and emit redacted telemetry for latency, errors, tool calls and outcome.
- Follow the shared `venturalabs-ai/ventura.build/AGENT_RUNTIME_STANDARD.md` contract.
