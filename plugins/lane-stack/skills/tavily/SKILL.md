---
name: tavily
description: "Tavily REST search and cited research. Key in ~/secrets/tavily.env. Use when: tavily, поиск в интернете, cited report, источники с URL. SKIP: one known URL (WebFetch); X/Twitter slang (grok); SEO SERP (seo-specialist)."
argument-hint: "[search|research]"
---

# Tavily

Host skill. Not the skills.sh `tvly` CLI pack. REST only.

Session agent: `tavily` (`cc tavily`). Copy-lead writes under `.agents/copy/research/inbox/`.

```bash
set -a; source ~/secrets/tavily.env; set +a
test -n "$TAVILY_API_KEY" || { echo "MISSING ~/secrets/tavily.env"; exit 1; }
```

No file / empty key → stop. Do not print the key. Do not `npx skills add`.

Query = search string, **< 400 chars**, not an essay. Split fat questions into 2–4 calls.

One note per query. Never append to a single `web.md`.

```bash
if [ -d .agents/copy ]; then
  INBOX=.agents/copy/research/inbox
else
  INBOX=.agents/research/inbox
fi
STAMP=$(date +%F)-<slug>
mkdir -p "$INBOX"
```

Copy the research-note template to `$INBOX/$STAMP.md`. Dump JSON beside it as `$STAMP.json`. Add a row to `.agents/copy/INDEX.md` when that board exists. Do not dump raw HTML into chat.

## search (default)

Facts, examples, language snippets, a handful of URLs. Seconds.

```bash
curl -sS -X POST https://api.tavily.com/search \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"<QUERY>","max_results":5,"search_depth":"basic","include_answer":true}' \
  > "$INBOX/$STAMP.json"
```

Useful fields (omit if unused):

| Field | Values |
|---|---|
| `search_depth` | `basic` (default), `advanced` |
| `max_results` | 1–20 |
| `topic` | `general`, `news`, `finance` |
| `time_range` | `day`, `week`, `month`, `year` |
| `include_domains` / `exclude_domains` | arrays of hosts |
| `include_raw_content` | `false` unless you need page text |

Then fill `$INBOX/$STAMP.md` (claim + URL + snippet). Invented slang = delete.

## research (report)

Only when the human wants a **cited report** (landscape / ЦА / compare) and a time budget. 30–120s. Not for «найди 3 примера».

`input` may be a longer brief than a search query.

```bash
req=$(curl -sS -X POST https://api.tavily.com/research \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input":"<BRIEF>","model":"mini","output_length":"standard"}')
echo "$req" > "$INBOX/$STAMP-job.json"
id=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["request_id"])' <<<"$req")
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  code=$(curl -sS -o "$INBOX/$STAMP.json" -w '%{http_code}' \
    -H "Authorization: Bearer $TAVILY_API_KEY" \
    "https://api.tavily.com/research/$id")
  [ "$code" = "200" ] && break
  sleep 10
done
```

| `model` | When |
|---|---|
| `mini` | one topic (~30s) — default |
| `pro` | compare / multi-angle (~60–120s) |
| `auto` | let Tavily pick |

Ask duration if unknown: «Сколько крутить ресёрч?» Unknown → `mini`.

Copy `content` + `sources` into `$INBOX/$STAMP.md` (`kind: report`). Report sentences are leads, not buyer quotes. After a lift into copy files: `mv` the note to `research/used/`.

## NEVER

- Print `TAVILY_API_KEY` or the env file
- Install `tvly` / skills.sh Tavily packs
- `/research` for one URL or a top-N list
- Raw HTML in chat
- Treat a snippet as a confirmed customer quote
- Append into `web.md` / `deep.md` at the research root
