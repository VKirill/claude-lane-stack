# Plan: Stable Solo Factory → Multica-class Fleet

**Date:** 2026-08-04  
**Status:** draft plan (not yet executed)  
**Owner:** human operator + dev-orchestrator  
**Repo:** `claude-lane-stack` (solo trunk) → later fork `lane-fleet` / multica-core

---

## 0. North star

| Horizon | Goal | Definition of done |
|---------|------|--------------------|
| **H1 — Stable Solo** | Current system is boring-reliable for 1 human + 1 PM | 2 weeks green day-path on ≥3 live projects; night review/fix without babysitting |
| **H2 — Fleet Core** | Multi-project control plane on same contracts | One daemon + API + multi-project HANDOFF/Board; still one operator |
| **H3 — Multica-class** | Multi-operator / channels / agent registry; best-of Multica via PRs | Chat/UI are clients of control plane; receipts remain source of truth |
| **H4 — Best Multica** | Absorb external Multica (and peers) via selective PRs | Capability matrix green; solo semantics never broken |

**Non-negotiables (never drop when “going multi”):**

1. Durable `run-controller` (not subagent-per-task).
2. Immutable task contracts + `owns_paths` + verification tiers L0/L1/L2.
3. Receipts = truth (`outcome.json`, `acceptance.json`, `controller.json`, `events.jsonl`).
4. Day = fast ship (no daytime LLM review); night = typed review/fix.
5. Chat/channel never writes production code directly — only control-plane commands.
6. English in repo artifacts; RU in human chat.

**Out of scope for H1:** Telegram as primary control, multi-tenant SaaS, agent marketplace, rewriting Claude Code.

---

## 1. Current baseline (what we already have)

Treat these as **assets to keep**, not rewrite:

| Layer | Components | Role |
|-------|------------|------|
| Contracts | task YAML, `owns_paths`, verification, run schema v2 | Law of the factory |
| Day control | `run-controller`, `run-supervisor`, `lane-ctl`, `lane-bg/exec` | Durable progressive accept |
| Routing | `agents-doctor` / `adoc`, `routing.profile.yaml` | Who writes, worktree vs in_place |
| Night | `night-review`, `night-shift`, findings, checkpoint | Quality without day friction |
| Memory | HANDOFF, PROGRESS, LESSONS, session-ledger, todos | Cold start + learning |
| Surface | Lane Board, statusLine dual-mode, resume-project | Operator HUD |
| Guards | `guard_shell`, PM allowlists, verification_safety | Fail-closed |

**Known debt (from PROGRESS + recent ops):**

- `lane-bg` exit=0 can mask inner CLI failure  
- `owns_paths` mostly post-check, not hard PreToolUse / sparse-checkout  
- night-review blows up on whole-day huge diffs  
- no lane telemetry (model/duration/cost)  
- codex-implementer lessons not fully baked  
- HANDOFF/statusLine dual-mode need live soak  
- worktree `check.py` class of bugs reduced but not proven across projects  
- PROGRESS/docs lag releases (1.13.x narrative)

---

## 2. Target maturity model

### Level S0 — Fragile solo (past)

Works when operator stares at it. Chat-driven recovery. Broken verify paths.

### Level S1 — Usable solo (≈ now)

adoc + controller + night + board + handoff exist. Still intermittent false blocked / masked exits.

### Level S2 — **Stable solo (H1 exit gate)** ← must reach before multi fork

- Day: green write→verify→accept→merge on golden scenarios without manual contract surgery  
- Night: chunked review + resumable fix; morning HANDOFF truthful  
- Telemetry: enough to debug “who burned tokens / who lied about exit”  
- Operator: one command cold start (`resume-project` / HANDOFF) is enough  

### Level F1 — Fleet (H2)

Multi-project scheduler + control API + multi HANDOFF. Still one human.

### Level M1 — Multica-class (H3)

Multi-operator ACL + channels as clients + agent registry v0.

### Level M2 — Best Multica (H4)

External Multica/peer capabilities landed via PR policy; compatibility suite.

