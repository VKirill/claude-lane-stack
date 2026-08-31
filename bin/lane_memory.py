"""SMA 5.6.1 memory canons — files are truth; CORE always loaded; no embeddings."""
from __future__ import annotations

import hashlib
import math
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

MEMORY_TYPES = frozenset(
    {
        "working",
        "semantic",
        "episodic",
        "procedural",
        "normative",
        "preference",
        "prospective",
    }
)
TRUTH_MODES = frozenset(
    {"observed", "inferred", "factual", "hypothesis", "decision", "normative"}
)
STATUSES = frozenset(
    {"draft", "active", "superseded", "revoked", "expired", "archived"}
)
DEAD_STATUSES = frozenset({"superseded", "revoked", "expired", "archived"})
SENSITIVITIES = frozenset({"public", "internal", "sensitive", "encrypted-required"})
SENS_RANK = {"public": 0, "internal": 1, "sensitive": 2, "encrypted-required": 3}
AUD_CEILING = {"owner": 3, "subagent": 1, "export": 0}
LINK_TYPES = frozenset(
    {
        "derived_from",
        "supports",
        "contradicts",
        "supersedes",
        "caused_by",
        "applies_to",
        "exception_to",
        "requires",
        "verified_by",
        "owned_by",
        "part_of",
    }
)
REQUIRED = (
    "id",
    "schema_version",
    "status",
    "memory_type",
    "truth_mode",
    "claim",
    "language",
    "sensitivity",
)
GENERATED_NAMES = frozenset({"MEMORY.md", "TAGS.md", "GOLDEN.yaml"})
DRAFT_TEMPLATE = """---
id: your-fact-id
schema_version: 2
status: active
memory_type: normative
truth_mode: decision
claim: One sentence that will fire again next month
language: en
source:
  authority: owner
evidence:
  - type: conversation
    ref: YYYY-MM-DD
risk: low
sensitivity: internal
context_priority: always
retrieval:
  areas: [procedures]
  hint: synonyms, including russian
verification:
  command: test -f .agents/PROGRESS.md
---

Why this rule exists. Related: [[other-id]].
Copy this file, rename to <id>.md, replace placeholders, then:
lane-memory write --apply .agents/memory/drafts/<id>.md --confirm .agents/memory/<id>.md --yes
"""
CORE_MARK_START = "<!-- lane-memory:core -->"
CORE_MARK_END = "<!-- /lane-memory:core -->"
DEFAULTS = {
    "core_budget": 3072,
    "note_budget": 8000,
    "index_budget": 65536,
    "context_budget": 2500,
    "audience": "subagent",
    "search_engine": "auto",
    "inject": True,
    "maintain": True,
    "personal_bot": "",
}
LANGUAGES = frozenset({"en", "ru"})
PATH_RE = re.compile(r"(?:[\w.-]+/)+[\w.-]+|[\w.-]+\.[A-Za-z][\w.-]*")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA |OPENSSH )?PRIVATE KEY"
    r"|password\s*=\s*\S+|api[_-]?key\s*=\s*\S+)",
    re.I,
)
INJECT_RE = re.compile(
    r"(ignore (all )?(previous|prior) instructions|"
    r"забудь(те)? (все )?(прежние |предыдущие )?инструкции|"
    r"forget (all )?(previous|prior) instructions)",
    re.I,
)
RELATIVE_DATE_RE = re.compile(
    r"\b(вчера|позавчера|на прошлой неделе|yesterday|last week)\b", re.I
)
NEGATION = frozenset({"не", "нельзя", "нет", "not", "never", "no", "without"})
RRF_K = 60


def corpus_dir(repo: Path) -> Path:
    return Path(repo) / ".agents" / "memory"


def cls_dir(repo: Path) -> Path:
    """Was .sma/ — derived index + this-machine-only. First-level .cls/."""
    return Path(repo) / ".cls"


def local_dir(repo: Path) -> Path:
    neu = cls_dir(repo) / "local-memory"
    mid = Path(repo) / ".agents" / "sma" / "local-memory"
    old = Path(repo) / ".agents" / "memory.local"
    if neu.is_dir() or (not mid.is_dir() and not old.is_dir()):
        return neu
    if mid.is_dir():
        return mid
    return old


def tags_path(repo: Path) -> Path:
    return corpus_dir(repo) / "TAGS.md"


def memory_index_path(repo: Path) -> Path:
    return corpus_dir(repo) / "MEMORY.md"


def index_dir(repo: Path) -> Path:
    neu = cls_dir(repo) / "index"
    mid = Path(repo) / ".agents" / "sma" / "index"
    old = corpus_dir(repo) / ".index"
    if neu.is_dir() or (not mid.is_dir() and not old.is_dir()):
        return neu
    if mid.is_dir():
        return mid
    return old


def sqlite_path(repo: Path) -> Path:
    return index_dir(repo) / "memory-lexical.sqlite"


def stage_settings(repo: Path) -> dict[str, Any]:
    bin_dir = Path(__file__).resolve().parent
    if str(bin_dir) not in sys.path:
        sys.path.insert(0, str(bin_dir))
    from pipeline_stages import resolve_memory  # noqa: WPS433

    return resolve_memory(Path(repo))


def settings(repo: Path) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    try:
        raw = stage_settings(repo)
    except Exception:
        raw = {}
    out = dict(DEFAULTS)
    for key, default in DEFAULTS.items():
        if key not in raw or raw.get(key) in (None, ""):
            continue
        if isinstance(default, bool):
            out[key] = str(raw[key]).strip().lower() in {"1", "true", "yes", "on"}
        elif isinstance(default, int):
            try:
                out[key] = int(raw[key])
            except (TypeError, ValueError):
                out[key] = default
        else:
            out[key] = str(raw[key]).strip() or default
    out["enabled"] = bool(raw.get("enabled"))
    out["audience"] = out["audience"] if out["audience"] in AUD_CEILING else "subagent"
    engine = str(out["search_engine"])
    if engine not in {"auto", "fts5", "bm25"}:
        out["search_engine"] = "auto"
    bot = str(out.get("personal_bot") or "").strip()
    if not bot:
        bot = str(os.environ.get("LANE_MEMORY_BOT") or "").strip()
    out["personal_bot"] = bot
    return out


def enabled(repo: Path) -> bool:
    try:
        return bool(stage_settings(repo).get("enabled"))
    except Exception:
        return False


