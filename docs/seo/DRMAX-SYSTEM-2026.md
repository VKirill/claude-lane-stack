# DrMax SEO system (host stack) — 2026-08

## What was integrated

Sources under `/home/ubuntu/downloads/drmax_update`:

| Source | Role |
|---|---|
| `drmax chanel.7z` | Official @DrMaxSEO export → channel corpus (ids through ~1661) |
| `drmax promt.7z` | @DrMaxPrompt export → originals + prompt-channel corpus (through id 83) |
| Prompt book zip v1.5 | 25 systems + bonuses (hashes match prior skill pack) |
| `Доказательное SEO 2026` PDF | Re-extracted book markdown |
| GIST pocketbook PDF | Re-extracted pocketbook |

Importer: `~/.agents/skills/seo-prompt-engineering-2026/scripts/import_drmax_sources.py`  
Validation: `…/scripts/validate_drmax_corpus.py` (194 exact originals at last import).

## Skill map

| Skill | Role |
|---|---|
| `seo-drmax-orchestrator` | **Master**: phases, activation, `.agents/seo/`, workers |
| `seo-prompt-engineering-2026` | Canonical originals + channel/book corpus |
| `seo-evidence-based-2026` | Leak-signal execution capabilities |
| `seo-copywriting` | On-page copy mechanics |
| `ai-detect` | LinguaForensic **v3.9.4** (was 3.8.6 body) |
| `drmax-latent-intent` | Latent Intent Analyst v2.2 |
| `drmax-cvd` | Content Value Detector v2.3 |
| `drmax-text-humanization` | Humanization v1.6.1 + help/scenarios |
| `drmax-lexadapt` | LexAdapt v1.5 |

Agent: `~/.claude/agents/seo-specialist.md` (orchestrator behavior + bootstrap).

Templates: `~/.agents/templates/seo-project/{PROJECT,STATUS,BOARD}.md`

## Prompt-channel systems (semantic roles)

| IDs | System | When |
|---|---|---|
| 4–6 | Assessor MC lite/full + Spam | Quality / scaled spam before publish |
| 7 | Trend v4 | Early demand shifts |
| 12 | SEO TITAN OS | Wide strategic OS analysis |
| 13–20, 71–72 | GIST family → **v3.3 canonical** | Page creation/audit non-replaceable content |
| 21–22 | page-audit-001, SERP Barrier Breaker | Ranking pipeline / “good but loses” |
| 23 | Chunk Sentinel | RAG chunking / extractability |
| 25–37 | Reddit Mapper 0–6 | Audience voice → clusters |
| 40–47 | Listicle Citation Engine | Link/citation outreach |
| 48–49 | Forensic SEO DD v2→**v3** | YouTube idea mining |
| 50–56 | SemanticRank Orchestrator | Semantic HTML + AI citation readiness |
| 57–58 | Entity Footprint | Brand entity in Google/LLM |
| 59–60 | Brand Poisoning Forensics | Negatives / coordination |
| 61–62 | Market-Scoped Differentiation | Locale versions |
| 63 | InfoGapRadar | Information gaps |
| 64–65 | LSI 2.0 | LLM citability audit |
| 66–67 | Imperial Steam Onion | Satire only — not SEO |
| 70→**83** | LinguaForensic 3.8.12→**3.9.4** | AI text detect/rewrite |
| 73 | VeriScan | Fake reviews |
| 74 | LexAdapt | CEFR/ТРКИ simplify |
| 77 | CVD v2.3 | Replaceability / RSP |
| 79–81 | Text Humanization 1.6.1 | Post-GIST editorial |
| 82 | Latent Intent v2.2 | Hidden intents of one query |

Book systems 01–25 remain the research library; competitive bonus chain order is fixed in `prompt-systems-guide.md`.

## Project artifact root

```text
.agents/seo/<project-slug>/
  PROJECT.md STATUS.md BOARD.md
  passport/ discovery/ strategy/ technical/
  content/ offpage/ measurement/ evidence/
  prompts-used/ runs/
```

Code SEO fixes still go through `.agents/runs/` + `dev-orchestrator`.

## Re-import later

```bash
python3 ~/.agents/skills/seo-prompt-engineering-2026/scripts/import_drmax_sources.py \
  --channel <export-dir> \
  --prompt-channel <export-dir> \
  --book-pack <v1-5-dir> \
  --evidence-pdf <pdf> \
  --gist <gist-dir-with-skill-md-and-pocketbook-pdf> \
  --chat <optional-chat-export>
python3 ~/.agents/skills/seo-prompt-engineering-2026/scripts/validate_drmax_corpus.py \
  ~/.agents/skills/seo-prompt-engineering-2026
```


## Harness CLI (full control plane)

```bash
export PATH="$HOME/.agents/bin:$PATH"
ccs                                    # claude --agent seo-specialist
# or: cc → key s

seo-init <slug> --domain example.com
seo-resume .
seo-run-init <slug> <run> --title "..." --phase discovery
seo-task <slug> <run> add|list|set-status|accept
seo-dispatch <slug> <run> <id> --original /abs --output path --executor grok
seo-prompt-log <slug> --system "..." --path "..." --artifact path
seo-board . && seo-handoff-write .
```

Control-plane doc: [SOLO-SEO-ORCHESTRATION.md](SOLO-SEO-ORCHESTRATION.md)