---

## 3. Phase plan

### Phase A — Day-path trust (S1 → S2 core)

**Duration estimate:** 1–2 weeks focused  
**Exit:** golden day-path suite green 5/5 consecutive runs on 3 projects

#### A1. Receipt honesty

| # | Work | Acceptance |
|---|------|------------|
| A1.1 | Fix `lane-bg` / `lane-exec` so process exit reflects inner CLI failure | Fake provider exit 1 → outcome `crashed` / non-zero; no false accept |
| A1.2 | Surface `protocol_valid` + `failure_class` consistently in HANDOFF + Board | Blocked list shows real class, not only `verification_failed` |
| A1.3 | Regression tests for masked success | Unit/integration in `tests/` |

#### A2. Contract / worktree footguns closed

| # | Work | Acceptance |
|---|------|------------|
| A2.1 | Golden matrix: in_place + worktree × product tests vs pre-authored `check.py` | `run-validate --phase pre-dispatch` fails early when script missing under `verification.cwd` (already) + PM skills always copy checks |
| A2.2 | Template/snippets: `check.py` scaffolding in `run-init` / adoc | New run never ships empty verification path |
| A2.3 | Live soak: temples-admin / yookassa / one greenfield | No `verification_script_missing` on well-formed contracts |

#### A3. owns_paths hard edge

| # | Work | Acceptance |
|---|------|------------|
| A3.1 | Design: PreToolUse deny outside owns (writer lanes) OR sparse-checkout worktrees | ADR in `docs/decisions.md` |
| A3.2 | Implement chosen approach for ≥1 provider path | Intentional write outside owns → fail closed + receipt |
| A3.3 | Parallel multi-task same worktree still OK with `--run-scope` | Existing tests green + new deny test |

#### A4. Cold start operator UX

| # | Work | Acceptance |
|---|------|------------|
| A4.1 | SessionStart inject compact HANDOFF for `dev-orchestrator` (optional flag) | Boot = Now/Blocked/Next without full BOARD dump |
| A4.2 | `/handoff` or skill always regenerates + prints compact | One action refresh |
| A4.3 | statusLine dual-mode soak: pulse in normal; lane HUD in orchestrator | Document failure modes if `agent_type` missing; SessionStart mark works |

#### A5. Docs & release hygiene

| # | Work | Acceptance |
|---|------|------------|
| A5.1 | PROGRESS/CHANGELOG/README align to shipped 1.13.x+ | No stale “Grok-only write” contradictions |
| A5.2 | Tag stable solo baseline (e.g. `v1.14.0-stable-solo`) | Install from tag works on clean host |

**Phase A exit checklist**

- [ ] A1–A4 done  
- [ ] Full unit suite green  
- [ ] 3 projects × 2 micro runs + 1 multi-task run each  
- [ ] Operator can leave machine for a day-run without chat babysitting  

---

### Phase B — Night quality + observability (finish S2)

**Duration estimate:** 1–2 weeks  
**Exit:** night-shift on largest project without manual diff surgery; cost/duration visible

| # | Work | Acceptance |
|---|------|------------|
| B1 | night-review: chunk by merged run / file budget; exclude lockfiles/binary/`.agents` noise | No 1MB Codex input blow-up on backfill-class days |
| B2 | Lane telemetry: model, duration, exit, tokens/cost if available → report + Board aggregation | Board or `artifacts/telemetry.json` per task |
| B3 | Bake codex lane lessons into `codex-implementer.md` + tests/docs | Lessons: plain `rm`, empty diff = FAIL, poll `lane-wait` until exit≠2 |
| B4 | Effort policy eval stub: log high vs xhigh outcomes when used | Table for later decision (not full eval harness yet) |
| B5 | Morning path: `resume-project` + HANDOFF + REVIEW always consistent | Scripted smoke on fixture repo |

**Phase B exit = S2 complete → allowed to start fleet fork.**

---

### Phase C — Freeze solo trunk + fork policy

**Duration:** 2–3 days  
**Exit:** clear repo boundaries