def _split_fm(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    rest = text[3:]
    end = rest.find("\n---")
    if end < 0:
        return {}, text
    meta = yaml.safe_load(rest[:end]) or {}
    if not isinstance(meta, dict):
        return {}, text
    return meta, rest[end + 4 :].lstrip("\n")


def _clean_meta(meta: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in meta.items() if not str(k).startswith("_")}


def _dump_record(meta: dict[str, Any], body: str) -> str:
    dumped = yaml.safe_dump(_clean_meta(meta), allow_unicode=True, sort_keys=False).rstrip()
    return f"---\n{dumped}\n---\n\n{body.rstrip()}\n"


def tag_catalog(repo: Path) -> dict[str, set[str]]:
    """canonical -> {canonical + aliases}."""
    path = tags_path(repo)
    catalog: dict[str, set[str]] = {}
    current = ""
    if not path.is_file():
        return catalog
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if not raw.lstrip().startswith("- "):
            continue
        name = raw.lstrip()[2:].split(":")[0].strip("`, ")
        if not name:
            continue
        if indent == 0:
            current = name
            catalog.setdefault(current, {current})
        elif current:
            catalog[current].add(name)
    return catalog


def resolve_tag(repo: Path, raw: str) -> str:
    token = raw.strip()
    catalog = tag_catalog(repo)
    if token in catalog:
        return token
    for canon, names in catalog.items():
        if token in names:
            return canon
    return token


def allowed_tags(repo: Path) -> set[str]:
    return set(tag_catalog(repo))


def iter_record_paths(repo: Path) -> list[Path]:
    out: list[Path] = []
    roots = [corpus_dir(repo), local_dir(repo)]
    for legacy in (
        Path(repo) / ".agents" / "sma" / "local-memory",
        Path(repo) / ".agents" / "memory.local",
    ):
        if legacy.is_dir() and legacy.resolve() != local_dir(repo).resolve():
            roots.append(legacy)
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            if path.name in GENERATED_NAMES or path.name.startswith("INDEX-"):
                continue
            if path.parent.name in {".index", "drafts", "episodes"}:
                continue
            out.append(path)
    return out


def load_record(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    meta, body = _split_fm(text)
    meta["_path"] = path
    meta["_body"] = body
    meta["_text"] = text
    return meta


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[0-9A-Za-zА-Яа-яЁё_-]+", text or "")]


def convert_relative_dates(text: str, today: date | None = None) -> str:
    today = today or date.today()
    table = {
        "вчера": (today - timedelta(days=1)).isoformat(),
        "позавчера": (today - timedelta(days=2)).isoformat(),
        "на прошлой неделе": (today - timedelta(days=7)).isoformat(),
        "yesterday": (today - timedelta(days=1)).isoformat(),
        "last week": (today - timedelta(days=7)).isoformat(),
    }

    def repl(match: re.Match[str]) -> str:
        return table.get(match.group(0).lower(), match.group(0))

    return RELATIVE_DATE_RE.sub(repl, text)


def is_trusted(record: dict[str, Any]) -> tuple[bool, str]:
    blob = f"{record.get('claim', '')}\n{record.get('_body', '')}"
    if INJECT_RE.search(blob):
        return False, "untrusted: addresses the assistant"
    return True, ""


def audience_ok(record: dict[str, Any], audience: str) -> bool:
    ceil = AUD_CEILING.get(audience, 0)
    rank = SENS_RANK.get(str(record.get("sensitivity") or "internal"), 1)
    return rank <= ceil


def is_deliverable(
    record: dict[str, Any],
    *,
    today: date | None = None,
    audience: str = "owner",
) -> tuple[bool, str]:
    today = today or date.today()
    status = str(record.get("status") or "")
    if status in DEAD_STATUSES or status == "draft":
        return False, f"status={status}"
    start = record.get("valid_from")
    if start:
        try:
            if date.fromisoformat(str(start)[:10]) > today:
                return False, "not-yet-valid"
        except ValueError:
            return False, "bad valid_from"
    until = record.get("valid_until")
    if until:
        try:
            if date.fromisoformat(str(until)[:10]) < today:
                return False, "expired"
        except ValueError:
            return False, "bad valid_until"
    ok, reason = is_trusted(record)
    if not ok:
        return False, reason
    if not audience_ok(record, audience):
        return False, f"audience={audience} fail-closed"
    return True, ""


def _axis(rec: dict[str, Any]) -> str:
    retrieval = rec.get("retrieval") if isinstance(rec.get("retrieval"), dict) else {}
    hint = str((retrieval or {}).get("hint") or "")
    areas = " ".join(str(a) for a in (retrieval or {}).get("areas") or [])
    return " ".join(
        [
            str(rec.get("id") or ""),
            str(rec.get("claim") or ""),
            hint,
            areas,
            str(rec.get("memory_type") or ""),
        ]
    )


def _live_records(repo: Path, audience: str | None = None) -> list[dict[str, Any]]:
    aud = audience or settings(repo)["audience"]
    bot = str(settings(repo).get("personal_bot") or "")
    out = []
    for path in iter_record_paths(repo):
        rec = load_record(path)
        if isinstance(path, Path) and "bots" in path.parts:
            if not bot or not _is_bot_record(rec, bot):
                continue
        ok, _ = is_deliverable(rec, audience=aud)
        if ok:
            out.append(rec)
    return out


def probe_fts5() -> bool:
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()


def resolve_engine(repo: Path) -> str:
    pref = settings(repo)["search_engine"]
    if pref == "bm25":
        return "fallback-bm25"
    if pref == "fts5":
        return "fts5" if probe_fts5() else "unavailable"
    if probe_fts5():
        return "fts5"
    return "fallback-bm25"


def corpus_hash(repo: Path) -> str:
    digest = hashlib.sha256()
    for path in iter_record_paths(repo):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def index_stale(repo: Path) -> bool:
    marker = index_dir(repo) / "HASH"
    if not marker.is_file() or not sqlite_path(repo).is_file():
        return True
    return marker.read_text(encoding="utf-8").strip() != corpus_hash(repo)


def rebuild_sqlite(repo: Path) -> str:
    engine = resolve_engine(repo)
    folder = index_dir(repo)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / ".gitignore").write_text("*\n", encoding="utf-8")
    db = sqlite_path(repo)
    if db.is_file():
        db.unlink()
    conn = sqlite3.connect(str(db))
    try:
        if engine == "fts5":
            try:
                # ponytail: fts5 table+column cannot share the name "axis"
                conn.execute("CREATE VIRTUAL TABLE mem_axis USING fts5(rid, body)")
            except sqlite3.OperationalError:
                engine = "fallback-bm25"
                conn.execute("CREATE TABLE mem_axis (rid TEXT PRIMARY KEY, body TEXT)")
        else:
            conn.execute("CREATE TABLE mem_axis (rid TEXT PRIMARY KEY, body TEXT)")
        for rec in _live_records(repo, audience="owner"):
            tokens = " ".join(tokenize(_axis(rec)))
            conn.execute(
                "INSERT INTO mem_axis(rid, body) VALUES (?, ?)",
                (str(rec.get("id")), tokens),
            )
        conn.commit()
    finally:
        conn.close()
    (folder / "ENGINE").write_text(engine + "\n", encoding="utf-8")
    (folder / "HASH").write_text(corpus_hash(repo) + "\n", encoding="utf-8")
    return engine


def _ensure_index(repo: Path) -> tuple[str, str]:
    """Return (engine, degradation). Rebuilds a stale derived index in place."""
    if index_stale(repo):
        try:
            engine = rebuild_sqlite(repo)
            return engine, "rebuilt stale index"
        except Exception as exc:
            return "unavailable", f"stale index, rebuild failed: {exc}"
    engine = (index_dir(repo) / "ENGINE").read_text(encoding="utf-8").strip()
    return engine or "fallback-bm25", ""


def _facets(rec: dict[str, Any]) -> set[str]:
    retrieval = rec.get("retrieval") if isinstance(rec.get("retrieval"), dict) else {}
    areas = {str(a).lower() for a in (retrieval or {}).get("areas") or []}
    hint = set(tokenize(str((retrieval or {}).get("hint") or "")))
    paths = {p.lower() for p in _fp_paths(rec)}
    return set(tokenize(str(rec.get("id") or ""))) | areas | hint | paths


def _layer_exact(repo: Path, query: str, audience: str) -> list[dict[str, Any]]:
    q = set(tokenize(query))
    paths = {m.lower() for m in PATH_RE.findall(query or "")}
    hits = []
    for rec in _live_records(repo, audience):
        facets = _facets(rec)
        if q & set(tokenize(str(rec.get("id") or ""))):
            hits.append(rec)
        elif paths and (paths & facets or any(p in " ".join(facets) for p in paths)):
            hits.append(rec)
        elif q & {a.lower() for a in (
            (rec.get("retrieval") or {}).get("areas") or []
            if isinstance(rec.get("retrieval"), dict)
            else []
        )}:
            hits.append(rec)
    hits.sort(key=lambda rec: str(rec.get("id") or ""))
    return hits


def _layer_lexical(repo: Path, query: str, audience: str, engine: str) -> list[dict[str, Any]]:
    q_tokens = tokenize(query)
    if not q_tokens:
        return []
    by_id = {str(rec.get("id")): rec for rec in _live_records(repo, audience)}
    if engine == "fts5" and sqlite_path(repo).is_file():
        conn = sqlite3.connect(str(sqlite_path(repo)))
        try:
            match = " AND ".join(q_tokens)
            rows = conn.execute(
                "SELECT rid FROM mem_axis WHERE body MATCH ? ORDER BY rank",
                (match,),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        finally:
            conn.close()
        return [by_id[row[0]] for row in rows if row[0] in by_id]
    # BM25 on the same token stream
    docs = [(str(rec.get("id")), tokenize(_axis(rec)), rec) for rec in by_id.values()]
    n = len(docs) or 1
    avgdl = sum(len(toks) for _, toks, _ in docs) / n
    df: dict[str, int] = {}
    for _, toks, _ in docs:
        for tok in set(toks):
            df[tok] = df.get(tok, 0) + 1
    scored: list[tuple[float, dict[str, Any]]] = []
    k1, b = 1.5, 0.75
    for _rid, toks, rec in docs:
        score = 0.0
        tl = len(toks) or 1
        tf: dict[str, int] = {}
        for tok in toks:
            tf[tok] = tf.get(tok, 0) + 1
        for tok in q_tokens:
            if tok not in tf:
                continue
            idf = math.log(1 + (n - df.get(tok, 0) + 0.5) / (df.get(tok, 0) + 0.5))
            score += idf * (tf[tok] * (k1 + 1)) / (
                tf[tok] + k1 * (1 - b + b * tl / avgdl)
            )
        if score:
            scored.append((score, rec))
    scored.sort(key=lambda item: (-item[0], str(item[1].get("id"))))
    return [rec for _, rec in scored]


def _rec_date(rec: dict[str, Any]) -> str:
    for key in ("valid_from",):
        raw = rec.get(key)
        if raw:
            return str(raw)[:10]
    path = rec.get("_path")
    if isinstance(path, Path) and path.is_file():
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%d"
        )
    return "1970-01-01"


def _layer_facet(repo: Path, audience: str) -> list[dict[str, Any]]:
    recs = list(_live_records(repo, audience))
    risk_rank = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda rec: str(rec.get("id") or ""))
    recs.sort(key=lambda rec: _rec_date(rec), reverse=True)
    recs.sort(key=lambda rec: risk_rank.get(str(rec.get("risk") or "low"), 2))
    return recs


