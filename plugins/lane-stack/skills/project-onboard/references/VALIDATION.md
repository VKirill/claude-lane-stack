# Pack validation — refuse STATUS: complete until green

Deep Phase 5 must run these and record `VALIDATION: pass|fail`.

## Automated / shell

```bash
set -euo pipefail
leftovers=$(grep -R "REPLACE_ME" llms.txt docs/llm CLAUDE.md AGENTS.md 2>/dev/null | grep -v DESIGN.md | grep -v 'description: REPLACE' || true)
if [ -n "$leftovers" ]; then
  echo "FAIL REPLACE_ME leftovers:"
  echo "$leftovers"
  exit 1
fi

python3 - <<'PY'
import re
import yaml
from pathlib import Path

def load(p):
    return yaml.safe_load(Path(p).read_text(encoding="utf-8"))

for p in [
    "docs/llm/MODULE_MAP.yaml",
    "docs/llm/API_SURFACE.yaml",
    "docs/llm/MANIFEST.yaml",
    "docs/llm/TAXONOMY.yaml",
    "docs/llm/TEST_INDEX.yaml",
]:
    assert Path(p).is_file(), p
    load(p)
print("yaml ok")

mods = load("docs/llm/MODULE_MAP.yaml").get("modules") or []
assert len(mods) >= 3, f"modules={len(mods)}"
for x in mods:
    assert x.get("id") and x.get("path") and x.get("responsibility")
    mp = Path(str(x["path"]).split(":")[0])
    assert mp.exists(), f"module path missing: {x['id']} -> {x['path']}"

# Deep monorepo: apps/* coverage or GAPS in report (checked manually); soft count
apps = [p for p in Path("apps").glob("*/package.json")] if Path("apps").is_dir() else []
mod_paths = {str(m.get("path") or "").rstrip("/") for m in mods}
if len(apps) >= 4:
    covered = 0
    for pkg in apps:
        root = str(pkg.parent)
        if any(root == mp or root.startswith(mp + "/") for mp in mod_paths):
            covered += 1
    print("apps_covered", covered, "/", len(apps))
    assert covered >= max(3, len(apps) // 2), (
        f"MODULE_MAP covers only {covered}/{len(apps)} apps — add modules or list GAPS"
    )

# Per-app packs (monorepo): sequential walk should leave CLAUDE + docs/INDEX per app
app_packs_ok = []
app_packs_missing = []
for pkg in apps:
    app_dir = pkg.parent
    # skip obvious empty stubs (no src/app/server besides package.json)
    codeish = any(
        (app_dir / n).exists()
        for n in ("src", "app", "server", "lib", "cmd", "internal")
    ) or any(app_dir.glob("*.ts")) or any(app_dir.glob("*.tsx"))
    if not codeish and not (app_dir / "Dockerfile").exists():
        continue
    claude = app_dir / "CLAUDE.md"
    index = app_dir / "docs" / "INDEX.md"
    if claude.is_file() and index.is_file():
        app_packs_ok.append(app_dir.name)
    else:
        app_packs_missing.append(app_dir.name)
print("app_packs_ok", len(app_packs_ok), app_packs_ok[:12])
print("app_packs_missing", len(app_packs_missing), app_packs_missing[:12])
report_blob = ""
for cand in (
    Path(".agents/runs/_onboard/artifacts/001/report.md"),
    Path(".agents/runs/_onboard/artifacts/001/phase4b-app-packs.md"),
    Path(".agents/runs/_onboard/artifacts/001/phase4-passport.md"),
):
    if cand.is_file():
        report_blob += cand.read_text(encoding="utf-8", errors="replace")
if apps and report_blob and "APP_PACKS" not in report_blob:
    print("WARN: report missing APP_PACKS line")
if len(apps) >= 3:
    # Deep bar: majority of real apps get a local pack, or every miss is explained in APP_PACKS/GAPS
    if app_packs_missing:
        explained = all(
            name in report_blob for name in app_packs_missing
        ) and ("APP_PACKS" in report_blob or "GAPS:" in report_blob)
        assert len(app_packs_ok) >= max(2, (len(app_packs_ok) + len(app_packs_missing)) // 2) or explained, (
            "per-app packs missing for: "
            + ", ".join(app_packs_missing)
            + " — walk each apps/* or explain skips in APP_PACKS"
        )

# Per-app pack quality: refuse template-thin / catch-all-only catalogs
thin_packs = []
catchall_packs = []
root_surfs = []
root_api_path = Path("docs/llm/API_SURFACE.yaml")
if root_api_path.is_file():
    root_surfs = load("docs/llm/API_SURFACE.yaml").get("surfaces") or []
for name in app_packs_ok:
    app_dir = Path("apps") / name
    arch = app_dir / "docs" / "ARCHITECTURE.md"
    flows = app_dir / "docs" / "llm" / "FLOWS.md"
    surf_p = app_dir / "docs" / "llm" / "API_SURFACE.yaml"
    got = app_dir / "docs" / "GOTCHAS.md"
    if arch.is_file() and len(arch.read_text(encoding="utf-8", errors="replace").splitlines()) < 25:
        thin_packs.append(f"{name}/ARCHITECTURE")
    if flows.is_file():
        ft = flows.read_text(encoding="utf-8", errors="replace")
        if len(ft.splitlines()) < 20 and ft.count("path:") + len(re.findall(r":\d+", ft)) < 4:
            thin_packs.append(f"{name}/FLOWS")
    if got.is_file() and len(got.read_text(encoding="utf-8", errors="replace").splitlines()) < 8:
        thin_packs.append(f"{name}/GOTCHAS")
    if surf_p.is_file():
        local = load(str(surf_p)).get("surfaces") or []
        ids = " ".join(str(s.get("id") or "") for s in local)
        if re.search(r"apple\|google|yookassa\||/v1/\*|authenticated/\*", ids):
            catchall_packs.append(name)
        # Composition roots: local surface count must not be tiny vs root projection
        root_for_app = [s for s in root_surfs if str(s.get("path") or "").startswith(f"apps/{name}/")]
        if name in {"api", "worker"} and root_for_app:
            if len(local) < max(8, len(root_for_app) // 2):
                thin_packs.append(
                    f"{name}/API_SURFACE({len(local)}<{max(8, len(root_for_app)//2)} vs root {len(root_for_app)})"
                )
print("thin_packs", thin_packs)
print("catchall_packs", catchall_packs)
flows = Path("docs/llm/FLOWS.md")
assert flows.is_file(), "docs/llm/FLOWS.md missing"
ft = flows.read_text(encoding="utf-8", errors="replace")
assert "REPLACE_ME" not in ft, (
    "docs/llm/FLOWS.md still has REPLACE_ME — write the SoT file, not only phase3-flows.md"
)
flow_cites = ft.count("path:") + len(re.findall(r":\d+", ft))
assert flow_cites >= 6, f"docs/llm/FLOWS.md too thin cites={flow_cites}"
for name in app_packs_ok:
    t = (Path("apps") / name / "CLAUDE.md").read_text(encoding="utf-8", errors="replace")
    if "## What" not in t or "## Verify" not in t or (
        "## Never" not in t and "## Always" not in t
    ):
        raise AssertionError(
            f"stub apps/{name}/CLAUDE.md — need What + Never/Always + Verify"
        )
    if not re.search(r":\d+", t):
        raise AssertionError(f"apps/{name}/CLAUDE.md missing file:line evidence")
assert not catchall_packs, (
    "per-app API_SURFACE still uses catch-all ids — split providers/families: "
    + ", ".join(catchall_packs)
)
assert not thin_packs, (
    "per-app packs too thin for agent work — expand ARCHITECTURE/FLOWS/GOTCHAS/API_SURFACE: "
    + ", ".join(thin_packs)
)

tax = load("docs/llm/TAXONOMY.yaml")
assert tax.get("framework") == "diataxis"
paths = {e.get("path") for e in (tax.get("entries") or []) if isinstance(e, dict)}
for must in ("CLAUDE.md", "docs/llm/API_SURFACE.yaml", "docs/llm/TAXONOMY.yaml"):
    assert must in paths, must

manifest = load("docs/llm/MANIFEST.yaml")
always = (manifest.get("pack") or {}).get("always_load") or []
for heavy in ("docs/llm/MODULE_MAP.yaml", "docs/llm/DOC_LAYOUT.md"):
    assert heavy not in always, f"{heavy} must not be in MANIFEST always_load"

surfs = load("docs/llm/API_SURFACE.yaml").get("surfaces") or []
assert len(surfs) >= 1, "empty API_SURFACE"
webhook_ids = [s.get("id", "") for s in surfs if s.get("kind") == "webhook"]
# Catch-all only: fail when multiple webhook* route files exist
wh_files = list(Path(".").glob("**/webhooks*.ts")) + list(Path(".").glob("**/webhooks*.py"))
wh_files = [p for p in wh_files if "node_modules" not in str(p) and "__tests__" not in str(p)]
if len(wh_files) >= 3:
    assert len(webhook_ids) >= 2, (
        "multiple webhook handlers found — split API_SURFACE webhook entries per provider"
    )
    assert not any(re.search(r"webhooks/\*$", i) and len(webhook_ids) == 1 for i in webhook_ids)

unk = [s.get("id") for s in surfs if s.get("auth") == "unknown"]
print("auth_unknown", len(unk), "/", len(surfs))
# Soft: >40% unknown → fail deep quality bar
if surfs:
    assert len(unk) / len(surfs) <= 0.4, f"too many auth:unknown ({len(unk)}/{len(surfs)})"

tests = load("docs/llm/TEST_INDEX.yaml").get("tests") or []
print("modules", len(mods), "surfaces", len(surfs), "tests", len(tests), "webhooks", len(webhook_ids))
PY

# has_ui → DESIGN Google format
if grep -q 'has_ui: 1' .agents/onboard.scenario.yaml 2>/dev/null; then
  test -f docs/DESIGN.md
  head -1 docs/DESIGN.md | grep -q '^---'
  npx --yes @google/design.md lint docs/DESIGN.md || echo "WARN: design.md lint unavailable"
fi

python3 - <<'PY'
from pathlib import Path
text = Path(".agents/onboard.scenario.yaml").read_text(encoding="utf-8") if Path(".agents/onboard.scenario.yaml").is_file() else ""
if "deploy: 1" in text or "has_deploy: 1" in text:
    assert Path("docs/RUNBOOK.md").is_file(), "RUNBOOK missing for has_deploy"
    print("runbook ok")
# Deep full: decisions should have ADR headings or GAPS noted in report later
dec = Path("docs/decisions.md")
if dec.is_file():
    body = dec.read_text(encoding="utf-8")
    adrs = body.count("## ADR-")
    print("adr_count", adrs)
PY

python3 - <<'PY'
from pathlib import Path
t = Path("CLAUDE.md").read_text(encoding="utf-8")
body = t.split("<!-- gitnexus:start -->")[0]
assert len(body.splitlines()) <= 220, len(body.splitlines())
print("claude_lines", len(body.splitlines()))
PY

# Phase artifacts required for deep
python3 - <<'PY'
from pathlib import Path
import os
art = Path(os.environ.get("ARTIFACT_DIR", ".agents/runs/_onboard/artifacts/001"))
need = [
    "phase1-layout.md",
    "phase2-maps.md",
    "phase3-flows.md",
    "phase4-passport.md",
    "phase5-critique.md",
    "report.md",
]
missing = [n for n in need if not (art / n).is_file()]
# Monorepo deep: phase4b required when apps/* exist
if Path("apps").is_dir() and any(Path("apps").glob("*/package.json")):
    if not (art / "phase4b-app-packs.md").is_file():
        missing.append("phase4b-app-packs.md")
print("artifact_dir", art)
print("missing_artifacts", missing)
assert not missing, f"phase artifacts missing: {missing}"
PY
```