| # | Work | Acceptance |
|---|------|------------|
| C1 | Branch/tag policy: `main` = stable solo only | CONTRIBUTING / plan section |
| C2 | Create fork repo or long-lived branch `fleet/main` | No experimental fleet code on solo `main` without backport ADR |
| C3 | Compatibility contract v1: file schema versions that fleet must read | `schemas/*` version table |
| C4 | Backport rule: fleet bugfixes to contracts/controller → PR to solo | Checklist in PR template |

**Solo trunk after C:** only security/reliability patches + schema-compatible features.

---

### Phase D — Fleet Core (F1 / H2)

**Duration estimate:** 3–6 weeks  
**Product name working title:** `lane-fleet`  
**Still:** one human operator, N projects

#### D1. Control database (not only git files)

| Component | Purpose |
|-----------|---------|
| SQLite (start) or Postgres | projects, runs index, events, quotas, agent marks |
| Project registry | path, profile, night config, priority |
| Event log | append-only; Board/API subscribe |

Git remains: contracts, code, acceptance artifacts.  
DB remains: fleet scheduling truth.

#### D2. Fleet daemon

```text
lane-fleetd
  ├── discover projects (config watchlist)
  ├── schedule runs (caps: provider slots, per-project concurrent)
  ├── watch controllers (PID/liveness already exist — aggregate)
  ├── trigger night-shift-all with fairness
  └── emit events → API / Board
```

Acceptance: 5 projects registered; concurrent runs respect global slot cap; daemon restart resumes watch without double-dispatch.

#### D3. Control API

Minimal HTTP (or local unix socket first):

| Method | Path | Effect |
|--------|------|--------|
| GET | `/healthz` | liveness |
| GET | `/projects` | list + HANDOFF summary |
| GET | `/projects/{id}/handoff` | compact now/blocked/next |
| POST | `/projects/{id}/runs` | start run from approved plan ref |
| GET | `/runs/{id}` | stage, tasks, telemetry |
| POST | `/runs/{id}/actions` | retry / cancel / accept-policy (typed) |
| GET | `/events?since=` | SSE or poll |

Acceptance: Board becomes API client (or dual-read files+API); CLI `lane-fleet` wraps API.

#### D4. Multi-project HANDOFF

- Aggregate “what’s on fire” across watchlist  
- statusLine / Board overview strip uses aggregate  
- No Telegram required  

Acceptance: one screen answers “where do I intervene?” in <5s.

#### D5. Global provider pool

- Single slot allocator for kimi/codex/grok/agy across projects  
- Fairness: project priority + starvation prevention  

Acceptance: two projects cannot each spawn 10 writers and melt the host.

**Phase D exit checklist**

- [ ] Daemon + API + multi HANDOFF  
- [ ] Solo day/night semantics unchanged per project  
- [ ] Load test: 5 projects, 2 concurrent runs, night batch  
- [ ] Docs: FLEET.md + operator runbook  

---

### Phase E — Multica-class surfaces (M1 / H3)

**Duration estimate:** 4–8 weeks after D  
**Only start when D is green in production use**

#### E1. Multi-operator (minimal)

| Piece | Notes |
|-------|-------|
| Identity | local users or SSO later; start with `operators.yaml` |
| ACL | project → role: owner / operator / viewer |
| Merge rights | only owner/operator with policy; audit log |

#### E2. Channels as thin clients

Order: **Web Board actions first**, then optional TG/Slack.

Rules:

- Channel message → API action only  
- Never: bot shell with write to main  
- Alerts: blocked, night P0, controller dead  

MVP channel commands: `status`, `handoff`, `retry <run>`, `ack finding`.

#### E3. Agent registry v0

```yaml
# agents.registry.yaml
agents:
  dev-orchestrator:
    role: pm
    host: claude
  writer-kimi:
    role: writer
    provider: kimi
    max_slots: 5
  night-codex:
    role: reviewer
    provider: codex
    model: gpt-5.6-sol
    effort: xhigh
```

Hot-load skills/paths; capability advertise (read/write/review).

