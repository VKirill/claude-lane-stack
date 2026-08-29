# Module: clustering-serp

## Purpose
1. Снять SERP (xmlstock / xmlriver) для набора запросов.
2. Сохранить сырые выдачи в проекте.
3. Кластеризовать (LLM-слой) с настраиваемой **temperature** — можно менять температуру и пересобирать кластеры **без** повторного fetch.

## TUI (seodoc → Cluster)

| Поле | Значения |
|---|---|
| SERP provider | `xmlstock` \| `xmlriver` |
| Engine | `yandex` \| `google` |
| TOP-N | `10` \| `20` \| `30` |
| temperature | `0.0`–`1.0` (LLM clustering) |
| save_serp | true/false |
| use_proxy | true/false (proxy6) |

## CLI

```bash
# settings
seo-routing set-cluster --provider xmlstock --engine yandex --top 10 --temperature 0.2

# fetch + save
seo-serp-save acme --query "купить диван" --query "диван москва"
seo-serp-save acme --queries-file queries.txt

# artifacts
.agents/seo/acme/evidence/serp/yandex-top10-<ts>/
  <query>.raw
  manifest.json
.agents/seo/acme/evidence/serp/LATEST   # points to latest dump dir name
```

## Re-cluster without re-fetch
1. Point agent at `evidence/serp/LATEST` (or specific dir).
2. `seo-routing set-cluster --temperature 0.45` (or seodoc).
3. Run clustering stage worker (`seo-dispatch … --stage clustering`) with SERP dumps as inputs.

## Embeddings assist (optional)
If methodology needs vector assist: `stages.embeddings.system` = `openai` \| `gemini` (Embed tab).
