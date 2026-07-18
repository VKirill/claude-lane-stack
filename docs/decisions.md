# Architecture decisions

## ADR-001: Separate immutable run specifications from runtime receipts

- **Date:** 2026-07-18
- **Status:** accepted
- **Context:** Mutable task YAML, flat retry artifacts, and free-form reports
  allowed declared status to disagree with the real provider and verification
  lifecycle. Historical attempts could also be overwritten.
- **Decision:** New runs use schema v2. `run.yaml` and task YAML are declarative;
  task bytes become immutable at first start. Runtime state lives in
  `state.json`, attempt evidence in `attempts/NN`, completion in
  `acceptance.json`, delivery in `merge.json`, and final project-memory actions
  in `finalize.json`.
- **Consequences:** Dispatch and merge gain strict validation and complete audit
  history. Consumers must read receipts first while retaining schema-v1
  fallback for existing runs.
- **Alternatives considered:** Keep mutable YAML status; append more Markdown;
  overwrite flat artifacts on retry. Rejected because none provides a reliable
  machine gate or preserves attempt history.

## ADR-002: Durable deterministic daytime controller with one visible watcher

- **Date:** 2026-07-18
- **Status:** accepted
- **Context:** Detached provider lifetime prevented Claude cleanup from killing
  Grok, but the one-action lane supervisor returned after start. Nothing durable
  consumed provider completion and advanced ownership, verification, and
  acceptance, so the PM could look idle while finished lanes remained open.
- **Decision:** Every schema-v2 daytime run has one detached deterministic
  `run-controller` and one source-read-only `run-supervisor` for operator
  visibility. The controller owns DAG dispatch, separate provider/verification
  pools, one retry, progressive acceptance, and atomic run receipts. Daytime
  never invokes an LLM reviewer; the existing Codex review/Grok repair/re-review
  loop remains a separate night shift.
- **Consequences:** Controller progress survives Claude/subagent exit, one UI
  task stays visibly active, and exact stages/next actions are available to the
  Board. A configured daytime review gate fails closed for an operator decision.
- **Alternatives considered:** One LLM watcher per provider (too many slots and
  token overhead); detached providers with no watcher (no closed loop); parent
  polling lifecycle events (lost when the main thread idles).