## Manual acceptance

| File | Diátaxis | Pass if |
|------|----------|---------|
| CLAUDE.md | how-to | Real Never/Always + verify; pointer to INDEX |
| AGENTS.md | how-to | Pointer / short; no architecture paste |
| llms.txt / INDEX | reference | Links resolve; no REPLACE_ME; lean always-load |
| TAXONOMY.yaml | reference | Entries match existing pack; omit tutorials |
| MODULE_MAP | reference | Paths exist; apps coverage or GAPS; runners/hot libs when present |
| API_SURFACE | reference | Ids resolve; webhooks split per provider; auth mostly resolved; OpenAPI in `sources` |
| TEST_INDEX | reference | ≥1 real command from repo scripts/CI (deep) |
| FLOWS | explanation | ≥3 flows; notification flow includes stream + queue consumer when those exist |
| ARCHITECTURE | explanation | Boundaries, not file tree |
| decisions.md | explanation | 3–5 evidenced ADRs (deep full) or explicit GAPS |
| DESIGN (UI) | reference | Google front matter + sections; lint attempted |
| RUNBOOK (deploy) | how-to | Start/smoke/rollback from real infra |
| Per-app pack | how-to+ref | Filled local passport (not stubs); surfaces projected/split; FLOWS evidenced |
| Report | — | PIPELINE incl. phase4b; `APP_PACKS:` + quality notes for api/worker |

