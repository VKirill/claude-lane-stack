# ADR: Durable orchestration model (no Claude subagent per writer)

## Status
Accepted (2026-07-30)

## Context
Solo multi-task runs need writers that outlive Claude turns and a deterministic
lifecycle. Spawning one Claude babysitter per Kimi/Qwen task is expensive and
idle-prone.

## Decision
- Lifecycle: durable `run-controller` (process).
- Visibility: exactly one `run-supervisor` Claude agent per run.
- Writers: process lanes via `lane-bg` / `lane-exec` / `lane-session`.
- Partial block: one task blocked does not freeze runnable siblings; dependents
  of blocked upstream are cascaded blocked.
- Recovery: typed ladder only (retry → Codex fallback → lane-supervisor →
  emergency-writer). No PM nohup/async ad-hoc monitors.
- Silence: receipts (`controller.json`, `events.jsonl`) over chat idle.

## Consequences
PM and skills must not invent "subagent per task" as the default lifecycle.
Install mirrors must stay in sync with this repo's agents/skills/docs.