#### E4. Topology (still not full multi-PM chaos)

- One PM agent per project session (as today)  
- Fleet does **not** run 10 PMs editing one main  
- Cross-project deps: explicit “blocked on project X handoff” links only  

**Phase E exit:** two humans can operate two projects safely; channel can unblock without SSH.

---

### Phase F — Best Multica via external PR harvest (H4)

**Parallel track** starting mid-Phase D (research), landing after E1.

#### F1. Source map (what to mine)

| Source | Mine for | Avoid copying blindly |
|--------|----------|------------------------|
| **Multica** (upstream) | UX of multi-agent board, agent cards, session routing, channel adapters, presence | Chat-as-truth, unbounded agent fan-out, no owns_paths |
| Claude Code / Agent teams | subagent lifecycle, permissions, statusLine | Coupling factory to one host UI |
| OpenClaw / other open multi-agent | message bus, tool policy, sandbox patterns | Rewrite of controller |
| Your Board + HANDOFF | already best for factory ops | — |

Maintain living file: `docs/plans/multica-capability-matrix.md` (create in F1).

#### F2. Capability matrix (score each feature)

For every Multica (or peer) feature:

| Field | Values |
|-------|--------|
| Feature | name |
| Source | repo/PR/issue |
| Value to us | high/med/low |
| Conflicts with receipts/owns/day-night? | y/n |
| Target phase | D/E/F or reject |
| Port strategy | reimplement / adapt PR / wrap / reject |
| Effort | S/M/L |

#### F3. PR harvest process (how we “collect all PRs”)

1. **Mirror / watch** Multica upstream (and 1–2 peers) as git remotes or weekly digest.  
2. **Triage board** (todos or GitHub project):  
   - `adopt` — port into fleet  
   - `adapt` — rewrite to our control-plane API  
   - `observe` — watch  
   - `reject` — violates non-negotiables  
3. **Port unit** = one PR in *our* fleet repo with:  
   - link to upstream commit/PR  
   - compatibility note  
   - test proving receipts still authoritative  
4. **Never** merge upstream Multica wholesale into solo `main`.  
5. **Quarterly** “Best Multica” review: matrix update + drop dead adapts.

#### F4. What we expect to steal first (hypothesis — validate in F1)

Likely **adopt/adapt**:

- Agent/session cards UX  
- Multi-channel adapter interface (not TG-first product)  
- Presence / “who is working”  
- Template agent packs  
- Notification routing rules  

Likely **reject**:

- Free-form multi-agent debate loops as merge authority  
- Daytime auto-merge without verify receipts  
- Hidden shell from chat without ACL  

#### F5. “Best Multica” release definition

Tag `fleet-m2` when:

- [ ] Matrix ≥80% of high-value Multica UX features either shipped or explicitly rejected with reason  
- [ ] All shipped features speak Control API  
- [ ] Solo factory still installable and green from `claude-lane-stack` main  
- [ ] One external contributor can add a channel adapter via documented interface  

---

## 4. Architecture target (end state sketch)

```text
                    ┌─────────────────┐
   Human(s) ───────►│ Board / Channel │  (thin clients)
                    └────────┬────────┘
                             │ Control API
                    ┌────────▼────────┐
                    │   lane-fleetd   │  schedule, ACL, quotas
                    │  + event log    │
                    └────────┬────────┘
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    project A           project B           project N
    .agents/runs        .agents/runs        .agents/runs
    run-controller      run-controller      run-controller
    writers/night       writers/night       writers/night
           │                 │                 │
           └──────────── git main ─────────────┘
                      receipts stay in repo
```

**Solo path remains:** human → dev-orchestrator → run-supervisor → controller (no fleet required).  
**Fleet path adds:** registration + global slots + aggregate HANDOFF; does not replace controller.

---

## 5. Workstreams & ownership