## Fail → STATUS: partial

- Empty API_SURFACE with HTTP routes / many CLIs  
- MODULE_MAP &lt; 3 on non-toy; apps coverage &lt; half without GAPS  
- Single catch-all webhook surface when many webhook handlers exist  
- `auth: unknown` on &gt;40% of surfaces  
- MANIFEST `always_load` includes MODULE_MAP or DOC_LAYOUT  
- Empty TEST_INDEX when package scripts/CI exist  
- has_ui but DESIGN stub / no YAML front matter  
- has_deploy but no RUNBOOK  
- TAXONOMY missing or out of sync  
- Phase artifact missing / cannot write `ARTIFACT_DIR`  
- Deep full with empty decisions and no GAPS note  
- Monorepo deep without phase4b / without walking apps/*  
- Majority of apps missing local CLAUDE+docs/INDEX with no APP_PACKS skip reasons  
- Local app pack that only pastes root ARCHITECTURE (must be scoped)  
- Thin local ARCHITECTURE/FLOWS/GOTCHAS or catch-all-only local API_SURFACE  
- `api`/`worker` local surfaces ≪ root projection for that app  
- `docs/llm/FLOWS.md` still `REPLACE_ME` or missing `path:line` (phase3 artifact is not SoT)  
- `apps/*/CLAUDE.md` is Owns+Pointers only (no What / Never / Verify / file:line)  