def rrf_merge(layers: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    store: dict[str, dict[str, Any]] = {}
    for layer in layers:
        for rank, rec in enumerate(layer, 1):
            rid = str(rec.get("id"))
            scores[rid] = scores.get(rid, 0.0) + 1.0 / (RRF_K + rank)
            store[rid] = rec
    ordered = sorted(scores, key=lambda rid: (-scores[rid], rid))
    # Diversify: at most 3 from the same first area in a row of 8
    out: list[dict[str, Any]] = []
    area_count: dict[str, int] = {}
    for rid in ordered:
        rec = store[rid]
        retrieval = rec.get("retrieval") if isinstance(rec.get("retrieval"), dict) else {}
        areas = list((retrieval or {}).get("areas") or ["untagged"])
        area = str(areas[0])
        if area_count.get(area, 0) >= 3 and len(out) < 8:
            continue
        area_count[area] = area_count.get(area, 0) + 1
        out.append(rec)
    return out


def search(
    repo: Path,
    query: str,
    *,
    limit: int = 8,
    audience: str | None = None,
    mode: str = "hybrid",
) -> tuple[list[dict[str, Any]], str]:
    mode = (mode or "hybrid").strip().lower()
    aud = audience or settings(repo)["audience"]
    if mode == "subagent":
        aud = "subagent"
    engine, degrade = _ensure_index(repo)
    exact = _layer_exact(repo, query, aud)

    def _strip(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [rec for rec in rows if rec.get("context_priority") != "always"][:limit]

    # Drawing §4.4: three paths stay off hybrid (speed > recall).
    if mode == "reflex":
        return _strip(exact), "reflex: exact only, no hybrid"
    if mode == "preaction":
        return _strip(exact), "preaction: exact only before tool, no hybrid"
    if mode == "subagent":
        facet = _layer_facet(repo, aud)
        seen: set[str] = set()
        rows = []
        for rec in exact + facet:
            rid = str(rec.get("id"))
            if rid in seen:
                continue
            seen.add(rid)
            rows.append(rec)
        return _strip(rows), "subagent pack: exact+facet, no hybrid"
    if engine == "unavailable":
        degrade = degrade or "search engine unavailable"
        return _strip(exact), degrade
    lexical = _layer_lexical(repo, query, aud, engine)
    facet = _layer_facet(repo, aud)
    merged = rrf_merge([exact, lexical, facet])
    contest = [rec for rec in merged if rec.get("context_priority") != "always"]
    return contest[:limit], degrade


def load_tags(repo: Path, tags: list[str], audience: str | None = None) -> list[dict[str, Any]]:
    """Between facets AND; inside one facet OR (canonical + aliases)."""
    aud = audience or settings(repo)["audience"]
    catalog = tag_catalog(repo)
    facets: list[set[str]] = []
    for raw in tags:
        token = raw.strip()
        if not token:
            continue
        canon = resolve_tag(repo, token)
        names = set(catalog.get(canon) or {canon})
        names.add(canon)
        facets.append({n.lower() for n in names})
    hits = []
    for rec in _live_records(repo, aud):
        retrieval = rec.get("retrieval") if isinstance(rec.get("retrieval"), dict) else {}
        areas = {str(a).lower() for a in (retrieval or {}).get("areas") or []}
        if facets and not all(facet & areas for facet in facets):
            continue
        hits.append(rec)
    return hits


def context_pack(
    repo: Path,
    query: str,
    *,
    budget: int | None = None,
    audience: str | None = None,
) -> str:
    cfg = settings(repo)
    budget = budget or int(cfg["context_budget"])
    aud = audience or cfg["audience"]
    core = core_text(repo)
    hits, degrade = search(repo, query, audience=aud)
    parts = [core, "", f"# Catalog ({query})", ""]
    if degrade:
        parts.append(f"_degraded: {degrade}_")
        parts.append("")
    used = len("\n".join(parts).encode("utf-8"))
    cards: list[dict[str, Any]] = []
    for rec in hits:
        card = f"- [[{rec.get('id')}]] {rec.get('claim')}"
        extra = used + len(card.encode("utf-8")) + 1
        if extra > budget:
            parts.append(f"_budget {budget} reached — trim or lower priority_")
            break
        parts.append(card)
        cards.append(rec)
        used = extra
    parts.extend(["", "# Fragments", ""])
    used = len("\n".join(parts).encode("utf-8"))
    pointed: list[dict[str, Any]] = []
    for rec in cards:
        body = str(rec.get("_body") or "").strip()
        frag = " ".join(body.split())[:400]
        block = f"## [[{rec.get('id')}]]\n{frag}\n"
        extra = used + len(block.encode("utf-8"))
        if extra > budget:
            pointed.append(rec)
            continue
        parts.append(block)
        used = extra
    if pointed:
        parts.extend(["", "# Pointers", ""])
        for rec in pointed:
            path = rec.get("_path")
            parts.append(f"- [[{rec.get('id')}]] {path}")
    parts.extend(["", f"# Manifest  audience={aud}  used={used}/{budget}"])
    return "\n".join(parts).rstrip() + "\n"


def _is_bot_record(rec: dict[str, Any], bot: str) -> bool:
    path = rec.get("_path")
    if not isinstance(path, Path):
        return False
    parts = path.parts
    return "bots" in parts and bot in parts


def core_records(repo: Path) -> list[dict[str, Any]]:
    bot = str(settings(repo).get("personal_bot") or "")
    out = []
    for rec in _live_records(repo):
        if rec.get("context_priority") != "always":
            continue
        path = rec.get("_path")
        under_bots = isinstance(path, Path) and "bots" in path.parts
        if under_bots and (not bot or not _is_bot_record(rec, bot)):
            continue
        out.append(rec)
    return out


def core_text(repo: Path) -> str:
    cfg = settings(repo)
    bot = str(cfg.get("personal_bot") or "")
    shared = []
    personal = []
    for rec in core_records(repo):
        if bot and _is_bot_record(rec, bot):
            personal.append(rec)
        else:
            shared.append(rec)
    lines = ["# Memory CORE (always)", "", "## shared", ""]
    if not shared:
        lines.append("_no always-on shared facts_")
    for rec in shared:
        claim = re.sub(r"<!--", "< !--", str(rec.get("claim") or ""))
        lines.append(f"- {rec.get('id')}: {claim}")
    if bot:
        lines.extend(["", f"## personal/{bot}", ""])
        if not personal:
            lines.append("_no personal always-on facts_")
        for rec in personal:
            claim = re.sub(r"<!--", "< !--", str(rec.get("claim") or ""))
            lines.append(f"- {rec.get('id')}: {claim}")
    text = "\n".join(lines) + "\n"
    used = len(text.encode("utf-8"))
    header = f"# Memory CORE (always)  {used}/{cfg['core_budget']} bytes\n"
    return header + "\n".join(lines[1:]) + "\n"


def last_episode(repo: Path) -> Path | None:
    folder = corpus_dir(repo) / "episodes"
    if not folder.is_dir():
        return None
    files = sorted(folder.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def inject_core(repo: Path) -> list[Path]:
    if not enabled(repo) or not settings(repo)["inject"]:
        return []
    block = f"{CORE_MARK_START}\n{core_text(repo).rstrip()}\n{CORE_MARK_END}\n"
    touched: list[Path] = []
    for name in ("CLAUDE.md", "AGENTS.md"):
        path = Path(repo) / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if CORE_MARK_START in text and CORE_MARK_END in text:
            text = re.sub(
                re.escape(CORE_MARK_START) + r".*?" + re.escape(CORE_MARK_END),
                block.strip(),
                text,
                count=1,
                flags=re.S,
            )
        else:
            text = text.rstrip() + "\n\n" + block
        path.write_text(text, encoding="utf-8")
        touched.append(path)
    return touched


def expected_memory_md(repo: Path) -> str:
    lines = [
        "<!-- generated by lane-memory; do not edit -->",
        "",
        "# MEMORY",
        "",
        "## Core (always loaded)",
        "",
    ]
    by_area: dict[str, list[str]] = {}
    core_rows = []
    for rec in _live_records(repo, audience="owner"):
        rid = rec.get("id")
        claim = rec.get("claim")
        row = f"- [[{rid}]] — {claim} · {rec.get('memory_type')} · {rec.get('truth_mode')}"
        if rec.get("context_priority") == "always":
            core_rows.append(row)
        retrieval = rec.get("retrieval") if isinstance(rec.get("retrieval"), dict) else {}
        areas = list((retrieval or {}).get("areas") or ["untagged"])
        for area in areas:
            by_area.setdefault(str(area), []).append(row)
    lines.extend(core_rows or ["_empty_"])
    lines.extend(["", "## Areas", ""])
    for area, rows in sorted(by_area.items()):
        lines.append(f"- [{area}](INDEX-{area}.md) — {len(rows)}")
    return "\n".join(lines) + "\n"


def expected_area_index(repo: Path, area: str, rows: list[str]) -> str:
    return (
        "<!-- generated by lane-memory; do not edit -->\n\n"
        + f"# {area}\n\n"
        + "\n".join(rows)
        + "\n"
    )


def rebuild_index(repo: Path) -> str:
    root = corpus_dir(repo)
    root.mkdir(parents=True, exist_ok=True)
    text = expected_memory_md(repo)
    memory_index_path(repo).write_text(text, encoding="utf-8")
    by_area: dict[str, list[str]] = {}
    for rec in _live_records(repo, audience="owner"):
        row = (
            f"- [[{rec.get('id')}]] — {rec.get('claim')} · "
            f"{rec.get('memory_type')} · {rec.get('truth_mode')}"
        )
        retrieval = rec.get("retrieval") if isinstance(rec.get("retrieval"), dict) else {}
        areas = list((retrieval or {}).get("areas") or ["untagged"])
        for area in areas:
            by_area.setdefault(str(area), []).append(row)
    written: set[Path] = set()
    for area, rows in by_area.items():
        dest = root / f"INDEX-{area}.md"
        dest.write_text(
            expected_area_index(repo, area, rows),
            encoding="utf-8",
        )
        written.add(dest)
    for stale in root.glob("INDEX-*.md"):
        if stale not in written:
            stale.unlink()
    rebuild_sqlite(repo)
    return text


def fingerprint(repo: Path, paths: list[str]) -> str:
    digest = hashlib.sha256()
    for rel in sorted(paths):
        path = Path(repo) / rel
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def _fp_paths(rec: dict[str, Any]) -> list[str]:
    raw = rec.get("fingerprint")
    if isinstance(raw, dict):
        return [str(p) for p in raw.get("paths") or []]
    return []


def lint(repo: Path) -> list[str]:
    cfg = settings(repo)
    findings: list[str] = []
    tags = allowed_tags(repo)
    seen_claims: dict[str, str] = {}
    records = [load_record(p) for p in iter_record_paths(repo)]
    ids = {str(r.get("id") or "") for r in records}
    active_claims: list[tuple[str, set[str], str]] = []
    for rec in records:
        path = rec["_path"]
        rid = str(rec.get("id") or "")
        if rid != path.stem:
            findings.append(f"IDLAW {path.name}: id must equal filename")
        for key in REQUIRED:
            if rec.get(key) in (None, ""):
                findings.append(f"V2SCHEMA {path.name}: missing {key}")
        if rec.get("memory_type") not in MEMORY_TYPES:
            findings.append(f"V2SCHEMA {path.name}: bad memory_type")
        if rec.get("truth_mode") not in TRUTH_MODES:
            findings.append(f"V2SCHEMA {path.name}: bad truth_mode")
        if rec.get("status") not in STATUSES:
            findings.append(f"V2SCHEMA {path.name}: bad status")
        if rec.get("sensitivity") not in SENSITIVITIES:
            findings.append(f"V2SCHEMA {path.name}: bad sensitivity")
        if rec.get("language") not in LANGUAGES:
            findings.append(f"V2SCHEMA {path.name}: language must be en|ru")
        if str(rec.get("schema_version")) != "2":
            findings.append(f"V2SCHEMA {path.name}: schema_version must be 2")
        if rec.get("status") == "draft" and path.parent.name != "drafts":
            findings.append(f"DRAFTPLACE {path.name}: draft must live in drafts/")
        if rec.get("written_via") != "lane-memory":
            findings.append(f"OFFPIPELINE {path.name}: missing written_via=lane-memory")
        claim = str(rec.get("claim") or "").strip()
        if claim.count(". ") >= 1 or "\n" in claim:
            findings.append(f"ONECLAIM {path.name}: claim must be one statement")
        norm = re.sub(r"\s+", " ", claim.lower())
        if rec.get("status") == "active":
            if norm in seen_claims:
                findings.append(f"DUPE {path.name}: same claim as {seen_claims[norm]}")
            seen_claims[norm] = path.name
            active_claims.append((rid, set(tokenize(claim)), claim))
        body_hash = hashlib.sha256(
            re.sub(r"\s+", " ", str(rec.get("_body") or "")).strip().encode()
        ).hexdigest()[:16]
        rec["_body_hash"] = body_hash
        retrieval = rec.get("retrieval") if isinstance(rec.get("retrieval"), dict) else {}
        areas = list((retrieval or {}).get("areas") or [])
        for area in areas:
            if tags and str(area) not in tags:
                findings.append(f"VOCAB {path.name}: tag {area!r} not in TAGS.md")
        if SECRET_RE.search(rec.get("_text") or ""):
            findings.append(f"SECRET {path.name}: secret-like string")
        if rec.get("sensitivity") in {"sensitive", "encrypted-required"}:
            placed = str(path)
            if not any(
                mark in placed
                for mark in (".cls/local-memory", "sma/local-memory", "memory.local")
            ):
                findings.append(f"SENSPLACE {path.name}: sensitive file in git corpus")
        authority = ""
        source = rec.get("source")
        if isinstance(source, dict):
            authority = str(source.get("authority") or "")
        if rec.get("memory_type") in {"decision", "normative"} and not authority:
            findings.append(f"AUTHORITY {path.name}: decision/normative needs source.authority")
        if rec.get("truth_mode") == "observed" and not rec.get("evidence"):
            findings.append(f"EVIDENCE {path.name}: observed claim needs evidence[]")
        if rec.get("context_priority") == "always":
            cmd = (
                (rec.get("verification") or {}).get("command")
                if isinstance(rec.get("verification"), dict)
                else None
            )
            if not cmd:
                findings.append(f"VERIFY {path.name}: CORE fact needs verification.command")
        if CORE_MARK_START in str(rec.get("_body") or ""):
            findings.append(f"COREMARK {path.name}: record body contains CORE markers")
        start = rec.get("valid_from")
        if start and rec.get("status") == "active":
            try:
                if date.fromisoformat(str(start)[:10]) > date.today():
                    findings.append(f"VALIDFROM {path.name}: not yet valid")
            except ValueError:
                pass
        if RELATIVE_DATE_RE.search(claim) or RELATIVE_DATE_RE.search(rec.get("_body") or ""):
            findings.append(f"RELATIVE {path.name}: relative date")
        ok, reason = is_trusted(rec)
        if not ok:
            findings.append(f"INJECT {path.name}: {reason}")
        for match in re.findall(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]", rec.get("_body") or ""):
            if match.strip() not in ids:
                findings.append(f"WIKILINK {path.name}: [[{match.strip()}]] missing")
        links = rec.get("links") or []
        if isinstance(links, list):
            for link in links:
                if not isinstance(link, dict):
                    continue
                if link.get("type") not in LINK_TYPES:
                    findings.append(f"V2SCHEMA {path.name}: bad link type")
                target = str(link.get("id") or "")
                if target and target not in ids:
                    findings.append(f"WIKILINK {path.name}: link {target} missing")
                if link.get("type") == "contradicts" and rec.get("status") == "active":
                    findings.append(f"CONTRADICT {path.name}: explicit contradicts {target}")
        if rec.get("supersedes") and rec.get("status") == "active":
            other = next((r for r in records if r.get("id") == rec.get("supersedes")), None)
            if other and other.get("superseded_by") != rid:
                findings.append(f"SUPERSEDE {path.name}: pair not atomic")
            seen_chain = {rid}
            cursor = rec.get("supersedes")
            while cursor:
                if cursor in seen_chain:
                    findings.append(f"SUPERSEDE {path.name}: loop")
                    break
                seen_chain.add(cursor)
                nxt = next((r for r in records if r.get("id") == cursor), None)
                cursor = nxt.get("supersedes") if nxt else None
        start = rec.get("valid_from")
        if start:
            try:
                date.fromisoformat(str(start)[:10])
            except ValueError:
                findings.append(f"V2SCHEMA {path.name}: bad valid_from")
        until = rec.get("valid_until")
        if until and rec.get("status") == "active":
            try:
                if date.fromisoformat(str(until)[:10]) < date.today():
                    findings.append(f"EXPIRE {path.name}: valid_until in the past")
            except ValueError:
                findings.append(f"V2SCHEMA {path.name}: bad valid_until")
        size = len((rec.get("_text") or "").encode("utf-8"))
        if size > int(cfg["note_budget"]):
            findings.append(f"NOTESIZE {path.name}: {size} > {cfg['note_budget']}")
        paths = _fp_paths(rec)
        stored = ""
        if isinstance(rec.get("fingerprint"), dict):
            stored = str(rec["fingerprint"].get("hash") or "")
        if paths and stored and fingerprint(repo, paths) != stored:
            findings.append(f"FPDRIFT {path.name}: world moved; re-run verification.command")
    # CONTRADICT heuristic
    for i, (aid, atok, _ac) in enumerate(active_claims):
        for bid, btok, _bc in active_claims[i + 1 :]:
            inter = atok & btok
            if len(inter) >= 3 and (atok & NEGATION) != (btok & NEGATION):
                findings.append(f"CONTRADICT {aid} vs {bid}: token clash")
    # TAGCHAOS
    used: dict[str, int] = {}
    for rec in records:
        retrieval = rec.get("retrieval") if isinstance(rec.get("retrieval"), dict) else {}
        for area in (retrieval or {}).get("areas") or []:
            used[str(area)] = used.get(str(area), 0) + 1
    for tag, count in used.items():
        if count == 1:
            findings.append(f"TAGCHAOS {tag}: used once")
        for other in used:
            if other != tag and other.startswith(tag):
                findings.append(f"TAGCHAOS near-duplicate {tag}~{other}")
    nrec = len(records) or 1
    for tag, count in used.items():
        if count >= 5 and count / nrec >= 0.5:
            findings.append(f"TAGWIDE {tag}: covers {count}/{nrec} records")
    by_hash: dict[str, list[str]] = {}
    for rec in records:
        digest = str(rec.get("_body_hash") or "")
        if digest:
            by_hash.setdefault(digest, []).append(str(rec.get("id") or rec["_path"].name))
    for names in by_hash.values():
        if len(names) > 1:
            findings.append(f"HASHDUPE {' '.join(names)}: identical body")
    if index_stale(repo):
        findings.append("STALEIDX derived index hash != corpus")
    if memory_index_path(repo).is_file():
        if memory_index_path(repo).read_text(encoding="utf-8") != expected_memory_md(repo):
            findings.append("REGEN MEMORY.md: hand-edited; regenerate with lane-memory index")
        idx_size = memory_index_path(repo).stat().st_size
        if idx_size > int(cfg["index_budget"]):
            findings.append(f"INDEXSIZE MEMORY.md {idx_size} > {cfg['index_budget']}")
        mem_ids: set[str] = set()
        for line in memory_index_path(repo).read_text(encoding="utf-8").splitlines():
            for match in re.findall(r"\[\[([^\]]+)\]\]", line):
                mem_ids.add(match)
                if match not in ids:
                    findings.append(f"ORPHAN MEMORY.md points at [[{match}]]")
        for rid in {str(r.get("id") or "") for r in _live_records(repo, "owner")}:
            if rid and rid not in mem_ids:
                findings.append(f"ORPHAN {rid}: file not in MEMORY.md")
    by_area: dict[str, list[str]] = {}
    for rec in _live_records(repo, audience="owner"):
        row = (
            f"- [[{rec.get('id')}]] — {rec.get('claim')} · "
            f"{rec.get('memory_type')} · {rec.get('truth_mode')}"
        )
        retrieval = rec.get("retrieval") if isinstance(rec.get("retrieval"), dict) else {}
        for area in list((retrieval or {}).get("areas") or ["untagged"]):
            by_area.setdefault(str(area), []).append(row)
    for area, rows in by_area.items():
        idx = corpus_dir(repo) / f"INDEX-{area}.md"
        if idx.is_file() and idx.read_text(encoding="utf-8") != expected_area_index(
            repo, area, rows
        ):
            findings.append(f"REGEN INDEX-{area}.md: hand-edited; regenerate with lane-memory index")
    core_bytes = len(core_text(repo).encode("utf-8"))
    if core_bytes > int(cfg["core_budget"]):
        findings.append(
            f"CORESIZE core is {core_bytes} bytes > {cfg['core_budget']}; trim or demote"
        )
    return findings


def redact_or_raise(text: str) -> None:
    if SECRET_RE.search(text):
        raise ValueError("SECRET: refuse write, including drafts")


def _twins(repo: Path, claim: str, skip_id: str) -> list[str]:
    norm = re.sub(r"\s+", " ", claim.strip().lower())
    q = set(tokenize(claim))
    out = []
    for rec in [load_record(p) for p in iter_record_paths(repo)]:
        if rec.get("id") == skip_id:
            continue
        other = re.sub(r"\s+", " ", str(rec.get("claim") or "").strip().lower())
        if other == norm:
            out.append(f"DUPE {rec.get('id')}")
        elif rec.get("status") == "active" and len(q & set(tokenize(other))) >= 3:
            out.append(f"neighbor {rec.get('id')}")
    return out


def write_apply(
    repo: Path,
    draft: Path,
    *,
    yes: bool,
    confirm: Path | None = None,
    observe: str = "",
) -> tuple[Path, list[str]]:
    """12-step door. Returns (dest, log)."""
    if not yes:
        raise ValueError("write requires --yes")
    log: list[str] = []
    raw = Path(draft).read_text(encoding="utf-8")
    bits = [f"draft={draft}"]
    if observe:
        bits.append(observe)
    try:
        git = subprocess.run(
            ["git", "status", "-sb"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        bits.append("git=" + (git.stdout or git.stderr)[:400].replace("\n", " "))
    except (OSError, subprocess.TimeoutExpired):
        bits.append("git=unavailable")
    episode = last_episode(repo)
    if episode:
        bits.append(f"episode={episode.name}")
    log.append("1 observe: " + " | ".join(bits))
    redact_or_raise(raw)
    log.append("3 redact: no secret")
    text = convert_relative_dates(raw)
    if text != raw:
        log.append("1b dates: relative → ISO")
    meta, body = _split_fm(text)
    log.append("2 classify: author fields required")
    for key in REQUIRED:
        if meta.get(key) in (None, ""):
            raise ValueError(f"missing {key} (machine does not classify)")
    if meta.get("memory_type") not in MEMORY_TYPES or meta.get("truth_mode") not in TRUTH_MODES:
        raise ValueError("classify: memory_type/truth_mode outside closed vocab")
    claim = str(meta["claim"]).strip()
    if claim.count(". ") >= 1 or "\n" in claim:
        raise ValueError("4 extract: claim must be one statement")
    log.append("4 extract: one claim")
    rid = str(meta["id"])
    twins = _twins(repo, claim, rid)
    if any(t.startswith("DUPE") for t in twins):
        raise ValueError(f"5 compare: {twins[0]} — update, do not spawn")
    log.append("5 compare: " + (", ".join(twins) if twins else "no twins"))
    if meta.get("truth_mode") == "observed" and not meta.get("evidence"):
        raise ValueError("6 evidence: observed claim needs evidence[]")
    log.append("6 evidence: ok")
    if "risk" not in meta or not meta.get("risk"):
        if meta.get("sensitivity") in {"sensitive", "encrypted-required"}:
            meta["risk"] = "high"
        elif not (isinstance(meta.get("verification"), dict) and meta["verification"].get("command")):
            meta["risk"] = "medium"
        else:
            meta["risk"] = "low"
    log.append(f"7 risk: {meta['risk']}")
    dest_root = (
        local_dir(repo)
        if meta.get("sensitivity") in {"sensitive", "encrypted-required"}
        else corpus_dir(repo)
    )
    bot_name = str(meta.get("bot") or "").strip()
    if bot_name:
        dest_root = corpus_dir(repo) / "bots" / bot_name
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / f"{rid}.md"
    if confirm is None:
        raise ValueError(f"write requires --confirm {dest}")
    if Path(confirm).resolve() != dest.resolve():
        raise ValueError(f"confirm path must be {dest}")
    paths = _fp_paths(meta)
    meta["written_via"] = "lane-memory"
    if paths:
        fp = meta.get("fingerprint")
        if not isinstance(fp, dict):
            fp = {"paths": paths}
        fp["hash"] = fingerprint(repo, paths)
        fp.setdefault("product", "lane-memory")
        meta["fingerprint"] = fp
    dest.write_text(_dump_record(meta, body), encoding="utf-8")
    log.append(f"8 persist: {dest}")
    old_id = meta.get("supersedes")
    if old_id:
        old_path = corpus_dir(repo) / f"{old_id}.md"
        if not old_path.is_file():
            old_path = local_dir(repo) / f"{old_id}.md"
        if old_path.is_file():
            old = load_record(old_path)
            body_old = old.pop("_body", "")
            old.pop("_path", None)
            old.pop("_text", None)
            old["status"] = "superseded"
            old["superseded_by"] = rid
            old_path.write_text(_dump_record(old, body_old), encoding="utf-8")
        log.append(f"12 lifecycle: superseded {old_id}")
    rebuild_index(repo)
    log.append("9 index: MEMORY.md + sqlite rebuilt")
    injected = inject_core(repo)
    if injected:
        log.append("9b inject: " + ", ".join(str(p) for p in injected))
    log.append(
        f"10 measure: records={len(list(iter_record_paths(repo)))} "
        f"core_bytes={len(core_text(repo).encode())}"
    )
    leftover = [t for t in twins if t.startswith("neighbor")]
    log.append(
        "11 consolidate: "
        + (", ".join(leftover) if leftover else "no merge proposals")
        + " (report only)"
    )
    return dest, log


def _erase_traces(repo: Path, rec_id: str) -> list[str]:
    traces: list[str] = []
    needle = rec_id
    surfaces = [
        memory_index_path(repo),
        sqlite_path(repo),
        Path(repo) / "CLAUDE.md",
        Path(repo) / "AGENTS.md",
    ]
    surfaces.extend(sorted(corpus_dir(repo).glob("INDEX-*.md")))
    for path in surfaces:
        if not path.is_file():
            continue
        try:
            blob = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            blob = ""
        if needle in blob or needle in path.name:
            traces.append(str(path))
    if needle in core_text(repo):
        traces.append("CORE")
    leftover = corpus_dir(repo) / f"{rec_id}.md"
    if leftover.is_file():
        traces.append(str(leftover))
    leftover_local = local_dir(repo) / f"{rec_id}.md"
    if leftover_local.is_file():
        traces.append(str(leftover_local))
    return traces


def forget(repo: Path, rec_id: str, *, mode: str, yes: bool) -> Path:
    path = corpus_dir(repo) / f"{rec_id}.md"
    if not path.is_file():
        path = local_dir(repo) / f"{rec_id}.md"
    if not path.is_file():
        raise ValueError(f"missing {rec_id}")
    if mode == "erase":
        if not yes:
            raise ValueError("erase requires --yes")
        path.unlink()
        rebuild_index(repo)
        inject_core(repo)
        leftover = _erase_traces(repo, rec_id)
        if leftover:
            raise ValueError(f"erase leftover: {', '.join(leftover)}")
        return path
    rec = load_record(path)
    body = rec.pop("_body", "")
    rec.pop("_path", None)
    rec.pop("_text", None)
    rec["status"] = {"expire": "expired", "archive": "archived"}[mode]
    path.write_text(_dump_record(rec, body), encoding="utf-8")
    rebuild_index(repo)
    inject_core(repo)
    return path


def trim(repo: Path, rec_id: str) -> Path:
    path = corpus_dir(repo) / f"{rec_id}.md"
    rec = load_record(path)
    body = rec.pop("_body", "")
    rec.pop("_path", None)
    rec.pop("_text", None)
    rec["context_priority"] = "on-demand"
    path.write_text(_dump_record(rec, body), encoding="utf-8")
    rebuild_index(repo)
    inject_core(repo)
    return path


def compress(repo: Path, rec_id: str) -> Path:
    path = corpus_dir(repo) / f"{rec_id}.md"
    rec = load_record(path)
    body = rec.get("_body") or ""
    short = " ".join(body.split())[:400]
    dest = corpus_dir(repo) / "drafts" / f"{rec_id}-compressed.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    rec.pop("_path", None)
    rec.pop("_text", None)
    rec.pop("_body", None)
    dest.write_text(_dump_record(rec, short), encoding="utf-8")
    return dest


def neighbors(repo: Path, rec_id: str) -> list[str]:
    rec = load_record(corpus_dir(repo) / f"{rec_id}.md")
    lines = []
    for link in rec.get("links") or []:
        if isinstance(link, dict):
            lines.append(f"{link.get('type')} -> {link.get('id')}")
    for other in [load_record(p) for p in iter_record_paths(repo)]:
        for link in other.get("links") or []:
            if isinstance(link, dict) and link.get("id") == rec_id:
                lines.append(f"{other.get('id')} {link.get('type')} -> {rec_id}")
    return lines


def history_search(repo: Path, words: str) -> list[str]:
    q = set(tokenize(words))
    hits = []
    roots = [
        corpus_dir(repo) / "episodes",
        Path(repo) / ".agents" / "session-log",
    ]
    extras = [Path(repo) / ".agents" / "LESSONS.md"]
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            if path.name.startswith("INDEX"):
                continue
            text = path.read_text(encoding="utf-8")
            if q & set(tokenize(text)):
                hits.append(str(path))
    for path in extras:
        if path.is_file() and q & set(tokenize(path.read_text(encoding="utf-8"))):
            hits.append(str(path))
    for rec in [load_record(p) for p in iter_record_paths(repo)]:
        if rec.get("memory_type") != "episodic":
            continue
        if q & set(tokenize(rec.get("_body") or "")):
            hits.append(str(rec["_path"]))
    return hits


def write_episode(repo: Path, text: str, *, title: str = "") -> Path:
    folder = corpus_dir(repo) / "episodes"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = folder / f"{stamp}.md"
    head = title.strip() or "session"
    path.write_text(
        f"# Episode {stamp}\n\n{head}\n\n{text.rstrip()}\n",
        encoding="utf-8",
    )
    return path


def explain(repo: Path, task: str) -> list[str]:
    aud = settings(repo)["audience"]
    q = set(tokenize(task))
    hits, degrade = search(repo, task, audience=aud)
    delivered = {str(r.get("id")) for r in hits}
    delivered |= {str(r.get("id")) for r in core_records(repo)}
    lines = []
    if degrade:
        lines.append(f"degraded: {degrade}")
    for path in iter_record_paths(repo):
        rec = load_record(path)
        ok, reason = is_deliverable(rec, audience=aud)
        rid = rec.get("id")
        if not ok:
            lines.append(f"reject [[{rid}]] — {reason}")
        elif rec.get("context_priority") == "always":
            lines.append(f"deliver [[{rid}]] — CORE (not ranked)")
        elif rid in delivered:
            lines.append(f"deliver [[{rid}]] — RRF lexical/exact/facet")
        elif q & set(tokenize(_axis(rec))):
            lines.append(f"reject [[{rid}]] — overlap but lost RRF/budget")
        else:
            lines.append(f"reject [[{rid}]] — no token overlap")
    return lines


def verify_record(repo: Path, rec_id: str) -> tuple[str, int]:
    path = corpus_dir(repo) / f"{rec_id}.md"
    if not path.is_file():
        path = local_dir(repo) / f"{rec_id}.md"
    if not path.is_file():
        return "NOT_RUN missing", 2
    rec = load_record(path)
    cmd = (
        (rec.get("verification") or {}).get("command")
        if isinstance(rec.get("verification"), dict)
        else None
    )
    if not cmd:
        return "NOT_RUN no-command", 3
    proc = subprocess.run(cmd, shell=True, cwd=repo, capture_output=True, text=True, check=False)
    if proc.returncode == 0:
        return "ok", 0
    return "blockers", proc.returncode


def measure(repo: Path) -> dict[str, Any]:
    golden = corpus_dir(repo) / "GOLDEN.yaml"
    if not golden.is_file():
        return {"error": "no GOLDEN.yaml"}
    cases = yaml.safe_load(golden.read_text(encoding="utf-8")) or []
    recall_hits = 0
    prec_num = 0
    prec_den = 0
    mrr = 0.0
    ndcg_sum = 0.0
    superseded_bad = 0
    critical_miss = 0
    n = 0
    for case in cases:
        n += 1
        query = str(case.get("query") or "")
        must = [str(x) for x in case.get("must") or []]
        hits, _ = search(repo, query)
        ids = [str(h.get("id")) for h in hits[:3]]
        if must and any(m in ids for m in must):
            recall_hits += 1
        prec_den += 3
        prec_num += sum(1 for i in ids if i in must)
        rels = [1.0 if hid in must else 0.0 for hid in ids]
        dcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(rels))
        ideal = sorted(rels, reverse=True)
        idcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal))
        ndcg_sum += (dcg / idcg) if idcg else 0.0
        for rank, hid in enumerate(ids, 1):
            if hid in must:
                mrr += 1 / rank
                break
        for hid in ids:
            path = corpus_dir(repo) / f"{hid}.md"
            if path.is_file() and load_record(path).get("status") == "superseded":
                superseded_bad += 1
        if case.get("critical") and must and not any(m in ids for m in must):
            critical_miss += 1
    return {
        "n": n,
        "recall@3": recall_hits / n if n else 0,
        "precision@3": prec_num / prec_den if prec_den else 0,
        "mrr": mrr / n if n else 0,
        "ndcg@3": ndcg_sum / n if n else 0,
        "critical_miss": critical_miss,
        "superseded_leaks": superseded_bad,
    }


def init_corpus(repo: Path) -> Path:
    root = corpus_dir(repo)
    (root / "drafts").mkdir(parents=True, exist_ok=True)
    (root / "episodes").mkdir(parents=True, exist_ok=True)
    (root / "bots").mkdir(parents=True, exist_ok=True)
    cls = cls_dir(repo)
    (cls / "local-memory").mkdir(parents=True, exist_ok=True)
    (cls / "index").mkdir(parents=True, exist_ok=True)
    (cls / "local-memory" / ".gitignore").write_text("*\n", encoding="utf-8")
    (cls / "index" / ".gitignore").write_text("*\n", encoding="utf-8")
    (cls / ".gitignore").write_text("local-memory/\nindex/\n", encoding="utf-8")
    local = local_dir(repo)
    local.mkdir(parents=True, exist_ok=True)
    if not (local / ".gitignore").is_file():
        (local / ".gitignore").write_text("*\n", encoding="utf-8")
    if not tags_path(repo).is_file():
        tags_path(repo).write_text(
            "# Allowed retrieval.areas (indent = alias)\n\n"
            "- decisions\n- lessons\n- preferences\n"
            "- procedures\n  - howto\n"
            "- product\n- reports\n  - отчёт\n  - сводка\n",
            encoding="utf-8",
        )
    golden = root / "GOLDEN.yaml"
    if not golden.is_file():
        golden.write_text("# query -> must-hit ids\n[]\n", encoding="utf-8")
    template = root / "drafts" / "_TEMPLATE.md"
    if not template.is_file():
        template.write_text(DRAFT_TEMPLATE, encoding="utf-8")
    rebuild_index(repo)
    inject_core(repo)
    return root


def _record_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pending_worktree_ids(main: Path, worktree: Path) -> list[str]:
    if not corpus_dir(worktree).is_dir():
        return []
    main_map = {
        str(load_record(p).get("id")): _record_bytes(p) for p in iter_record_paths(main)
    }
    pending = []
    for path in iter_record_paths(worktree):
        rec = load_record(path)
        rid = str(rec.get("id") or "")
        if main_map.get(rid) != _record_bytes(path):
            pending.append(rid)
    return pending


def export_worktree(main: Path, worktree: Path) -> list[Path]:
    copied: list[Path] = []
    main_map = {
        str(load_record(p).get("id")): _record_bytes(p) for p in iter_record_paths(main)
    }
    for path in iter_record_paths(worktree):
        rec = load_record(path)
        rid = str(rec.get("id") or "")
        if main_map.get(rid) == _record_bytes(path):
            continue
        dest_root = (
            local_dir(main)
            if rec.get("sensitivity") in {"sensitive", "encrypted-required"}
            else corpus_dir(main)
        )
        bot_name = str(rec.get("bot") or "").strip()
        if bot_name:
            dest_root = corpus_dir(main) / "bots" / bot_name
        dest = dest_root / f"{rid}.md"
        draft = corpus_dir(main) / "drafts" / f"{rid}.md"
        draft.parent.mkdir(parents=True, exist_ok=True)
        draft.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        out, _log = write_apply(
            main,
            draft,
            yes=True,
            confirm=dest,
            observe=f"export-worktree {worktree}",
        )
        copied.append(out)
    leftover = pending_worktree_ids(main, worktree)
    if leftover:
        raise ValueError(f"worktree memory not exported: {', '.join(leftover)}")
    return copied
