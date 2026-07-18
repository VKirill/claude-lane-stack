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
