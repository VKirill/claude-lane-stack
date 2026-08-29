#!/usr/bin/env python3
"""EN/RU strings for agents-doctor TUI. Keys only — no logic."""
from __future__ import annotations

from typing import Any

LANGS = ("en", "ru")
LANG_LABEL = {"en": "English", "ru": "Русский"}

# fmt: off
STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "Lane Stack · Project Setup",
        "tab_coder": "Coder",
        "tab_coder_sub": "CLI + model + effort",
        "tab_stages": "Stages",
        "tab_stages_sub": "Conveyor · per-agent",
        "tab_memory": "Memory",
        "tab_memory_sub": "Fact corpus · opt-in",
        "tab_docs": "Docs",
        "tab_docs_sub": "Living docs/ · night",
        "tab_work": "Work",
        "tab_work_sub": "in-place vs worktree",
        "tab_night": "Night",
        "tab_night_sub": "Review & repair",
        "tab_ui": "UI",
        "tab_ui_sub": "Language",
        "tab_status": "Status",
        "tab_status_sub": "Host CLIs",
        "tab_info": "Info",
        "tab_info_sub": "Roles · first hour",
        "tab_apply": "Apply",
        "tab_apply_sub": "Save to project",
        "nav_title": "SETUP",
        "nav_hint": "click · ↑↓",
        "keys_nav": "click menu · ^←/^→ pane",
        "msg_nav": "Menu · ↑↓ section · Enter work",
        "msg_main": "Working pane",
        "sum_coder": "coder ",
        "sum_night_on": "night:ON",
        "sum_night_off": "night:off",
        "field_provider": "Provider",
        "field_model": "Model",
        "field_effort": "Effort",
        "field_fast": "Fast mode",
        "field_agent": "Agent",
        "coder_fast_hint": "Codex/Cursor · service_tier=fast (Codex credits or Cursor *-fast model). Independent of Effort.",
        "msg_fast": "Fast mode → {value}",
        "stages_h1": "  Conveyor stages\n",
        "stages_help": (
            "  Each stage has its own agent + model. ↑↓ fields (wraps stages) ·\n"
            "  ←→ / Space change value · 1-5 jump stage · p/n prev/next stage.\n\n"
        ),
        "stages_pipe_h2": "  Pipeline\n",
        "stages_fields_h2": "\n  Settings · {stage}\n",
        "stages_tip": (
            "\n  ←→ cycles the highlighted field. On «Provider» switch structural → Qwen/Kimi…\n"
            "  On «Model» you get the full catalog for that agent (Kimi has several).\n"
            "  Critique mode «gate» blocks pre-dispatch until pass/ack.\n"
            "  Fast mode (Codex/Cursor) is on Critique and Onboard.\n"
            "  Memory and Docs are their own tabs — not stages.\n"
        ),
        "memory_h1": "  Project memory\n",
        "memory_help": (
            "  Facts that cannot be derived from git. Off until Enabled.\n"
            "  ↑↓ fields · ←→ / Space change value.\n\n"
        ),
        "memory_fields_h2": "  Settings\n",
        "memory_info_h2": "\n  How it works\n",
        "memory_info": (
            "  1. Enabled = the only switch that creates/uses the corpus.\n"
            "  2. Layout: .agents/memory/ in git · .cls/local-memory/ this machine ·\n"
            "     .cls/index/ FTS (derived). Not PROGRESS / LESSONS / docs/.\n"
            "  3. CORE loads every session when Inject is on. Rest is on-demand:\n"
            "     lane-memory context / search / explain.\n"
            "  4. Write only via lane-memory write (one door). Night agent does not\n"
            "     invent facts. Maintain = nightly memory-maintain-project.\n"
            "  5. Defaults: Codex terra high · audience subagent · search auto.\n"
            "     Budgets are recommended; change only if a pack overflows.\n"
        ),
        "docs_h1": "  Project docs\n",
        "docs_help": (
            "  Living docs/ only. Off until Enabled. Night does not commit.\n"
            "  ↑↓ fields · ←→ / Space change value.\n\n"
        ),
        "docs_fields_h2": "  Settings\n",
        "docs_info_h2": "\n  How it works\n",
        "docs_info": (
            "  1. Enabled + Apply = docs-web skeleton now. Background: Luna\n"
            "     onboard (CLAUDE.md / app packs) then wiki INIT. No feature docs.\n"
            "  2. At Hour: docs-web → daylog → docs-stale → Luna on stale_docs.\n"
            "     stub always stale, filled first. No commit.\n"
            "  3. Living tree is docs/. wiki/ / TODO/ / docs/plans/ are archive.\n"
            "  4. Night updates every stale page (page_cap 0 = all). Optional\n"
            "     cap only if you set one. Since = git window. Hour = local clock.\n"
            "  5. Daylog: docs/log.md + .agents/session-log/DOCS-DAY-YYYY-MM-DD.md\n"
            "     maps today's committed files to the pages Luna should edit.\n"
        ),
        "stage_plan_critique": "Plan critique",
        "stage_plan_critique_badge": "CHEAP",
        "stage_write": "Write",
        "stage_write_badge": "MAIN",
        "stage_night_review": "Night review",
        "stage_night_review_badge": "CODEX",
        "stage_specialist": "Specialist",
        "stage_specialist_badge": "RISK",
        "stage_onboard": "Onboard",
        "stage_onboard_badge": "PASS",
        "stage_memory": "Memory",
        "stage_memory_badge": "SMA",
        "stage_docs": "Docs",
        "stage_docs_badge": "WIKI",
        "stage_fix_writer": "fix",
        "sfield_enabled": "Enabled",
        "sfield_mode": "Mode",
        "sfield_provider": "Provider",
        "sfield_model": "Model",
        "sfield_effort": "Effort",
        "sfield_fast": "Fast mode",
        "sfield_depth": "Onboard depth",
        "sfield_agent": "Agent",
        "sfield_when": "When",
        "sfield_maintain": "Maintain",
        "sfield_inject": "Inject CORE",
        "sfield_audience": "Audience",
        "sfield_personal_bot": "Bot CORE",
        "sfield_search_engine": "Search",
        "sfield_core_budget": "CORE bytes",
        "sfield_note_budget": "Note bytes",
        "sfield_index_budget": "Index bytes",
        "sfield_context_budget": "Pack bytes",
        "sfield_page_cap": "Page cap",
        "page_cap_all": "all",
        "sfield_since": "Since",
        "sfield_hour": "Hour",
        "msg_stage_page_cap": "Docs page cap: {n}",
        "msg_stage_since": "Docs window: {since}",
        "msg_stage_hour": "Docs cron hour: {hour}",
        "audience_owner": "owner",
        "audience_subagent": "subagent",
        "audience_export": "export",
        "engine_auto": "auto",
        "engine_fts5": "fts5",
        "engine_bm25": "bm25",
        "mode_advisory": "advisory",
        "mode_gate": "gate",
        "when_high_risk": "high-risk only",
        "when_always": "always",
        "prov_structural": "structural",
        "prov_qwen": "Qwen",
        "prov_kimi": "Kimi",
        "prov_grok": "Grok",
        "prov_agy": "AGY",
        "prov_codex": "Codex",
        "prov_cursor": "Cursor",
        "prov_opencode": "OpenCode",
        "pipe_crit": "crit",
        "pipe_write": "write",
        "pipe_night": "night",
        "pipe_spec": "spec",
        "coder_h1": "  Daytime coder\n",
        "coder_help": (
            "  Who implements task YAML. Claude remains PM/orchestrator.\n"
            "  One level at a time: ↑↓ fields → Enter list → Enter confirm.\n\n"
        ),
        "coder_settings": "  Settings\n",
        "coder_open_list": "  ←→ cycle · ⏎ list",
        "coder_tip": (
            "\n  Shortcuts: p provider · m model · e effort (open that list).\n"
            "  When done: 0 or Tab → Apply → Enter to save.\n"
        ),
        "coder_models_of": "{n}/{total} options for {writer}",
        "pick_h1": "  Choose {label}{parent}\n",
        "pick_help": "  ↑↓ move · Enter confirm · Esc / ← back to form\n\n",
        "pick_none": "  (no options)\n",
        "pick_footer": "\n  {n}/{total}  ·  current: {current}\n",
        "work_h1": "  Writer workspace\n",
        "work_help": (
            "  Where daytime writers edit code. Not about night review.\n"
            "  ↑↓ choose mode · Space/Enter select · +/- auto score · [ ]/,. session · m multi-write\n\n"
        ),
        "work_mode_h2": "  Mode\n",
        "work_auto_h2": "\n  Auto thresholds  (only when Mode = Auto)\n",
        "work_score_line": "  worktree when score ≥ {n} / 10     [+/-]\n",
        "work_multi_line": "  {sw}  worktree when ≥2 write tasks     [m]\n",
        "work_thr_ignored": "  (thresholds ignored until Mode = Auto)\n",
        "work_session_h2": "\n  Writer session\n",
        "work_session_line": "  tasks per session = {n} / 10     [[ ]]\n",
        "work_session_hint": "  1 = new session every task. Same run resumes until this limit.\n",
        "work_footer": (
            "\n  In-place: project_cwd = repo, PM commits main.\n"
            "  Worktree: wt-create → agent/<slug>, PM wt-merge-main.\n"
            "  Saved under workspace: in routing.profile.yaml.\n"
        ),
        "ws_in_place_title": "In-place (main)",
        "ws_in_place_blurb": "Writers edit the repo checkout. PM commits main. Best for small/solo sites.",
        "ws_worktree_title": "Always worktree",
        "ws_worktree_blurb": "Always wt-create → .worktrees/<slug>. PM merges with wt-merge-main.",
        "ws_auto_title": "Auto",
        "ws_auto_blurb": "Worktree when score ≥ threshold or ≥2 write tasks; else in-place.",
        "night_h1": "  Night shift\n",
        "night_help": (
            "  Optional Codex Sol review + bounded fix tasks via cron.\n"
            "  Keep OFF for simple/static sites.\n\n"
        ),
        "night_toggle": "  {sw}  Night review + repair     [Space]\n\n",
        "night_off_note": "  Night disabled → enabled: false in night-shift.yaml\n",
        "night_budget_h2": "  Fix budget  (+/-)\n",
        "night_budget_line": "  max_fix_tasks = {n} / 10\n",
        "night_merge_h2": "  Auto-merge  (a)\n",
        "night_merge_line": "  {sw}  Merge to main when green  (usually OFF)\n\n",
        "night_writer_h2": "  Night fix writer  (n, ↑↓)\n",
        "ui_h1": "  Interface\n",
        "ui_help": (
            "  TUI language only — run files and task YAML stay English.\n"
            "  ↑↓ language · Space/Enter select · L cycles anytime\n\n"
        ),
        "ui_lang_h2": "  Language\n",
        "ui_note": (
            "\n  Preference is saved in this project (ui.language) and as your\n"
            "  global default (~/.agents/doctor.ui.yaml) on Apply.\n"
        ),
        "status_h1": "  Host tooling\n",
        "status_help": "  Green = ready for writer lanes.\n\n",
        "status_profile": "\n  Profile preview · {profile}\n",
        "status_rescan": "\n  r  rescan CLIs\n",
        "apply_h1": "  Save to this project\n",
        "apply_help": "  Writes routing + night-shift. Safe to re-run anytime.\n\n",
        "apply_summary": "  Summary\n",
        "apply_project": "  project   {repo}\n",
        "apply_coder": "  coder     {title}  ({writer})\n",
        "apply_model": "  model     {model}\n",
        "apply_effort": "  effort    {effort}\n",
        "apply_fast": "  fast mode {value}\n",
        "apply_workspace": "  workspace {ws}\n",
        "apply_session": "  session   {n} tasks / session\n",
        "apply_lang": "  language  {lang}\n",
        "apply_night": "  night     {night}\n",
        "apply_critique": "  critique  {crit}\n",
        "apply_profile": "  profile   {profile}\n\n",
        "apply_files": "  Files\n",
        "apply_box1": "  ╔══════════════════════════════════╗\n",
        "apply_box2": "  ║   ENTER  ·  Save & close TUI     ║\n",
        "apply_box3": "  ╚══════════════════════════════════╝\n",
        "apply_footer": (
            "\n  Saves routing + stages + night-shift, then exits.\n"
            "  New runs pick up main_write + pipeline stages + workspace.\n"
        ),
        "keys_coder_pick": "↑↓ choose · Enter confirm · Esc back · q quit",
        "keys_coder": "↑↓ field · ←→ value · Enter list · Tab · 0 Apply",
        "keys_stages": "↑↓ field · ←→ value · 1-5 stage · p/n · Space",
        "keys_memory": "↑↓ field · ←→ value · Space · 0 Apply",
        "keys_docs": "↑↓ field · ←→ value · Space · 0 Apply",
        "keys_work": "↑↓ mode · Space select · +/- score · [ ]/,. session · m multi",
        "keys_night": "Space night · a merge · +/- budget · n writer",
        "keys_ui": "↑↓ language · L cycle · Tab tabs",
        "keys_status": "r rescan · 1-9 tabs · 0 Apply · q quit",
        "keys_info": "Tab next · 0 Apply · q quit",
        "keys_apply": "ENTER save · q quit",
        "info_h1": "  What this factory does\n",
        "info_help": (
            "  PM is Claude. Writers are host CLIs from the Coder tab.\n"
            "  Open this page anytime with ?\n\n"
        ),
        "info_roles_h2": "  Roles\n",
        "info_roles": (
            "  PM        Claude via lane-pm — plan, dispatch, merge. Not a writer.\n"
            "  Writer    process from Coder: Kimi / Qwen / Grok / AGY / Codex / Cursor / OpenCode\n"
            "  Onboard   Stages → Onboard — own provider + model (default Codex)\n"
            "  Night     Stages → Night review — read-only repair after hours\n\n"
        ),
        "info_pipe_h2": "  Conveyor\n",
        "info_pipe": (
            "  plan (PM) → critique → write → L1 verify → night / specialist\n"
            "  Onboard is a project passport, not a write lane.\n\n"
        ),
        "info_start_h2": "  Existing repo — first hour\n",
        "info_start": (
            "  1.  cd /path/to/repo && adoc     then Apply\n"
            "  2.  Stages → Onboard: pick the model that will fill the passport\n"
            "  3.  lane-pm\n"
            "  4.  In chat: /project-onboard    or shell: project-onboard .\n"
            "  5.  Next day: /resume-project    or say «продолж»\n\n"
        ),
        "info_cmds_h2": "  Commands\n",
        "info_cmds": (
            "  adoc                 this TUI — coder, stages, onboard model\n"
            "  lane-pm              start the Claude PM session\n"
            "  project-onboard .    write CLAUDE.md / docs/llm pack\n"
            "  resume-project .     Now / Blocked / Next\n"
            "  run-board            list runs\n\n"
        ),
        "info_onboard_note": (
            "  Onboard model is Stages → Onboard (not Coder).\n"
            "  Fast on Onboard = Codex service_tier + depth=fast (passport, not forensic).\n"
            "  Coder is only the daytime writer.\n"
        ),
        "msg_boot": "Left menu · click or ^← · ? help",
        "msg_tab": "Tab · {name}",
        "msg_focus": "Field → {name}",
        "msg_pick": "Pick {name} · ↑↓ · Enter",
        "msg_no_opts": "No options for {name}",
        "msg_coder": "Coder → {name}",
        "msg_model": "Model → {name}",
        "msg_agent": "Agent → {name}",
        "msg_effort": "Effort → {name}",
        "msg_cancelled": "Cancelled",
        "msg_workspace": "Workspace → {name}",
        "msg_ws_score": "worktree_min_score → {n}",
        "msg_session_max": "session_max_tasks → {n}",
        "msg_multi": "multi-write worktree → {on}",
        "msg_night": "Night → {on}",
        "msg_merge": "Auto-merge → {on}",
        "msg_night_writer": "Night writer list · ↑↓",
        "msg_night_fix": "Night fix writer → {name}",
        "msg_max_fix": "Max fix tasks → {n}",
        "msg_lang": "Language → {name}",
        "msg_rescan": "Host tooling rescanned",
        "msg_saved": "✓ Saved — closing…",
        "msg_apply_fail": "Apply failed: {err}",
        "msg_help_pick": "↑↓ choose · Enter ok · Esc back · q quit",
        "msg_help": "1 Coder 2 Stages 3 Memory 4 Docs 5 Work 6 Night 7 UI 8 Status 9 Info 0 Apply · L · q",
        "msg_stage": "Stage → {name}",
        "msg_stage_enabled": "{stage} → {on}",
        "msg_stage_mode": "Critique mode → {mode}",
        "msg_stage_when": "Specialist when → {when}",
        "msg_stage_provider": "Stage provider → {provider}",
        "msg_stage_model": "Stage model → {model}",
        "msg_stage_effort": "Stage effort → {effort}",
        "msg_stage_fast": "Onboard Fast mode → {value}",
        "msg_stage_fast_na": "Fast mode only for Codex/Cursor onboard",
        "msg_stage_depth": "Onboard depth → {value}",
        "msg_stage_write_fixed": "Write stage is always on (pick provider/model)",
        "msg_stage_flag": "{field} → {on}",
        "msg_stage_audience": "Memory audience → {audience}",
        "msg_stage_bot": "Memory bot CORE → {bot}",
        "msg_stage_engine": "Memory search → {engine}",
        "msg_stage_budget": "{field} → {n}",
        "msg_stage_edit": "{stage} · {field}",
        "msg_stage_no_models": "No models for this provider — pick another agent",
        "model_na": "n/a (structural)",
        "on": "ON",
        "off": "off",
        "wr_qwen_blurb": "Fast everyday coder for product work",
        "wr_kimi_blurb": "Long-context Kimi K3 (256k)",
        "wr_grok_blurb": "xAI Grok writer lane",
        "wr_agy_blurb": "Gemini 3.7 Flash high via AGY",
        "wr_codex_blurb": "Bare Codex lane-writer (no host MCP/plugins)",
        "wr_cursor_blurb": "Cursor Agent CLI — any account model (+ fast siblings)",
        "wr_opencode_blurb": "OpenCode CLI — any connected model + host agent (build/plan/wiki/…)",
        "wr_auto_blurb": "First available: Kimi → Qwen → Grok → AGY",
        "done_title": "✓ Project configured",
        "done_lbl_path": "path",
        "done_lbl_coder": "coder",
        "done_lbl_model": "model",
        "done_lbl_effort": "effort",
        "done_lbl_fast": "fast mode",
        "done_lbl_ws": "workspace",
        "done_lbl_session": "session",
        "done_lbl_lang": "language",
        "done_lbl_night": "night",
        "done_lbl_critique": "critique",
        "done_lbl_files": "wrote",
        "done_fast_on": "ON  ·  service_tier=fast  (~1.5× speed, ~2.5× credits)",
        "done_fast_off": "off  ·  service_tier=standard",
        "done_night_on": "on  ·  fix={provider}  max={max}",
        "done_night_off": "off",
        "done_file_routing": "routing.profile.yaml",
        "done_file_night": "night-shift.yaml",
        "done_hint": "New runs use this conveyor. Re-open: agents-doctor / adoc",
        # legacy keys kept for safety
        "done_path": "  path:     {v}",
        "done_coder": "  coder:    {v}",
        "done_model": "  model:    {v}",
        "done_effort": "  effort:   {v}",
        "done_fast": "  fast:     {v}",
        "done_ws": "  workspace:{v}",
        "done_lang": "  language: {v}",
        "done_night": "  night:    {v}",
        "done_critique": "  critique: {v}",
        "done_wrote": "  wrote:    {v}",
        "err_no_pt": "TUI needs prompt_toolkit. Falling back to: agents-doctor setup",
        "err_no_claude": "ERROR: Claude Code is required as PM.",
        "err_tui": "TUI error: {err}\nFalling back to setup wizard.",
    },
    "ru": {
        "app_title": "Lane Stack · Настройка проекта",
        "tab_coder": "Кодер",
        "tab_coder_sub": "CLI + модель + effort",
        "tab_stages": "Этапы",
        "tab_stages_sub": "Конвейер · агенты",
        "tab_memory": "Память",
        "tab_memory_sub": "Факты · opt-in",
        "tab_docs": "Документация",
        "tab_docs_sub": "Живые docs/ · ночь",
        "tab_work": "Work",
        "tab_work_sub": "main или worktree",
        "tab_night": "Ночь",
        "tab_night_sub": "Ревью и фиксы",
        "tab_ui": "UI",
        "tab_ui_sub": "Язык интерфейса",
        "tab_status": "Статус",
        "tab_status_sub": "CLI хоста",
        "tab_info": "Информация",
        "tab_info_sub": "Роли · первый час",
        "tab_apply": "Сохранить",
        "tab_apply_sub": "Запись в проект",
        "nav_title": "НАСТРОЙКА",
        "nav_hint": "клик · ↑↓",
        "keys_nav": "клик меню · ^←/^→ панель",
        "msg_nav": "Меню · ↑↓ раздел · Enter работа",
        "msg_main": "Рабочая панель",
        "sum_coder": "кодер ",
        "sum_night_on": "ночь:ВКЛ",
        "sum_night_off": "ночь:выкл",
        "field_provider": "Провайдер",
        "field_model": "Модель",
        "field_effort": "Effort",
        "field_fast": "Fast mode",
        "field_agent": "Агент",
        "coder_fast_hint": "Codex/Cursor · service_tier=fast (кредиты Codex или модель Cursor *-fast). Не зависит от Effort.",
        "msg_fast": "Fast mode → {value}",
        "stages_h1": "  Этапы конвейера\n",
        "stages_help": (
            "  У каждого этапа свой агент и модель. ↑↓ поля (переходит между этапами) ·\n"
            "  ←→ / Пробел сменить значение · 1–5 этап · p/n предыдущий/следующий.\n\n"
        ),
        "stages_pipe_h2": "  Конвейер\n",
        "stages_fields_h2": "\n  Настройки · {stage}\n",
        "stages_tip": (
            "\n  ←→ крутит выделенное поле. «Провайдер»: структурный → Qwen/Kimi/Grok…\n"
            "  «Модель»: полный каталог агента (у Kimi несколько вариантов).\n"
            "  Режим «шлюз» блокирует pre-dispatch, пока нет pass/ack.\n"
            "  Fast mode (Codex/Cursor) — критика и онбординг.\n"
            "  Память и Документация — отдельные вкладки, не этапы.\n"
        ),
        "memory_h1": "  Память проекта\n",
        "memory_help": (
            "  Факты, которые нельзя вывести из git. Выкл, пока не Enabled.\n"
            "  ↑↓ поля · ←→ / Пробел сменить значение.\n\n"
        ),
        "memory_fields_h2": "  Настройки\n",
        "memory_info_h2": "\n  Как работает\n",
        "memory_info": (
            "  1. Enabled — единственный рубильник корпуса.\n"
            "  2. Раскладка: .agents/memory/ в git · .cls/local-memory/ эта машина ·\n"
            "     .cls/index/ FTS. Не PROGRESS / LESSONS / docs/.\n"
            "  3. CORE грузится каждую сессию, если Inject вкл. Остальное по запросу:\n"
            "     lane-memory context / search / explain.\n"
            "  4. Писать только через lane-memory write (одна дверь). Ночной агент\n"
            "     факты не выдумывает. Фон = memory-maintain-project.\n"
            "  5. Дефолт: Codex terra high · audience subagent · search auto.\n"
            "     Бюджеты уже рекомендуемые; крути, если пак не влезает.\n"
        ),
        "docs_h1": "  Документация проекта\n",
        "docs_help": (
            "  Живые только docs/. Выкл, пока не Enabled. Ночь не коммитит.\n"
            "  ↑↓ поля · ←→ / Пробел сменить значение.\n\n"
        ),
        "docs_fields_h2": "  Настройки\n",
        "docs_info_h2": "\n  Как работает\n",
        "docs_info": (
            "  1. Enabled + Apply = скелет docs-web сразу. Фон: Luna сначала\n"
            "     онбордит паспорт (CLAUDE.md / apps/*), потом wiki INIT.\n"
            "  2. В Час: docs-web → daylog → docs-stale → Luna по stale_docs.\n"
            "     stub всегда stale, fill первым. Без commit.\n"
            "  3. Живое дерево — docs/. wiki/ / TODO/ / docs/plans/ — архив.\n"
            "  4. Ночь правит все stale-страницы (лимит 0 = все). Потолок\n"
            "     только если выставишь сам. Окно = git since. Час — локальный.\n"
            "  5. Daylog: docs/log.md + .agents/session-log/DOCS-DAY-YYYY-MM-DD.md\n"
            "     карта сегодняшних коммитов → какие страницы править точечно.\n"
        ),
        "stage_plan_critique": "Критика плана",
        "stage_plan_critique_badge": "БЫСТР",
        "stage_write": "Код",
        "stage_write_badge": "ОСНОВ",
        "stage_night_review": "Ночной ревью",
        "stage_night_review_badge": "CODEX",
        "stage_specialist": "Специалист",
        "stage_specialist_badge": "РИСК",
        "stage_onboard": "Онбординг",
        "stage_onboard_badge": "ПАСПОРТ",
        "stage_memory": "Память",
        "stage_memory_badge": "SMA",
        "stage_docs": "Документация",
        "stage_docs_badge": "WIKI",
        "stage_fix_writer": "фикс",
        "sfield_enabled": "Включено",
        "sfield_mode": "Режим",
        "sfield_provider": "Провайдер",
        "sfield_model": "Модель",
        "sfield_effort": "Effort",
        "sfield_fast": "Fast mode",
        "sfield_depth": "Глубина онборда",
        "sfield_agent": "Агент",
        "sfield_when": "Когда",
        "sfield_maintain": "Фон",
        "sfield_inject": "Вшивать ядро",
        "sfield_audience": "Аудитория",
        "sfield_personal_bot": "Ядро бота",
        "sfield_search_engine": "Поиск",
        "sfield_core_budget": "Ядро байт",
        "sfield_note_budget": "Заметка байт",
        "sfield_index_budget": "Индекс байт",
        "sfield_context_budget": "Пакет байт",
        "sfield_page_cap": "Лимит страниц",
        "page_cap_all": "все",
        "sfield_since": "Окно",
        "sfield_hour": "Час",
        "msg_stage_page_cap": "Лимит страниц docs: {n}",
        "msg_stage_since": "Окно docs: {since}",
        "msg_stage_hour": "Час cron docs: {hour}",
        "audience_owner": "владелец",
        "audience_subagent": "субагент",
        "audience_export": "экспорт",
        "engine_auto": "auto",
        "engine_fts5": "fts5",
        "engine_bm25": "bm25",
        "mode_advisory": "совет",
        "mode_gate": "шлюз",
        "when_high_risk": "только high-risk",
        "when_always": "всегда",
        "prov_structural": "структурный",
        "prov_qwen": "Qwen",
        "prov_kimi": "Kimi",
        "prov_grok": "Grok",
        "prov_agy": "AGY",
        "prov_codex": "Codex",
        "prov_cursor": "Cursor",
        "prov_opencode": "OpenCode",
        "pipe_crit": "критика",
        "pipe_write": "код",
        "pipe_night": "ночь",
        "pipe_spec": "спец",
        "coder_h1": "  Дневной кодер\n",
        "coder_help": (
            "  Кто пишет код по task YAML. Claude остаётся PM/оркестратором.\n"
            "  Один уровень: ↑↓ поля → Enter список → Enter выбрать.\n\n"
        ),
        "coder_settings": "  Настройки\n",
        "coder_open_list": "  ←→ листать · ⏎ список",
        "coder_tip": (
            "\n  Ярлыки: p провайдер · m модель · e effort (открыть список).\n"
            "  Готово: 0 или Tab → Сохранить → Enter.\n"
        ),
        "coder_models_of": "{n}/{total} вариантов для {writer}",
        "pick_h1": "  Выберите {label}{parent}\n",
        "pick_help": "  ↑↓ · Enter подтвердить · Esc / ← назад\n\n",
        "pick_none": "  (нет вариантов)\n",
        "pick_footer": "\n  {n}/{total}  ·  сейчас: {current}\n",
        "work_h1": "  Рабочая область writer\n",
        "work_help": (
            "  Куда пишут дневные writer’ы. Не про ночной review.\n"
            "  ↑↓ режим · Space/Enter · +/- порог auto · [ ]/,. сессия · m multi-write\n\n"
        ),
        "work_mode_h2": "  Режим\n",
        "work_auto_h2": "\n  Пороги Auto  (только при Mode = Auto)\n",
        "work_score_line": "  worktree если score ≥ {n} / 10     [+/-]\n",
        "work_multi_line": "  {sw}  worktree если ≥2 write-задач     [m]\n",
        "work_thr_ignored": "  (пороги не действуют, пока Mode ≠ Auto)\n",
        "work_session_h2": "\n  Сессия writer\n",
        "work_session_line": "  задач на сессию = {n} / 10     [[ ]]\n",
        "work_session_hint": "  1 = новая сессия на каждую задачу. Иначе resume в том же run до лимита.\n",
        "work_footer": (
            "\n  In-place: project_cwd = repo, PM коммитит main.\n"
            "  Worktree: wt-create → agent/<slug>, PM wt-merge-main.\n"
            "  Пишется в workspace: в routing.profile.yaml.\n"
        ),
        "ws_in_place_title": "In-place (main)",
        "ws_in_place_blurb": "Writer’ы правят checkout репо. PM коммитит main. Удобно для мелких сайтов.",
        "ws_worktree_title": "Всегда worktree",
        "ws_worktree_blurb": "Всегда wt-create → .worktrees/<slug>. PM мержит wt-merge-main.",
        "ws_auto_title": "Auto",
        "ws_auto_blurb": "Worktree при score ≥ порога или ≥2 write-задачах; иначе in-place.",
        "night_h1": "  Ночная смена\n",
        "night_help": (
            "  Опциональный Codex Sol review + ограниченные фиксы по cron.\n"
            "  Для простых/статических сайтов лучше OFF.\n\n"
        ),
        "night_toggle": "  {sw}  Ночной review + repair     [Space]\n\n",
        "night_off_note": "  Ночь выкл → enabled: false в night-shift.yaml\n",
        "night_budget_h2": "  Бюджет фиксов  (+/-)\n",
        "night_budget_line": "  max_fix_tasks = {n} / 10\n",
        "night_merge_h2": "  Auto-merge  (a)\n",
        "night_merge_line": "  {sw}  Мерж в main при green  (обычно OFF)\n\n",
        "night_writer_h2": "  Ночной fix-writer  (n, ↑↓)\n",
        "ui_h1": "  Интерфейс\n",
        "ui_help": (
            "  Только язык TUI — run-файлы и task YAML остаются на английском.\n"
            "  ↑↓ язык · Space/Enter · L переключает в любой момент\n\n"
        ),
        "ui_lang_h2": "  Язык\n",
        "ui_note": (
            "\n  Сохраняется в проекте (ui.language) и как глобальный default\n"
            "  (~/.agents/doctor.ui.yaml) при Apply.\n"
        ),
        "status_h1": "  Инструменты хоста\n",
        "status_help": "  Зелёный = готово для writer lanes.\n\n",
        "status_profile": "\n  Превью профиля · {profile}\n",
        "status_rescan": "\n  r  пересканировать CLI\n",
        "apply_h1": "  Сохранить в проект\n",
        "apply_help": "  Пишет routing + night-shift. Можно запускать снова.\n\n",
        "apply_summary": "  Итог\n",
        "apply_project": "  проект    {repo}\n",
        "apply_coder": "  кодер     {title}  ({writer})\n",
        "apply_model": "  модель    {model}\n",
        "apply_effort": "  effort    {effort}\n",
        "apply_fast": "  fast mode {value}\n",
        "apply_workspace": "  workspace {ws}\n",
        "apply_session": "  сессия    {n} задач / сессия\n",
        "apply_lang": "  язык      {lang}\n",
        "apply_night": "  ночь      {night}\n",
        "apply_critique": "  critique  {crit}\n",
        "apply_profile": "  profile   {profile}\n\n",
        "apply_files": "  Файлы\n",
        "apply_box1": "  ╔══════════════════════════════════╗\n",
        "apply_box2": "  ║   ENTER  ·  Сохранить и выйти    ║\n",
        "apply_box3": "  ╚══════════════════════════════════╝\n",
        "apply_footer": (
            "\n  Сохраняет routing + stages + night-shift и закрывает TUI.\n"
            "  Новые run’ы берут main_write + этапы конвейера + workspace.\n"
        ),
        "keys_coder_pick": "↑↓ выбор · Enter · Esc назад · q выход",
        "keys_coder": "↑↓ поле · ←→ значение · Enter список · Tab · 0 Сохранить",
        "keys_stages": "↑↓ поле · ←→ значение · 1–5 этап · p/n · Пробел",
        "keys_memory": "↑↓ поле · ←→ значение · Пробел · 0 Сохранить",
        "keys_docs": "↑↓ поле · ←→ значение · Пробел · 0 Сохранить",
        "keys_work": "↑↓ режим · Space · +/- score · [ ]/,. сессия · m multi",
        "keys_night": "Space ночь · a merge · +/- бюджет · n writer",
        "keys_ui": "↑↓ язык · L переключить · Tab",
        "keys_status": "r rescan · 1–9 вкладки · 0 Сохранить · q выход",
        "keys_info": "Tab дальше · 0 Сохранить · q выход",
        "keys_apply": "ENTER сохранить · q выход",
        "info_h1": "  Что делает эта фабрика\n",
        "info_help": (
            "  PM — Claude. Писатели — CLI с вкладки Кодер.\n"
            "  Сюда всегда можно попасть по ?\n\n"
        ),
        "info_roles_h2": "  Роли\n",
        "info_roles": (
            "  PM        Claude через lane-pm — план, диспатч, merge. Не писатель.\n"
            "  Writer    процесс с Кодера: Kimi / Qwen / Grok / AGY / Codex / Cursor / OpenCode\n"
            "  Онбординг Этапы → Онбординг — свой провайдер и модель (по умолчанию Codex)\n"
            "  Ночь      Этапы → Ночной ревью — только чтение/ремонт ночью\n\n"
        ),
        "info_pipe_h2": "  Конвейер\n",
        "info_pipe": (
            "  план (PM) → критика → код → L1 verify → ночь / специалист\n"
            "  Онбординг — паспорт проекта, не lane записи.\n\n"
        ),
        "info_start_h2": "  Существующий репо — первый час\n",
        "info_start": (
            "  1.  cd /path/to/repo && adoc     потом Сохранить\n"
            "  2.  Этапы → Онбординг: модель, которая заполнит паспорт\n"
            "  3.  lane-pm\n"
            "  4.  В чате: /project-onboard     или в шелле: project-onboard .\n"
            "  5.  Назавтра: /resume-project    или «продолж»\n\n"
        ),
        "info_cmds_h2": "  Команды\n",
        "info_cmds": (
            "  adoc                 этот TUI — кодер, этапы, модель онбординга\n"
            "  lane-pm              сессия Claude PM\n"
            "  project-onboard .    CLAUDE.md / пакет docs/llm\n"
            "  resume-project .     Сейчас / Блок / Дальше\n"
            "  run-board            список ранов\n\n"
        ),
        "info_onboard_note": (
            "  Модель онбординга — Этапы → Онбординг (не Кодер).\n"
            "  Fast на Онбординге = service_tier Codex + depth=fast (паспорт, не forensic).\n"
            "  Кодер — только дневной писатель.\n"
        ),
        "msg_boot": "Меню слева · клик или ^← · ? справка",
        "msg_tab": "Вкладка · {name}",
        "msg_focus": "Поле → {name}",
        "msg_pick": "Выбор {name} · ↑↓ · Enter",
        "msg_no_opts": "Нет вариантов для {name}",
        "msg_coder": "Кодер → {name}",
        "msg_model": "Модель → {name}",
        "msg_agent": "Агент → {name}",
        "msg_effort": "Effort → {name}",
        "msg_cancelled": "Отмена",
        "msg_workspace": "Workspace → {name}",
        "msg_ws_score": "worktree_min_score → {n}",
        "msg_session_max": "session_max_tasks → {n}",
        "msg_multi": "multi-write worktree → {on}",
        "msg_night": "Ночь → {on}",
        "msg_merge": "Auto-merge → {on}",
        "msg_night_writer": "Список night writer · ↑↓",
        "msg_night_fix": "Night fix writer → {name}",
        "msg_max_fix": "Max fix tasks → {n}",
        "msg_lang": "Язык → {name}",
        "msg_rescan": "CLI пересканированы",
        "msg_saved": "✓ Сохранено — закрываю…",
        "msg_apply_fail": "Ошибка Apply: {err}",
        "msg_help_pick": "↑↓ · Enter · Esc назад · q выход",
        "msg_help": "1 Кодер 2 Этапы 3 Память 4 Документация 5 Work 6 Ночь 7 UI 8 Статус 9 Инфо 0 Сохранить · L · q",
        "msg_stage": "Этап → {name}",
        "msg_stage_enabled": "{stage} → {on}",
        "msg_stage_mode": "Режим критики → {mode}",
        "msg_stage_when": "Специалист когда → {when}",
        "msg_stage_provider": "Провайдер этапа → {provider}",
        "msg_stage_model": "Модель этапа → {model}",
        "msg_stage_effort": "Effort этапа → {effort}",
        "msg_stage_fast": "Onboard Fast mode → {value}",
        "msg_stage_fast_na": "Fast mode только для Codex/Cursor онбординга",
        "msg_stage_depth": "Глубина онборда → {value}",
        "msg_stage_write_fixed": "Этап «Код» всегда включён (меняйте провайдер/модель)",
        "msg_stage_flag": "{field} → {on}",
        "msg_stage_audience": "Аудитория памяти → {audience}",
        "msg_stage_bot": "Ядро бота → {bot}",
        "msg_stage_engine": "Поиск памяти → {engine}",
        "msg_stage_budget": "{field} → {n}",
        "msg_stage_edit": "{stage} · {field}",
        "msg_stage_no_models": "Нет моделей — выберите другого провайдера",
        "model_na": "н/д (структурный)",
        "on": "ВКЛ",
        "off": "выкл",
        "wr_qwen_blurb": "Быстрый повседневный кодер",
        "wr_kimi_blurb": "Длинный контекст Kimi K3 (256k)",
        "wr_grok_blurb": "Writer-lane xAI Grok",
        "wr_agy_blurb": "Gemini 3.7 Flash high через AGY",
        "wr_codex_blurb": "Bare Codex lane-writer (без host MCP/plugins)",
        "wr_cursor_blurb": "Cursor Agent CLI — любая модель аккаунта (+ fast)",
        "wr_opencode_blurb": "OpenCode CLI — любая подключённая модель + агент хоста (build/plan/wiki/…)",
        "wr_auto_blurb": "Первый доступный: Kimi → Qwen → Grok → AGY",
        "done_title": "✓ Проект настроен",
        "done_lbl_path": "путь",
        "done_lbl_coder": "кодер",
        "done_lbl_model": "модель",
        "done_lbl_effort": "effort",
        "done_lbl_fast": "fast mode",
        "done_lbl_ws": "workspace",
        "done_lbl_session": "сессия",
        "done_lbl_lang": "язык",
        "done_lbl_night": "ночь",
        "done_lbl_critique": "critique",
        "done_lbl_files": "записано",
        "done_fast_on": "ВКЛ  ·  service_tier=fast  (~1.5× скорость, ~2.5× кредиты)",
        "done_fast_off": "выкл  ·  service_tier=standard",
        "done_night_on": "вкл  ·  fix={provider}  max={max}",
        "done_night_off": "выкл",
        "done_file_routing": "routing.profile.yaml",
        "done_file_night": "night-shift.yaml",
        "done_hint": "Новые run’ы берут этот конвейер. Снова: agents-doctor / adoc",
        "done_path": "  путь:     {v}",
        "done_coder": "  кодер:    {v}",
        "done_model": "  модель:   {v}",
        "done_effort": "  effort:   {v}",
        "done_fast": "  fast:     {v}",
        "done_ws": "  workspace:{v}",
        "done_lang": "  язык:     {v}",
        "done_night": "  ночь:     {v}",
        "done_critique": "  critique: {v}",
        "done_wrote": "  записано: {v}",
        "err_no_pt": "TUI нужен prompt_toolkit. Откат: agents-doctor setup",
        "err_no_claude": "ERROR: Claude Code обязателен как PM.",
        "err_tui": "Ошибка TUI: {err}\nОткат на setup wizard.",
    },
}
# fmt: on


def normalize_lang(value: object) -> str:
    raw = str(value or "en").strip().lower()
    if raw in {"ru", "rus", "russian", "рус", "русский"}:
        return "ru"
    return "en"


def tr(ui_lang: str, key: str, **kwargs: Any) -> str:
    """Translate key; fall back to English then key name.

    First arg is the UI language code — named ui_lang so format kwargs can
    freely use {lang} / {key} without colliding with parameters.
    """
    code = normalize_lang(ui_lang)
    table = STRINGS.get(code) or STRINGS["en"]
    text = table.get(key) or STRINGS["en"].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def writer_blurb(ui_lang: str, writer: str) -> str:
    return tr(ui_lang, f"wr_{writer}_blurb")
