# Module: routing-agents

## Purpose
Единая кастомизация **кто** исполняет каждый SEO-этап: один default на всю систему или override по stage.

## Supported systems

| Роль | Системы |
|---|---|
| Writers / CLI | `claude-code`, `qwen`, `kimi`, `codex`, `cursor`, `grok`, `deepseek-flash`, `deepseek-pro`, `gpt` |
| Transcription | `groq`, `codex` |
| Embeddings | `openai`, `gemini` |

## Stages
`deep_research` · `discovery` · `intent_analysis` · `strategy` · `technical` · `content_gist` · `content_quality` · `brand_entity` · `offpage` · `measurement` · `clustering` · `transcription` · `embeddings`

## Config locations
1. Global: `~/.agents/seo-services/routing.yaml` (via **seodoc** Agents / Embed tabs)
2. Project override: `.agents/seo/<slug>/routing.yaml`

## CLI

```bash
seo-routing show
seo-routing set-default claude-code
seo-routing set-stage intent_analysis deepseek-flash
seo-routing set-stage embeddings openai --model text-embedding-3-small
seo-routing resolve deep_research
seo-dispatch <proj> <run> <task> --stage intent_analysis --original … --output …
```

## Protocol
1. Human sets global default + stage overrides in seodoc (or CLI).
2. Orchestrator calls `seo-routing resolve <stage>` (or `seo-dispatch --stage`).
3. Worker package gets executor + cli_hint; does not invent model choice.