| Workstream | Phases | Primary owner |
|------------|--------|---------------|
| Day reliability | A | dev-orchestrator + worker on bin/ |
| Night + telemetry | B | night-* tools + Board |
| Freeze/fork | C | human + docs |
| Fleet daemon/API | D | new lane-fleet package |
| Multi-op + channels | E | fleet + thin adapters |
| Multica harvest | F | research weekly + adapt PRs |

---

## 6. Milestones & gates

| Milestone | Gate | Approx |
|-----------|------|--------|
| **M-S2** Stable Solo | Phase A+B exit checklists | 3–5 weeks |
| **M-F1** Fleet MVP | Phase D exit | +3–6 weeks |
| **M-M1** Multica-class | Phase E1–E3 | +4–8 weeks |
| **M-M2** Best Multica | Phase F matrix 80% high-value | ongoing quarterly |

**Hard gate:** no Phase D code on solo critical path until **M-S2**.  
**Hard gate:** no public “we are Multica” claim until **M-M1** receipts+ACL.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Fleet rewrite breaks solo | Fork + schema versioning + backport only via PR |
| Multica merge spaghetti | Capability matrix + reject list; no wholesale merge |
| Channels become root shell | API-only actions; audit log; deny raw bash from bot |
| Slot exhaustion / host melt | Global provider pool (D5) before multi-project spam |
| HANDOFF lies | A1 receipt honesty first |
| Scope creep (“full SaaS”) | H3 stops at multi-op + channels; SaaS = separate product later |

---

## 8. Immediate next actions (this week)

1. **Approve this plan** (human).  
2. Open Phase A run(s) in order: **A1 → A2 → A3 → A4 → A5** (one durable run per cluster or one epic run with tasks).  
3. Create empty living files when A starts:  
   - `docs/plans/multica-capability-matrix.md` (stub)  
   - PROGRESS Next rewritten to match Phase A checklist  
4. Do **not** start fleet daemon until A1+A2 green.  
5. Optional: weekly 30‑min “Multica digests” only after M-S2 or in parallel as research-only todos (no code).

---

## 9. Success metrics

### Solo (S2)

- Micro run success rate ≥95% on golden projects (first attempt or one typed retry)  
- Zero known classes: masked exit=0, missing check.py under worktree, false provider_incomplete on trusted codex primary  
- Night review completes on large day without manual chunking  
- Cold start ≤2 minutes to actionable Next  

### Fleet (F1)

- ≥5 projects supervised by one daemon  
- Global writer slots never exceeded  
- Aggregate HANDOFF answers “where to intervene” in one view  

### Multica-class (M1–M2)

- ≥2 operators without shared root shell  
- ≥1 channel adapter for alerts/actions  
- ≥N Multica UX features adapted with matrix evidence  
- Solo install path still one `./install.sh`  

---

## 10. Explicit non-goals (parked)

- Replacing Claude Code / Codex / Kimi CLIs  
- Multi-PM editing one branch without owns_paths  
- Daytime LLM review on every task  
- Telegram-first product (channel is optional client)  
- Billing/multi-tenant SaaS  
- Autonomous “agent society” without receipts  

---

## 11. One-page summary

```text
NOW ──► Phase A day trust ──► Phase B night+telemetry ──► S2 STABLE SOLO
                                                              │
                                                              ▼
                                              Phase C freeze + fork
                                                              │
                                                              ▼
                                              Phase D fleet daemon+API
                                                              │
                                              ┌───────────────┴───────────────┐
                                              ▼                               ▼
                                    Phase E multi-op/channels     Phase F Multica PR harvest
                                              │                               │
                                              └──────────► M2 Best Multica ◄──┘
```

**До какого уровня дописать текущую систему?**  
→ **S2 (Phase A+B fully green)** — не меньше. Это минимум, после которого multi не будет стоять на гнилых receipts.

**Как улучшить до лучшего мультика?**  
→ Форк fleet (D) → multi-op/channels (E) → систематический harvest Multica/peer PR (F) в наш control plane, а не chat-orchestrator.

---

## 12. Changelog for this plan

| Date | Note |
|------|------|
| 2026-08-04 | Initial full plan from stable-solo + multica strategy discussion |
