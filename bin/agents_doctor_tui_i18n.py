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
        "tab_work": "Work",
        "tab_work_sub": "in-place vs worktree",
        "tab_night": "Night",
        "tab_night_sub": "Review & repair",
        "tab_ui": "UI",
        "tab_ui_sub": "Language",
        "tab_status": "Status",
        "tab_status_sub": "Host CLIs",
        "tab_apply": "Apply",
        "tab_apply_sub": "Save to project",
        "sum_coder": "coder ",
        "sum_night_on": "night:ON",
        "sum_night_off": "night:off",
        "field_provider": "Provider",
        "field_model": "Model",
        "field_effort": "Effort",
        "field_fast": "Fast mode",
        "coder_fast_hint": "Codex only · service_tier=fast (~1.5× speed, ~2.5× ChatGPT credits). Independent of Effort.",
        "msg_fast": "Fast mode → {value}",
        "stages_h1": "  Conveyor stages\n",
        "stages_help": (
            "  Each stage has its own agent + model. ↑↓ fields (wraps stages) ·\n"
            "  ←→ / Space change value · 1-4 jump stage · p/n prev/next stage.\n\n"
        ),
        "stages_pipe_h2": "  Pipeline\n",
        "stages_fields_h2": "\n  Settings · {stage}\n",
        "stages_tip": (
            "\n  ←→ cycles the highlighted field. On «Provider» switch structural → Qwen/Kimi…\n"
            "  On «Model» you get the full catalog for that agent (Kimi has several).\n"
            "  Critique mode «gate» blocks pre-dispatch until pass/ack.\n"
        ),
        "stage_plan_critique": "Plan critique",
        "stage_plan_critique_badge": "CHEAP",
        "stage_write": "Write",
        "stage_write_badge": "MAIN",
        "stage_night_review": "Night review",
        "stage_night_review_badge": "CODEX",
        "stage_specialist": "Specialist",
        "stage_specialist_badge": "RISK",
        "stage_fix_writer": "fix",
        "sfield_enabled": "Enabled",
        "sfield_mode": "Mode",
        "sfield_provider": "Provider",
        "sfield_model": "Model",
        "sfield_effort": "Effort",
        "sfield_when": "When",
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
        "coder_open_list": "  ⏎ list",
        "coder_tip": (
            "\n  Shortcuts: p provider · m model · e effort (open that list).\n"
            "  When done: 7 or Tab → Apply → Enter to save.\n"
        ),
        "coder_models_of": "{n}/{total} options for {writer}",
        "pick_h1": "  Choose {label}{parent}\n",
        "pick_help": "  ↑↓ move · Enter confirm · Esc / ← back to form\n\n",
        "pick_none": "  (no options)\n",
        "pick_footer": "\n  {n}/{total}  ·  current: {current}\n",
        "work_h1": "  Writer workspace\n",
        "work_help": (
            "  Where daytime writers edit code. Not about night review.\n"
            "  ↑↓ choose mode · Space/Enter select · +/- auto score · m multi-write\n\n"
        ),
        "work_mode_h2": "  Mode\n",
        "work_auto_h2": "\n  Auto thresholds  (only when Mode = Auto)\n",
        "work_score_line": "  worktree when score ≥ {n} / 10     [+/-]\n",
        "work_multi_line": "  {sw}  worktree when ≥2 write tasks     [m]\n",
        "work_thr_ignored": "  (thresholds ignored until Mode = Auto)\n",
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
        "keys_coder": "↑↓ field · Enter list · Tab tabs · 7 Apply",
        "keys_stages": "↑↓ field · ←→ value · 1-4 stage · p/n · Space",
        "keys_work": "↑↓ mode · Space select · +/- score · m multi",
        "keys_night": "Space night · a merge · +/- budget · n writer",
        "keys_ui": "↑↓ language · L cycle · Tab tabs",
        "keys_status": "r rescan · 1-7 tabs · q quit",
        "keys_apply": "ENTER save · q quit",
        "msg_boot": "2 Stages · L language · ? help · conveyor strip below",
        "msg_tab": "Tab · {name}",
        "msg_focus": "Field → {name}",
        "msg_pick": "Pick {name} · ↑↓ · Enter",
        "msg_no_opts": "No options for {name}",
        "msg_coder": "Coder → {name}",
        "msg_model": "Model → {name}",
        "msg_effort": "Effort → {name}",
        "msg_cancelled": "Cancelled",
        "msg_workspace": "Workspace → {name}",
        "msg_ws_score": "worktree_min_score → {n}",
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
        "msg_help": "1 Coder 2 Stages 3 Work 4 Night 5 UI 6 Status 7 Apply · L · q",
        "msg_stage": "Stage → {name}",
        "msg_stage_enabled": "{stage} → {on}",
        "msg_stage_mode": "Critique mode → {mode}",
        "msg_stage_when": "Specialist when → {when}",
        "msg_stage_provider": "Stage provider → {provider}",
        "msg_stage_model": "Stage model → {model}",
        "msg_stage_effort": "Stage effort → {effort}",
        "msg_stage_write_fixed": "Write stage is always on (pick provider/model)",
        "msg_stage_edit": "{stage} · {field}",
        "msg_stage_no_models": "No models for this provider — pick another agent",
        "model_na": "n/a (structural)",
        "on": "ON",
        "off": "off",
        "wr_qwen_blurb": "Fast everyday coder for product work",
        "wr_kimi_blurb": "Long-context Kimi K3 (256k)",
        "wr_grok_blurb": "xAI Grok writer lane",
        "wr_agy_blurb": "Gemini Flash high via AGY",
        "wr_codex_blurb": "Bare Codex lane-writer (no host MCP/plugins)",
        "wr_auto_blurb": "First available: Kimi → Qwen → Grok → AGY",
        "done_title": "✓ Project configured",
        "done_lbl_path": "path",
        "done_lbl_coder": "coder",
        "done_lbl_model": "model",
        "done_lbl_effort": "effort",
        "done_lbl_fast": "fast mode",
        "done_lbl_ws": "workspace",
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
        "tab_work": "Work",
        "tab_work_sub": "main или worktree",
        "tab_night": "Ночь",
        "tab_night_sub": "Ревью и фиксы",
        "tab_ui": "UI",
        "tab_ui_sub": "Язык интерфейса",
        "tab_status": "Статус",
        "tab_status_sub": "CLI хоста",
        "tab_apply": "Сохранить",
        "tab_apply_sub": "Запись в проект",
        "sum_coder": "кодер ",
        "sum_night_on": "ночь:ВКЛ",
        "sum_night_off": "ночь:выкл",
        "field_provider": "Провайдер",
        "field_model": "Модель",
        "field_effort": "Effort",
        "field_fast": "Fast mode",
        "coder_fast_hint": "Только Codex · service_tier=fast (~1.5× скорость, ~2.5× кредиты ChatGPT). Не зависит от Effort.",
        "msg_fast": "Fast mode → {value}",
        "stages_h1": "  Этапы конвейера\n",
        "stages_help": (
            "  У каждого этапа свой агент и модель. ↑↓ поля (переходит между этапами) ·\n"
            "  ←→ / Пробел сменить значение · 1–4 этап · p/n предыдущий/следующий.\n\n"
        ),
        "stages_pipe_h2": "  Конвейер\n",
        "stages_fields_h2": "\n  Настройки · {stage}\n",
        "stages_tip": (
            "\n  ←→ крутит выделенное поле. «Провайдер»: структурный → Qwen/Kimi/Grok…\n"
            "  «Модель»: полный каталог агента (у Kimi несколько вариантов).\n"
            "  Режим «шлюз» блокирует pre-dispatch, пока нет pass/ack.\n"
        ),
        "stage_plan_critique": "Критика плана",
        "stage_plan_critique_badge": "БЫСТР",
        "stage_write": "Код",
        "stage_write_badge": "ОСНОВ",
        "stage_night_review": "Ночной ревью",
        "stage_night_review_badge": "CODEX",
        "stage_specialist": "Специалист",
        "stage_specialist_badge": "РИСК",
        "stage_fix_writer": "фикс",
        "sfield_enabled": "Включено",
        "sfield_mode": "Режим",
        "sfield_provider": "Провайдер",
        "sfield_model": "Модель",
        "sfield_effort": "Effort",
        "sfield_when": "Когда",
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
        "coder_open_list": "  ⏎ список",
        "coder_tip": (
            "\n  Ярлыки: p провайдер · m модель · e effort (открыть список).\n"
            "  Готово: 7 или Tab → Сохранить → Enter.\n"
        ),
        "coder_models_of": "{n}/{total} вариантов для {writer}",
        "pick_h1": "  Выберите {label}{parent}\n",
        "pick_help": "  ↑↓ · Enter подтвердить · Esc / ← назад\n\n",
        "pick_none": "  (нет вариантов)\n",
        "pick_footer": "\n  {n}/{total}  ·  сейчас: {current}\n",
        "work_h1": "  Рабочая область writer\n",
        "work_help": (
            "  Куда пишут дневные writer’ы. Не про ночной review.\n"
            "  ↑↓ режим · Space/Enter · +/- порог auto · m multi-write\n\n"
        ),
        "work_mode_h2": "  Режим\n",
        "work_auto_h2": "\n  Пороги Auto  (только при Mode = Auto)\n",
        "work_score_line": "  worktree если score ≥ {n} / 10     [+/-]\n",
        "work_multi_line": "  {sw}  worktree если ≥2 write-задач     [m]\n",
        "work_thr_ignored": "  (пороги не действуют, пока Mode ≠ Auto)\n",
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
        "keys_coder": "↑↓ поле · Enter список · Tab · 7 Сохранить",
        "keys_stages": "↑↓ поле · ←→ значение · 1–4 этап · p/n · Пробел",
        "keys_work": "↑↓ режим · Space · +/- score · m multi",
        "keys_night": "Space ночь · a merge · +/- бюджет · n writer",
        "keys_ui": "↑↓ язык · L переключить · Tab",
        "keys_status": "r rescan · 1-7 вкладки · q выход",
        "keys_apply": "ENTER сохранить · q выход",
        "msg_boot": "2 Этапы · L язык · ? справка · конвейер снизу",
        "msg_tab": "Вкладка · {name}",
        "msg_focus": "Поле → {name}",
        "msg_pick": "Выбор {name} · ↑↓ · Enter",
        "msg_no_opts": "Нет вариантов для {name}",
        "msg_coder": "Кодер → {name}",
        "msg_model": "Модель → {name}",
        "msg_effort": "Effort → {name}",
        "msg_cancelled": "Отмена",
        "msg_workspace": "Workspace → {name}",
        "msg_ws_score": "worktree_min_score → {n}",
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
        "msg_help": "1 Кодер 2 Этапы 3 Work 4 Ночь 5 UI 6 Статус 7 Сохранить · L · q",
        "msg_stage": "Этап → {name}",
        "msg_stage_enabled": "{stage} → {on}",
        "msg_stage_mode": "Режим критики → {mode}",
        "msg_stage_when": "Специалист когда → {when}",
        "msg_stage_provider": "Провайдер этапа → {provider}",
        "msg_stage_model": "Модель этапа → {model}",
        "msg_stage_effort": "Effort этапа → {effort}",
        "msg_stage_write_fixed": "Этап «Код» всегда включён (меняйте провайдер/модель)",
        "msg_stage_edit": "{stage} · {field}",
        "msg_stage_no_models": "Нет моделей — выберите другого провайдера",
        "model_na": "н/д (структурный)",
        "on": "ВКЛ",
        "off": "выкл",
        "wr_qwen_blurb": "Быстрый повседневный кодер",
        "wr_kimi_blurb": "Длинный контекст Kimi K3 (256k)",
        "wr_grok_blurb": "Writer-lane xAI Grok",
        "wr_agy_blurb": "Gemini Flash high через AGY",
        "wr_codex_blurb": "Bare Codex lane-writer (без host MCP/plugins)",
        "wr_auto_blurb": "Первый доступный: Kimi → Qwen → Grok → AGY",
        "done_title": "✓ Проект настроен",
        "done_lbl_path": "путь",
        "done_lbl_coder": "кодер",
        "done_lbl_model": "модель",
        "done_lbl_effort": "effort",
        "done_lbl_fast": "fast mode",
        "done_lbl_ws": "workspace",
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
