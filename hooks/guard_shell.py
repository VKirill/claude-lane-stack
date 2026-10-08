#!/usr/bin/env python3
"""PreToolUse: block destructive shell across CLIs."""
from __future__ import annotations
import ipaddress, os, re, shlex, socket, sys, threading
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_payload import (  # type: ignore
    read_payload, detect_client, tool_name, shell_command, file_path,
    is_shell_tool, is_edit_tool, emit_allow, emit_deny,
)

PM_AGENTS = {"dev-orchestrator", "frontend-orchestrator", "marketing-orchestrator"}
LANE_PILOT_PM_AGENT_TYPES = {"lane-pilot-pm"}
LANE_PILOT_HELPER_ROLES = {
    "errand", "specialist", "browser-qa", "pm-read", "pm-reader",
    "critic", "plan-critic", "code-critic", "specialist-reviewer",
    "night-reviewer", "docs", "docs-maintainer", "onboarder",
    "memory-maintainer", "project-life", "gate-triage", "council-seat",
    "rules-analyzer",
    "design-lead", "copy-lead", "seo-specialist", "tavily",
}


def agent_key(agent: object) -> str | None:
    if not isinstance(agent, str) or not agent.strip():
        return None
    return agent.strip().rsplit(":", 1)[-1]


LANE_PILOT_READ_COMMANDS = {
    "cat", "cd", "cmp", "cut", "echo", "file", "find", "grep", "head", "jq",
    "ls", "printf", "pwd", "readlink", "realpath", "rg", "sed", "sha256sum",
    "sort", "stat", "tail", "test", "true", "false", "type", "wc", "which",
    "yq",
}
LANE_PILOT_GIT_READONLY = {"status", "diff", "log", "show"}
LANE_PILOT_RUN_CONTROLLER_SUBCOMMANDS = {"run", "start", "status", "watch"}
LANE_PILOT_LANE_CTL_SUBCOMMANDS = {
    "start", "status", "tail", "events", "cancel", "retry", "fallback",
    "verify", "accept",
}
LANE_PILOT_ADOC_COMMANDS = {"adoc", "agents-doctor"}
LANE_PILOT_FORBIDDEN_SCRIPT_RUNNERS = {
    "bash", "sh", "python", "python3", "node", "nodejs",
}
PM_READ_COMMANDS = {
    "cat", "cd", "cmp", "cut", "date", "df", "du", "echo", "file", "find",
    "gitnexus", "grep", "head", "journalctl", "jq", "ls", "lsof", "pgrep",
    "printf", "ps", "pstree", "pwd", "readlink", "realpath", "rg", "sed",
    "sha256sum", "sort", "stat", "tail", "test", "true", "false", "type",
    "uniq", "wc", "which", "yq",
}
# Read-only bb CLI calls the PM may use to look around; anything that changes state stays denied.
PM_BB_READ_COMMANDS = {
    ("status",), ("guide",), ("thread", "show"), ("thread", "get"), ("thread", "log"), ("thread", "messages"),
    ("thread", "list"), ("thread", "output"), ("thread", "search"), ("thread", "wait"), ("thread", "history"),
    ("thread", "context"), ("thread", "count"),
    ("memory", "search"), ("memory", "get"), ("memory", "catalog"),
    ("project", "list"), ("project", "show"),
    # Which accounts exist and asking the owner for a missing one; values stay with the errand helper.
    ("env-catalog", "list"), ("env-catalog", "request"),
}
# Agents coordinate by messaging each other's threads; starting, changing or archiving threads stays denied.
PM_BB_MESSAGE_COMMANDS = {
    ("thread", "tell"), ("thread", "message"),
    ("thread", "queue", "create"), ("thread", "queue", "send"), ("thread", "queue", "list"),
}
# A Lane Pilot PM is the owner's own chat and ships too (owner, 2026-10-03): it may read BB state and reload or
# install plugins. Starting, stopping and archiving threads stays with Lane Pilot's tools (lane_pilot_specialist,
# lane_pilot_errand, lane_pilot_dispatch_writer), so a writer never bypasses critique and acceptance.
LANE_PILOT_BB_COMMANDS = PM_BB_READ_COMMANDS | PM_BB_MESSAGE_COMMANDS | {
    ("version",), ("memory", "catalog"), ("project", "get"),
    ("plugin", "list"), ("plugin", "logs"), ("plugin", "info"), ("plugin", "show"), ("plugin", "status"),
    ("environment", "list"), ("environment", "show"), ("environment", "get"), ("environment", "providers"),
    ("host", "list"), ("host", "show"), ("provider", "list"), ("provider", "models"), ("skill", "list"),
    ("env-catalog", "list"), ("env-catalog", "request"),
}
# Shipping a plugin is the job of that plugin's own PM: reload/install/update only from a bb-plugin-* checkout, so a
# product PM cannot reload Lane Pilot under running writers.
LANE_PILOT_BB_PLUGIN_SHIP = {("plugin", "reload"), ("plugin", "install"), ("plugin", "update")}


def _is_plugin_checkout(cwd: object) -> bool:
    return isinstance(cwd, str) and any(part.startswith("bb-plugin-") for part in Path(cwd).parts)


# The bb CLI by name, by absolute path, or through the BB_CLI variable BB sets for agents.
PM_BB_EXECUTABLES = {"bb", "$BB_CLI", "${BB_CLI}"}
# Typed control-plane CLIs the PM may run directly (not writer lifecycle).
# lane-ctl / run-controller start|watch|status stay delegated to supervisors.
PM_CONTROL_COMMANDS = {
    "agents-doctor",
    "check-owns-paths",
    "plan-critique",
    "pm_read",
    "lane-stall-check",
    "resume-project",
    "run-board",
    "run-finalize",
    "run-init",
    "run-validate",
    "wt-create",
    "wt-merge-main",
    "lane-memory",
    "memory-maintain-project",
}
# Host ops the PM may run directly (deploy / cutover / long detach).
PM_OPS_COMMANDS = {
    "lane-bg",
    "lane-exec",
    "lane-wait",
    "systemctl",
    "sleep",
}
_SUDO_VALUE_OPTS = {
    "-u", "--user", "-g", "--group", "-h", "--host", "-p", "--prompt",
    "-R", "--chroot", "-T", "--command-timeout", "-C", "--close-from",
    "-D", "--chdir",
}
_ENV_VALUE_OPTS = {
    "-u", "--unset",
    "-C", "--chdir",
    "-S", "--split-string",
}
_DOCKER_MUTATING = {"restart", "start", "stop", "kill", "pause", "unpause"}
_DOCKER_COMPOSE_OPS = {
    "config", "images", "logs", "ps", "top",
    "up", "down", "start", "stop", "restart", "pull", "build", "run",
}
# Machine receipts under a run — owned by controller/lane-ctl, not hand-edited by PM.
_PM_RUN_MACHINE_RECEIPT = re.compile(
    r"^\.agents/runs/[^/]+/"
    r"(?:"
    r"controller(?:\.json|/)|"
    r"artifacts/|"
    r"events\.jsonl|"
    r"sessions\.json"
    r")"
)
# Exception: pre-authored L1 checkers the PM must place before dispatch.
# Matches main or worktree-relative trees:
#   .agents/runs/<slug>/check.py
#   .agents/runs/<slug>/artifacts/<task_id>/check.py
#   .worktrees/<wt>/.agents/runs/<slug>/.../check.py
_PM_L1_CHECK_SCRIPT = re.compile(
    r"^(?:\.worktrees/[^/]+/)?"
    r"\.agents/runs/[^/]+/"
    r"(?:artifacts/[^/]+/)?"
    r"check\.py$"
)
_PM_TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".txt"}
# Resolved once at import time: on macOS these literal roots are themselves
# symlinks (/tmp -> /private/tmp, /var/tmp -> /private/var/tmp), while a
# `.resolve()`d target path follows the symlink too. Comparing an unresolved
# literal against a resolved target would wrongly deny allowed temp paths.
# On Linux these roots are not symlinks, so resolving them is a no-op.
_PM_TMP_ROOTS = tuple(candidate.resolve() for candidate in (Path("/tmp"), Path("/var/tmp")))
SQL_MUTATION = re.compile(
    r"\b(?:insert|update|delete|merge|create|alter|drop|truncate|grant|revoke|"
    r"comment|vacuum|reindex|cluster|refresh)\b",
    re.I,
)


_LANE_PILOT_PM_WRITES = ".agents/ (not the Lane Pilot receipts), .bb/chats/<this chat>/, docs/plans/, .env* and /tmp"


def _lane_pilot_edit_tail(path: str) -> str:
    """Where a refused Lane Pilot PM edit should go instead, by what the path is."""
    normalized = path.replace("\\", "/").lstrip("./")
    name = normalized.rsplit("/", 1)[-1]
    if name in {"PROGRESS.md", "CHANGELOG.md"}:
        return ("Lane Pilot keeps PROGRESS.md and CHANGELOG.md; the PM records decisions in .agents/decisions/ "
                "and plans in .agents/plans/.")
    if name == "LESSONS.md":
        return "Lessons are rules on the hub now: call lane_pilot_lesson (audience pm, writer or both)."
    if name == "DESIGN.md":
        return "DESIGN.md belongs to design-lead: lane_pilot_specialist with role design-lead."
    if normalized.startswith("docs/") or "/docs/" in normalized or name in {"README.md", "PROJECT.md"}:
        return ("Lane Pilot writes docs/, README.md and PROJECT.md nightly from the code and reverts other edits there; "
                "record the decision as a draft in .agents/decisions/<date>-<slug>.md.")
    return ("Product changes go through lane_pilot_dispatch_writer: Lane Pilot critiques, accepts and merges them "
            f"(the PM writes only {_LANE_PILOT_PM_WRITES}). Send this edit as a lane_pilot_dispatch_writer task "
            "(a one-line change is a fine task); never hand the owner a command to paste and never route a repository "
            "edit through an errand.")


def _deny_pm(client: str, detail: str, lane_pilot: bool = False, path: str | None = None) -> None:
    if lane_pilot and path is not None:
        emit_deny(client, f"[lane-pilot-guard] {detail}. {_lane_pilot_edit_tail(path)}")
    # A Lane Pilot PM has no run supervisor: its writers are BB threads it dispatches itself.
    tail = (
        "Product changes go through lane_pilot_dispatch_writer (then poll lane_pilot_wait_writer); "
        "Lane Pilot critiques, accepts and merges them. A browser step in the owner's Chrome goes through "
        "lane_pilot_browser; other work outside the code (consoles, mail, accounts, recordings) through lane_pilot_errand."
        if lane_pilot
        else "Keep PM work read-only/control-plane-only; delegate mutations "
        "to the run supervisor and its writer/recovery lane."
    )
    emit_deny(client, f"[lane-pilot-guard] {detail}. {tail}" if lane_pilot else f"[orchestrator-guard] {detail}. {tail}")


# Heredoc bodies fed to anything but a shell are data (a report, a script for python), not commands.
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n(.*?)(?:\n[ \t]*\2[ \t]*(?:\n|$)|$)", re.S)
_SHELL_CONSUMER = re.compile(r"(?:^|[\s;&|(/])(?:ba|z|da|k)?sh\b|\beval\b")


def _without_data_heredocs(command: str) -> str:
    def strip(match: re.Match[str]) -> str:
        line_start = command.rfind("\n", 0, match.start()) + 1
        line_end = command.find("\n", match.start())
        if _SHELL_CONSUMER.search(command[line_start : line_end if line_end >= 0 else len(command)]):
            return match.group(0)
        return match.group(0)[: match.start(3) - match.start(0)] + "\n"
    return _HEREDOC.sub(strip, command)


_CONTROL_TOKENS = {";", "&&", "||", "|", "&", "(", ")", ";;", "|&"}


def _git_args(command: str, subcommands: set[str]) -> list[list[str]]:
    """Arguments of each real `git <subcommand>` in a command; quoted text such as a commit message stays one token."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        alternatives = "|".join(sorted(subcommands))
        return [m.group(1).split() for m in re.finditer(rf"\bgit\s+(?:{alternatives})\b([^;&|\n]*)", command)]
    pushes: list[list[str]] = []
    i = 0
    while i < len(tokens) - 1:
        if Path(tokens[i]).name == "git" and tokens[i + 1] in subcommands:
            j = i + 2
            while j < len(tokens) and tokens[j] not in _CONTROL_TOKENS:
                j += 1
            pushes.append(tokens[i + 2 : j])
            i = j
        else:
            i += 1
    return pushes


def _is_env_secret_file(name: str) -> bool:
    """True for dotenv-style files the PM may write without involving writers.

    Allows placing API keys/secrets in env files so they never pass through
    coder-lane prompts. Basename only: `.env`, `.env.local`, `.env.production`, …
    Not arbitrary source (e.g. `config.ts`).
    """
    base = Path(name).name
    if base == ".env":
        return True
    # .env.local, .env.development, .env.production.local, .env.example, …
    if base.startswith(".env."):
        return True
    return False


def _pm_edit_allowed(path: str, cwd: object) -> bool:
    """PM may edit control-plane docs + dotenv files — never production source.

    Aligns with SOLO/dev-orchestrator: `.agents/**`, legacy `docs/plans/**`,
    living memory (`.agents/PROGRESS.md` / `.agents/LESSONS.md`, plus
    legacy root copies), and dotenv (`.env*`) for secrets the human trusts
    the PM with. Machine lifecycle receipts under a run (controller,
    state/report under artifacts, events, sessions) stay tool-owned.

    Exception: basename exactly ``check.py`` under a run's artifacts (or run
    root) — pre-authored L1 verification scripts required before dispatch.
    """
    if not isinstance(cwd, str) or not cwd:
        return False
    root = Path(cwd).resolve()
    requested = Path(path)
    lexical = Path(os.path.abspath(requested if requested.is_absolute() else root / requested))
    target = lexical.resolve()
    suffix = target.suffix.lower()
    if lexical.is_relative_to(root) and not target.is_relative_to(root):
        return False
    if requested.is_absolute() and any(target.is_relative_to(root) for root in _PM_TMP_ROOTS):
        return suffix in _PM_TEXT_SUFFIXES
    if not target.is_relative_to(root):
        return False
    relative = target.relative_to(root)
    normalized = relative.as_posix()
    # LESSONS.md is not kept any more: lessons are rules on the hub (lane_pilot_lesson / lane-memory lesson).
    if normalized.rsplit("/", 1)[-1] == "LESSONS.md":
        return False
    # The repository-local git exclude (main repo or a linked worktree's): the PM keeps local ignores there.
    if re.fullmatch(r"\.git/(?:worktrees/[^/]+/)?info/exclude", normalized):
        return True
    # Lane Pilot bookkeeping files are owned by Lane Pilot project-life / living memory; PM never edits them.
    if normalized.rsplit("/", 1)[-1] in {"PROGRESS.md", "CHANGELOG.md"}:
        return False
    if _is_env_secret_file(normalized):
        return True
    if normalized.startswith("docs/plans/"):
        return suffix in _PM_TEXT_SUFFIXES
    # The chat's own folder (BB project-folders): notes, commit messages, scratch files of this PM chat.
    if normalized.startswith(".bb/chats/") and "/history/" not in normalized and not normalized.endswith("/thread.json"):
        return suffix in _PM_TEXT_SUFFIXES
    # Worktree-local or main-repo L1 checkers (must be check.py only).
    if _PM_L1_CHECK_SCRIPT.fullmatch(normalized):
        return True
    if normalized.startswith(".agents/") or "/.agents/" in normalized:
        # Strip optional .worktrees/<name>/ prefix for receipt matching.
        receipt_path = normalized
        if normalized.startswith(".worktrees/"):
            parts = normalized.split("/", 2)
            receipt_path = parts[2] if len(parts) >= 3 else normalized
        if _PM_RUN_MACHINE_RECEIPT.search(receipt_path):
            return False
        # SMA corpus: records only through lane-memory. Drafts are the inbox.
        if receipt_path.startswith(".agents/memory/"):
            rest = receipt_path[len(".agents/memory/") :]
            return rest.startswith("drafts/") and suffix in _PM_TEXT_SUFFIXES
        if receipt_path.startswith(".agents/memory.local/"):
            return False
        if receipt_path.startswith(".agents/sma/"):
            return False
        if receipt_path.startswith(".cls/"):
            return False
        if receipt_path.startswith(".agents/"):
            return suffix in _PM_TEXT_SUFFIXES
    return False


def _subcommand(args: list[str], options_with_values: set[str]) -> str:
    index = 0
    while index < len(args):
        token = args[index]
        if token in options_with_values:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return ""


def _safe_psql(args: list[str]) -> bool:
    if any(token in {"-f", "--file"} for token in args):
        return False
    queries = [
        args[index + 1]
        for index, token in enumerate(args[:-1])
        if token in {"-c", "--command"}
    ]
    return bool(queries) and all(not SQL_MUTATION.search(query) for query in queries)


# Folders whose contents a tool regenerates: deleting them for good loses nothing.
_DISPOSABLE_SEGMENTS = {
    "node_modules", "dist", "build", ".next", ".nuxt", ".output", ".cache", "coverage", ".turbo", ".vite",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "tmp", ".tmp",
}
_DISPOSABLE_ROOTS = ("/tmp/", "/private/tmp/", "/var/tmp/", "/var/folders/", "/dev/null")
_TRASH_HINT = (
    "move it to the Trash instead: ~/.agents/bin/agent-trash <path>... (takes rm's -r/-f; on servers the Trash "
    "keeps it 7 days). Build output, node_modules, caches and /tmp can still be removed with rm."
)


def _disposable_path(path: str) -> bool:
    if path.startswith(("$TMPDIR", "${TMPDIR")) or any(path.startswith(root) for root in _DISPOSABLE_ROOTS):
        return True
    variable = re.match(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)", path)
    if variable and re.search(r"te?mp", variable.group(1), re.I):  # a mktemp folder: tmp=$(mktemp -d); rm -rf "$tmp"
        return True
    return any(part in _DISPOSABLE_SEGMENTS for part in path.replace("\\", "/").split("/"))


def _delete_targets(args: list[str]) -> list[str] | None:
    """What a real delete command removes, or None if it is not one. Unknown targets (xargs) come back as ["?"]."""
    while args and args[0] in {"sudo", "env", "command", "nice", "nohup", "time"}:
        inner = _unwrap_sudo_args(args[1:]) if args[0] == "sudo" else _unwrap_env_args(args[1:]) if args[0] == "env" else args[1:]
        if not inner:
            return None
        args = inner
    if not args:
        return None
    name = Path(args[0]).name
    if name in {"rm", "unlink", "shred"}:
        operands, after_dashdash = [], False
        for token in args[1:]:
            if after_dashdash or not token.startswith("-") or token == "-":
                operands.append(token)
            elif token == "--":
                after_dashdash = True
        return operands or ["?"]
    if name == "find" and "-delete" in args:
        roots = []
        for token in args[1:]:
            if token.startswith("-") or token in {"(", "!"}:
                break
            roots.append(token)
        return roots or ["."]
    if name == "xargs":
        rest = [token for token in args[1:] if not token.startswith("-")]
        if rest and Path(rest[0]).name in {"rm", "unlink", "shred"}:
            return ["?"]
    if name in {"sh", "bash", "zsh"} and "-c" in args:
        index = args.index("-c")
        if index + 1 < len(args):
            for nested in _delete_commands(args[index + 1]):
                return nested
    return None


def _delete_commands(command: str) -> list[list[str]]:
    """Targets of every real rm/unlink/shred/find -delete in a command; text inside quotes (a grep pattern) is not one."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return [["?"]] if re.search(r"(?:^|[;&|(]\s*)(?:sudo\s+)?(?:rm|unlink|shred)\s", command) else []
    found: list[list[str]] = []
    segment: list[str] = []
    for token in [*tokens, ";"]:
        if token in _CONTROL_TOKENS:
            targets = _delete_targets(segment)
            if targets is not None:
                found.append(targets)
            segment = []
        else:
            segment.append(token)
    return found


def _permanent_delete_error(command: str) -> str | None:
    for targets in _delete_commands(command):
        kept = [target for target in targets if not _disposable_path(target)]
        if kept:
            shown = "files piped through xargs" if kept == ["?"] else " ".join(kept[:3]) + (" ..." if len(kept) > 3 else "")
            return f"[agent-guard] Deleting {shown} for good is blocked: {_TRASH_HINT}"
    return None


def _unwrap_sudo_args(args: list[str]) -> list[str] | None:
    """Return inner argv after sudo flags, or None if sudo has no command."""
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--":
            return args[index + 1 :]
        if token in _SUDO_VALUE_OPTS:
            index += 2
            continue
        if "=" in token and token.startswith("-"):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        return args[index:]
    return None


def _unwrap_env_args(args: list[str]) -> list[str] | None:
    """Strip env(1) flags and NAME=VALUE assignments; return the inner command."""
    index = 0
    while index < len(args):
        token = args[index]
        if token in {"--", "-"}:
            rest = args[index + 1 :]
            return rest or None
        if token in _ENV_VALUE_OPTS:
            if index + 1 >= len(args):
                return None
            index += 2
            continue
        if token.startswith("--unset=") or token.startswith("--chdir="):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token):
            index += 1
            continue
        return args[index:]
    return None


def _pm_bb_error(args: list[str]) -> str | None:
    words = [arg for arg in args if not arg.startswith("-")]
    if any(arg in {"--help", "-h", "--version", "-V"} for arg in args):
        return None
    allowed = PM_BB_READ_COMMANDS | PM_BB_MESSAGE_COMMANDS
    if any(tuple(words[:size]) in allowed for size in (1, 2, 3)):
        return None
    return "bb command neither reads nor messages a thread; delegate it"


def _pm_segment_error(segment: list[str]) -> str | None:
    if not segment:
        return None
    executable = Path(segment[0]).name
    args = segment[1:]

    # sudo / nohup: unwrap and re-check the inner command.
    if executable == "sudo":
        inner = _unwrap_sudo_args(args)
        if not inner:
            return "sudo requires a command"
        return _pm_segment_error(inner)
    if executable == "nohup":
        if not args:
            return "nohup requires a command"
        return _pm_segment_error(args)
    if executable == "env":
        inner = _unwrap_env_args(args)
        if not inner:
            return "env requires a command"
        return _pm_segment_error(inner)
    # A shell script run by its path (./scripts/deploy.sh) is the same as `bash scripts/deploy.sh`,
    # which the PM may already run: judge them alike instead of by the bare command name.
    if "/" in segment[0] and segment[0].endswith(".sh"):
        return None
    if executable in {"bash", "sh"}:
        # Script path: bash /tmp/foo.sh [args…]
        # -c: only when the inline string itself is PM-safe.
        index = 0
        while index < len(args) and args[index].startswith("-"):
            if args[index] in {"-c", "-lc"}:
                break
            if args[index] in {"--rcfile", "--init-file"} and index + 1 < len(args):
                index += 2
                continue
            index += 1
        if index < len(args) and args[index] in {"-c", "-lc"}:
            if index + 1 >= len(args):
                return "bash -c requires a command string"
            return _pm_shell_error(args[index + 1])
        if index >= len(args):
            return "bash requires a script path or -c"
        return None

    if executable == "export":
        if args and all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", arg) for arg in args):
            return None
        return "unsupported export command"
    if executable in PM_CONTROL_COMMANDS or executable in PM_OPS_COMMANDS:
        return None
    if executable in PM_BB_EXECUTABLES:
        return _pm_bb_error(args)
    if executable in PM_READ_COMMANDS:
        if executable == "find" and any(
            arg in {
                "-delete", "-exec", "-execdir", "-fls", "-fprint", "-fprint0",
                "-ok", "-okdir",
            }
            for arg in args
        ):
            return "mutating find action is forbidden"
        if executable == "sed" and any(
            arg == "-i"
            or arg.startswith("-i")
            or arg == "--in-place"
            or arg.startswith("--in-place=")
            for arg in args
        ):
            return "in-place sed is forbidden"
        if executable == "sort" and any(
            arg == "-o" or arg.startswith("--output") for arg in args
        ):
            return "sort output file is forbidden"
        return None
    if executable == "git":
        for index, token in enumerate(args[:-1]):
            if token == "-c" and "hook" in args[index + 1].split("=", 1)[0].lower():
                return "git hook override is forbidden"
        command = _subcommand(args, {"-C", "-c", "--git-dir", "--work-tree"})
        allowed = {
            "add", "branch", "commit", "describe", "diff", "fetch", "grep", "log",
            "ls-files", "merge", "push", "remote", "rev-parse", "show", "status",
        }
        if command not in allowed:
            return f"git {command or '<missing>'} is not PM-safe"
        command_index = args.index(command)
        command_args = args[command_index + 1 :]
        if command == "branch":
            safe_flags = {"-a", "-r", "-v", "-vv", "--list", "--show-current"}
            if any(arg not in safe_flags for arg in command_args):
                return "git branch mutation is forbidden"
        if command == "remote" and command_args and command_args[0] not in {
            "-v", "get-url", "show",
        }:
            return "git remote mutation is forbidden"
        return None
    if executable in {"npm", "pnpm", "yarn", "bun"}:
        command = _subcommand(
            args,
            {
                "-C", "--cwd", "--dir", "--filter", "--prefix", "-w", "--workspace",
            },
        )
        if command in {"test", "t"}:
            return None
        if command == "run":
            command_index = args.index(command)
            script = args[command_index + 1] if command_index + 1 < len(args) else ""
            if re.fullmatch(
                r"(?:build|check|lint|test|typecheck|verify)(?::[A-Za-z0-9_.-]+)*",
                script,
            ):
                return None
        return f"{executable} {command or '<missing>'} is not a verification command"
    if executable == "cargo":
        command = _subcommand(args, set())
        if command == "fmt":
            return None if "--check" in args else "cargo fmt may mutate source"
        return None if command in {"build", "check", "clippy", "test"} else (
            f"cargo {command or '<missing>'} is not a verification command"
        )
    if executable == "go":
        command = _subcommand(args, set())
        return None if command in {"build", "test", "vet"} else (
            f"go {command or '<missing>'} is not a verification command"
        )
    if executable == "ruff" and "--fix" in args:
        return "ruff --fix is forbidden"
    if executable in {"pytest", "ruff", "mypy"}:
        return None
    if executable in {"python", "python3"}:
        if len(args) >= 2 and args[0] == "-m" and args[1] in {
            "compileall", "mypy", "pytest", "ruff", "unittest",
        }:
            return None
        return "direct Python execution is forbidden"
    if executable in {"make", "just"}:
        targets = [arg for arg in args if not arg.startswith("-")]
        safe = {"check", "lint", "test", "tests", "typecheck", "verify"}
        return None if targets and all(target in safe for target in targets) else (
            f"{executable} target is not a verification target"
        )
    if executable == "docker":
        command = _subcommand(args, {"--context", "-H", "--host"})
        if command in {
            "images", "inspect", "logs", "ps", "stats", "top", "version",
            *_DOCKER_MUTATING,
        }:
            return None
        if command == "compose":
            offset = args.index("compose") + 1
            compose = _subcommand(
                args[offset:],
                {"-f", "--file", "-p", "--project-name", "--profile"},
            )
            return None if compose in _DOCKER_COMPOSE_OPS else (
                f"docker compose {compose or '<missing>'} is not PM-safe"
            )
        if command == "exec":
            offset = args.index("exec") + 1
            tail = args[offset:]
            while tail and tail[0].startswith("-"):
                tail = tail[1:]
            if len(tail) == 2 and tail[1] == "env":
                return None
            if len(tail) >= 2 and Path(tail[1]).name == "psql":
                return None if _safe_psql(tail[2:]) else "database mutation is forbidden"
            # ops-expand: docker exec <ctr> <cmd…> for deploys / probes
            if len(tail) >= 2:
                return _pm_segment_error(tail[1:])
        return f"docker {command or '<missing>'} is not PM-safe"
    if executable == "psql":
        return None if _safe_psql(args) else "database mutation is forbidden"
    if executable == "curl":
        if any(
            re.match(r"^-(?:d|F|o|T).*$", arg)
            or re.match(
                r"^--(?:data|data-ascii|data-binary|data-raw|form|json|output|upload-file)(?:=|$)",
                arg,
            )
            for arg in args
        ):
            return "mutating curl options are forbidden"
        method = None
        for index, arg in enumerate(args):
            if arg in {"-X", "--request"} and index + 1 < len(args):
                method = args[index + 1]
            elif arg.startswith("-X") and len(arg) > 2:
                method = arg[2:]
            elif arg.startswith("--request="):
                method = arg.split("=", 1)[1]
        if method is not None and method.upper() not in {"GET", "HEAD"}:
            return "non-read-only curl method is forbidden"
        return None
    return f"command {segment[0]!r} is not allowlisted for project management"


def _pm_redirect_target_ok(path: str) -> bool:
    """PM may only redirect to /tmp (cutover/deploy logs), not source trees."""
    if not path or path.isdigit():
        return True  # fd like 1 in 2>&1
    if path == "/dev/null":
        return True  # discarding output writes nothing
    try:
        resolved = Path(path).expanduser()
        # lexical check first (path may not exist yet)
        parts = resolved.parts
        if parts[:1] == ("/",) and len(parts) >= 2 and parts[1] == "tmp":
            return True
        if parts[:1] == ("/tmp",) or (len(parts) >= 1 and parts[0] == "/tmp"):
            return True
    except (OSError, ValueError):
        return False
    text = path.replace("\\", "/")
    return text == "/tmp" or text.startswith("/tmp/")


def _lane_pilot_redirect_target_ok(path: str, cwd: object) -> bool:
    """Allow output only under a real temp root, after .. and symlink resolution."""
    if not path or path.isdigit():
        return True
    if not isinstance(cwd, str) or not cwd:
        return False
    try:
        requested = Path(path).expanduser()
        absolute = requested if requested.is_absolute() else Path(cwd) / requested
        target = absolute.resolve(strict=False)
        return any(target.is_relative_to(root) for root in _PM_TMP_ROOTS)
    except (OSError, ValueError):
        return False


def _lane_pilot_flag_present(args: list[str], names: set[str]) -> bool:
    return any(token in names or any(token.startswith(f"{name}=") for name in names) for token in args)


def _lane_pilot_segment_error(segment: list[str]) -> str | None:
    if not segment:
        return None
    executable = Path(segment[0]).name
    args = segment[1:]
    if executable in LANE_PILOT_FORBIDDEN_SCRIPT_RUNNERS:
        return f"script runner {executable!r} is forbidden for lane-pilot-pm"
    if executable == "sudo":
        inner = _unwrap_sudo_args(args)
        if not inner:
            return "sudo requires a command"
        return _lane_pilot_segment_error(inner)
    if executable == "nohup":
        return "nohup is forbidden for lane-pilot-pm"
    if executable in LANE_PILOT_ADOC_COMMANDS:
        if not args:
            return f"{executable} requires an explicit report-only flag"
        allowed_flags = {"--json", "--no-tui"}
        if any(token == "setup" for token in args):
            return f"{executable} setup is forbidden"
        if any(token.startswith("-") and token not in allowed_flags for token in args):
            return f"unknown or mutating {executable} flag is forbidden"
        if not any(token in allowed_flags for token in args):
            return f"{executable} requires --json or --no-tui"
        return None
    if executable == "run-controller":
        command = _subcommand(args, set())
        return None if command in LANE_PILOT_RUN_CONTROLLER_SUBCOMMANDS else (
            f"run-controller {command or '<missing>'} is not allowlisted"
        )
    if executable == "lane-ctl":
        command = _subcommand(args, set())
        return None if command in LANE_PILOT_LANE_CTL_SUBCOMMANDS else (
            f"lane-ctl {command or '<missing>'} is not allowlisted"
        )
    if executable == "git":
        forbidden = {"-c", "--config", "-o", "--output", "--git-dir", "--work-tree"}
        if _lane_pilot_flag_present(args, forbidden):
            return "git output/configuration flags are forbidden"
        command = _subcommand(args, {"-C"})
        if command not in LANE_PILOT_GIT_READONLY:
            return f"git {command or '<missing>'} is not read-only"
        return None
    if executable in LANE_PILOT_READ_COMMANDS:
        if executable == "find" and any(
            token in {"-delete", "-exec", "-execdir", "-fls", "-fprint", "-fprint0", "-ok", "-okdir"}
            for token in args
        ):
            return "mutating find action is forbidden"
        if executable == "sed" and _lane_pilot_flag_present(args, {"-i", "--in-place"}):
            return "in-place sed is forbidden"
        if executable == "sort" and _lane_pilot_flag_present(args, {"-o", "--output"}):
            return "sort output file is forbidden"
        if executable == "yq" and _lane_pilot_flag_present(args, {"-i", "--inplace", "--in-place"}):
            return "in-place yq is forbidden"
        return None
    if executable in PM_BB_EXECUTABLES:
        return _pm_bb_error(args)
    return f"command {segment[0]!r} is not allowlisted for lane-pilot-pm"


def _lane_pilot_bb_command_error(args: list[str], cwd: object = None) -> str | None:
    words = [arg for arg in args if not arg.startswith("-")]
    if any(arg in {"--help", "-h", "--version", "-V"} for arg in args):
        return None
    if any(tuple(words[:size]) in LANE_PILOT_BB_COMMANDS for size in (1, 2, 3)):
        return None
    if tuple(words[:2]) in LANE_PILOT_BB_PLUGIN_SHIP:
        return None if _is_plugin_checkout(cwd) else f"bb {' '.join(words[:2])} runs only from a bb-plugin-* checkout (that plugin's own PM ships it)"
    return f"bb {' '.join(words[:2]) or '(none)'} is not open to the PM"


def _lane_pilot_bb_error(command: str, cwd: object = None) -> str | None:
    """bb in a Lane Pilot PM command: reading threads and messaging them, nothing that spawns, edits or reloads."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return None
    segment: list[str] = []
    for token in [*tokens, ";"]:
        if token in {"&&", "||", ";", "|", "&"}:
            if segment and (segment[0] in PM_BB_EXECUTABLES or Path(segment[0]).name == "bb"):
                error = _lane_pilot_bb_command_error(segment[1:], cwd)
                if error:
                    return error
            segment = []
        else:
            segment.append(token)
    return None


def _lane_pilot_shell_write_error(command: str, cwd: object) -> str | None:
    """A Lane Pilot PM command that edits a project file in place: sed/perl -i, tee, or a redirect into the checkout.
    Files the PM may write (_pm_edit_allowed), paths outside the checkout and /dev/null pass; scripts are not judged."""
    if not isinstance(cwd, str) or not cwd:
        return None
    try:
        lexer = shlex.shlex(_without_data_heredocs(command), posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return None
    root = Path(cwd).resolve()

    def project_file(target: str) -> bool:
        if not target or target.startswith("&") or target == "/dev/null":
            return False
        path = Path(target if os.path.isabs(target) else os.path.join(cwd, target))
        try:
            inside = path.resolve().is_relative_to(root)
        except (OSError, RuntimeError):
            return False
        return inside and not _pm_edit_allowed(target, cwd)

    for index, token in enumerate(tokens):
        if token in {">", ">>"} and index + 1 < len(tokens) and project_file(tokens[index + 1]):
            return f"redirect into {tokens[index + 1]}"
    segment: list[str] = []
    for token in [*tokens, ";"]:
        if token in {"&&", "||", ";", "|", "&"}:
            if segment:
                head = Path(segment[0]).name
                files = []
                skip = False
                for arg in segment[1:]:
                    if skip:
                        skip = False
                        continue
                    if arg in {"-e", "-f", "--expression", "--file"}:
                        skip = True
                        continue
                    if not arg.startswith("-"):
                        files.append(arg)
                in_place = head in {"sed", "gsed", "perl"} and any(arg == "-i" or arg.startswith("-i") or arg.startswith("--in-place") or (head == "perl" and "i" in arg.lstrip("-") and arg.startswith("-")) for arg in segment[1:])
                # sed/perl take their script as the first operand unless it comes with -e.
                if in_place and "-e" not in segment[1:]:
                    files = files[1:]
                if (in_place or head == "tee"):
                    for arg in files:
                        if project_file(arg):
                            return f"{head} {'-i ' if in_place else ''}{arg}".replace("  ", " ")
            segment = []
        else:
            segment.append(token)
    return None


def _lane_pilot_shell_error(command: str, cwd: object) -> str | None:
    if "\0" in command or "\n" in command or "$(" in command or "`" in command:
        return "multiline shell or command substitution is forbidden"
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError as exc:
        return f"shell command cannot be parsed: {exc}"
    segments: list[list[str]] = [[]]
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {"&&", "||", ";", "|"}:
            segments.append([])
            index += 1
            continue
        if token == "&":
            return "background jobs are forbidden"
        if token in {">", ">>", "<", "&>", ">&"} or re.fullmatch(r"\d>+", token):
            index += 1
            if index < len(tokens) and tokens[index] not in {
                "&&", "||", ";", "|", "&", ">", ">>", "<", "&>", ">&",
            } and not re.fullmatch(r"\d>+", tokens[index]):
                target = tokens[index]
                if not _lane_pilot_redirect_target_ok(target, cwd):
                    return f"redirect target {target!r} is outside a real temp root"
                index += 1
            continue
        if token.isdigit() and index + 2 < len(tokens) and tokens[index + 1] == ">&":
            index += 3
            continue
        if any(char in token for char in "<>"):
            return f"unsupported redirection {token!r}"
        segments[-1].append(token)
        index += 1
    for segment in segments:
        error = _lane_pilot_segment_error(segment)
        if error:
            return error
    return None


def _pm_shell_error(command: str) -> str | None:
    if "\0" in command or "\n" in command or "$(" in command or "`" in command:
        return "multiline shell or command substitution is forbidden"
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError as exc:
        return f"shell command cannot be parsed: {exc}"
    segments: list[list[str]] = [[]]
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {"&&", "||", ";", "|"}:
            segments.append([])
            index += 1
            continue
        # Background job marker — allowed for PM ops (nohup … &).
        if token == "&":
            index += 1
            continue
        # Redirection: >, >>, 2>, &>, 2>&1 (possibly split as 2, >&, 1).
        if token in {">", ">>", "<", "&>", ">&"} or re.fullmatch(r"\d>+", token):
            index += 1
            if index < len(tokens) and tokens[index] not in {
                "&&", "||", ";", "|", "&", ">", ">>", "<", "&>", ">&",
            } and not re.fullmatch(r"\d>+", tokens[index]):
                target = tokens[index]
                if not _pm_redirect_target_ok(target):
                    return f"redirect target {target!r} is outside /tmp"
                index += 1
            continue
        if token.isdigit() and index + 2 < len(tokens) and tokens[index + 1] == ">&":
            index += 3
            continue
        if any(char in token for char in "<>"):
            return f"unsupported redirection {token!r}"
        segments[-1].append(token)
        index += 1
    for segment in segments:
        error = _pm_segment_error(segment)
        if error:
            return error
    return None


def _lane_pilot_shell_checks(client: str, cmd: str, payload: dict) -> None:
    """The Lane Pilot PM's own shell rules, the same for the native BB PM (dev-orchestrator + LANE_PILOT_AGENT_TYPE)
    and lane-pilot-pm: bb beyond its list, and shell edits of project files."""
    error = _lane_pilot_bb_error(cmd, payload.get("cwd") or payload.get("workspaceRoot"))
    if error:
        emit_deny(client, f"[lane-pilot-guard] {error}. The PM's bb reads BB state (thread, memory, project, plugin, environment, "
                  "host, provider and skill listings, env-catalog list/request), messages threads, and in a bb-plugin-* checkout "
                  "reloads, installs or updates plugins. A secret value: the PM does not read one; name the account in lane_pilot_errand accounts or in a check secrets. A helper thread: lane_pilot_specialist or "
                  "lane_pilot_errand. A browser step: lane_pilot_browser. Product changes: lane_pilot_dispatch_writer.")
    edit = _lane_pilot_shell_write_error(cmd, payload.get("cwd") or payload.get("workspaceRoot"))
    if edit:
        emit_deny(client, f"[lane-pilot-guard] {edit}: shell edits of project files skip plan critique, code critique and acceptance. "
                  f"{_lane_pilot_edit_tail(edit.rsplit(' ', 1)[-1])} Deploy, build and test scripts are fine.")


HELPER_DENIAL = "Helpers do not change the repository; report what should change and the PM dispatches a writer task."


def is_helper_role(key: str | None) -> bool:
    if not key:
        return False
    if key in LANE_PILOT_HELPER_ROLES:
        return True
    if key.startswith("specialist:"):
        return True
    return False


def _helper_edit_allowed(path: str, cwd: object, role: str) -> bool:
    """Helper write permissions: /tmp, its own .bb/chats/<thread>/, and (.agents/ for specialists only)."""
    if not isinstance(cwd, str) or not cwd:
        return False
    root = Path(cwd).resolve()
    requested = Path(path)
    lexical = Path(os.path.abspath(requested if requested.is_absolute() else root / requested))
    target = lexical.resolve()
    suffix = target.suffix.lower()
    if requested.is_absolute() and any(target.is_relative_to(r) for r in _PM_TMP_ROOTS):
        return True
    if not target.is_relative_to(root):
        return False
    relative = target.relative_to(root)
    normalized = relative.as_posix()
    if normalized.startswith(".bb/chats/") and "/history/" not in normalized and not normalized.endswith("/thread.json"):
        return True
    is_specialist = role == "specialist" or role.startswith("specialist:") or role in {"design-lead", "copy-lead", "seo-specialist", "tavily"}
    if is_specialist:
        if normalized == ".agents" or normalized.startswith(".agents/"):
            return True
    return False


def _helper_shell_write_error(command: str, cwd: object, role: str) -> str | None:
    if not isinstance(cwd, str) or not cwd:
        return None
    no_heredocs = _without_data_heredocs(command)
    try:
        lexer = shlex.shlex(no_heredocs, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return None
    root = Path(cwd).resolve()

    def project_file(target: str) -> bool:
        if not target or target.startswith("&") or target == "/dev/null":
            return False
        path = Path(target if os.path.isabs(target) else os.path.join(cwd, target))
        try:
            inside = path.resolve().is_relative_to(root)
        except (OSError, RuntimeError):
            return False
        return inside and not _helper_edit_allowed(target, cwd, role)

    for index, token in enumerate(tokens):
        if token in {">", ">>"} and index + 1 < len(tokens) and project_file(tokens[index + 1]):
            return f"redirect into {tokens[index + 1]}"

    segment: list[str] = []
    for token in [*tokens, ";"]:
        if token in {"&&", "||", ";", "|", "&"}:
            if segment:
                head = Path(segment[0]).name
                files = []
                skip = False
                for arg in segment[1:]:
                    if skip:
                        skip = False
                        continue
                    if arg in {"-e", "-f", "--expression", "--file", "-t", "--target-directory"}:
                        skip = True
                        continue
                    if not arg.startswith("-"):
                        files.append(arg)
                in_place = head in {"sed", "gsed", "perl"} and any(
                    arg == "-i" or arg.startswith("-i") or arg.startswith("--in-place") or
                    (head == "perl" and "i" in arg.lstrip("-") and arg.startswith("-"))
                    for arg in segment[1:]
                )
                if in_place and "-e" not in segment[1:]:
                    files = files[1:]
                if in_place or head == "tee":
                    for arg in files:
                        if project_file(arg):
                            return f"{head} {arg}"
                if head in {"cp", "mv"}:
                    # If target is inside project
                    if files and project_file(files[-1]):
                        return f"{head} into {files[-1]}"
            segment = []
        else:
            segment.append(token)
    return None


def _helper_shell_checks(client: str, cmd: str, payload: dict, role: str) -> None:
    no_heredocs = _without_data_heredocs(cmd)
    git_mutations = _git_args(no_heredocs, {"add", "commit", "push", "merge", "checkout", "restore", "reset", "rebase", "tag", "branch"})
    if git_mutations:
        emit_deny(client, f"[helper-guard] {HELPER_DENIAL}")

    cwd = payload.get("cwd") or payload.get("workspaceRoot")
    write_err = _helper_shell_write_error(cmd, cwd, role)
    if write_err:
        emit_deny(client, f"[helper-guard] {HELPER_DENIAL}")


LANE_PILOT_WRITER_ROLES = {"writer", "emergency-writer"}

# The bb CLI by name (bb, bb-app, bb.js, npm names with a version), whatever the path or runner in front of it.
_BB_NAME = re.compile(r"^(?:@[\w.-]+/)?bb(?:-app|-cli)?(?:\.[cm]?js)?(?:@[\w.-]+)?$")
_ENV_CATALOG_WRITES = {"set", "delete", "export", "import-machine-env"}
_LANE_PILOT_PLUGIN_IDS = {"lane-pilot", "bb-plugin-lane-pilot"}
_LANE_PILOT_RPC_WRITES = re.compile(
    r"^(?:(?:save|reset|set)_.*|stack_install|stack_connect|stack_rollback|native_install_start|decide_rule_proposal"
    r"|rule_set_audience|memory_record_delete|prepare_native_session"
    # The schedule board: what the hub runs on its own, with the owner's accounts and machines. An agent asks through lane_pilot_schedule.
    r"|schedule_(?:upsert|delete|pause|resume|run_now|cancel_run)"
    # The owner's anamnesis: one RPC for every op (list with sensitive records, edit, forget all), so the whole method is the owner's.
    r"|anamnesis)$"
)
_LANE_PILOT_CLI_WRITES = {"configure", "budget", "host-run-cli", "host-install", "host-rollback", "host-connect-opencode", "host-import-config"}
# `bb lane-pilot schedule <sub>`: listing, showing and the history are reads; the rest changes or starts scheduled work.
_LANE_PILOT_SCHEDULE_WRITES = {"create", "update", "delete", "pause", "resume", "run-now", "cancel-run"}
# `bb lane-pilot anamnesis <sub>`: the PM reads (status, list, show, whoami, card, review ...); these change the owner's records. `sources --set`,
# `config --authors/--roots` and `load --run` too (see _anamnesis_error). A non-PM agent (strict) gets no subcommand at all: the server refuses
# them as well (anamnesis/wiring.ts deny()).
_ANAMNESIS_WRITES = {"add", "edit", "confirm", "reject", "forget"}
_SECRET_CLI_WRAPPERS = {
    "sudo", "doas", "nohup", "env", "command", "exec", "time", "nice", "ionice", "stdbuf", "timeout", "xargs", "builtin", "setsid", "unbuffer",
}
# Options of a wrapper that take a value as the next word (`sudo -u root bb ...`, `timeout -s KILL 5 bb ...`, `exec -a x bb ...`): the value is not the command.
_WRAPPER_VALUE_OPTS = {
    "sudo": _SUDO_VALUE_OPTS, "doas": {"-u", "-C"}, "env": _ENV_VALUE_OPTS, "timeout": {"-s", "--signal", "-k", "--kill-after"}, "exec": {"-a"},
    "nice": {"-n", "--adjustment"}, "ionice": {"-c", "-n", "-p", "-P", "-u"}, "stdbuf": {"-i", "-o", "-e"}, "time": {"-f", "-o"},
    "xargs": {"-I", "-n", "-P", "-L", "-s", "-d", "-E", "-a", "-l", "--max-args", "--max-procs", "--delimiter", "--arg-file"},
}
_SECRET_CLI_RUNNERS = {"npx", "pnpx", "bunx", "npm", "pnpm", "yarn", "bun", "node", "nodejs", "deno", "tsx", "ts-node"}
_SECRET_CLI_SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "ash", "fish"}
# bb subcommands that change or expose the plugin itself (settings, token, state): only the plugin's own PM ships it (reload/install/update stay
# the PM's, see LANE_PILOT_BB_PLUGIN_SHIP); a writer or helper has no use for them (audit 2026-10-08 r3, P0-2).
_BB_PLUGIN_ADMIN = {"config", "token", "disable", "enable", "reload", "remove", "safe-mode"}
# The hub and the machines behind it: a writer or helper never needs a shell there (it has `bb`, and the hub's data.db and master.key sit under one user).
_HUB_NAMES = {"ovh-main", "ovh-vps", "vechkasov-ovh", "selfystudio-work", "claude-dev-key", "rescue-vps"}
# 10.8.0.1 (the WireGuard address of the hub) and 54.37.129.153 (its public address) as 32-bit numbers.
_HUB_ADDRESSES = {(10 << 24) | (8 << 16) | 1, (54 << 24) | (37 << 16) | (129 << 8) | 153}
_DNS_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$")
_DNS_TIMEOUT = 1.5
_DNS_LOOKUPS = 6


def _ipv4_number(text: str) -> int | None:
    """An IPv4 address in any notation inet_aton reads (a.b.c.d, a.b.c, a.b, a; each part decimal, 0x hex or 0 octal) as a 32-bit number."""
    parts = text.split(".")
    if not 1 <= len(parts) <= 4:
        return None
    numbers: list[int] = []
    for part in parts:
        if re.fullmatch(r"0[xX][0-9a-fA-F]*", part):
            numbers.append(int(part[2:] or "0", 16))
        elif re.fullmatch(r"0[0-7]*", part):
            numbers.append(int(part or "0", 8))
        elif re.fullmatch(r"[1-9][0-9]*", part):
            numbers.append(int(part))
        else:
            return None
    *head, last = numbers
    if any(number > 255 for number in head) or last >= 256 ** (4 - len(head)):
        return None
    value = last
    for position, number in enumerate(head):
        value |= number << (24 - 8 * position)
    return value


def _address_number(text: str) -> int | None:
    """The IPv4 number of an address in any notation, also one inside an IPv6 address: ::ffff:a.b.c.d, ::ffff:xxxx:xxxx, the long forms, ::a.b.c.d, 64:ff9b::/96."""
    if ":" not in text:
        return _ipv4_number(text)
    try:
        address = ipaddress.IPv6Address(text.split("%", 1)[0])
    except ValueError:
        return None
    if address.ipv4_mapped is not None:
        return int(address.ipv4_mapped)
    packed = address.packed
    if packed[:12] == bytes(12) or packed[:12] == bytes.fromhex("0064ff9b0000000000000000"):
        return int.from_bytes(packed[12:], "big")
    return None


def _is_hub_literal(candidate: str) -> bool:
    return candidate in _HUB_NAMES or _address_number(candidate) in _HUB_ADDRESSES


def _ssh_config_hostnames() -> dict[str, str]:
    """Alias -> HostName from ~/.ssh/config (plain Host lines; wildcards and Include are not followed)."""
    table: dict[str, str] = {}
    try:
        lines = (Path(os.path.expanduser("~")) / ".ssh" / "config").read_text(errors="replace").splitlines()
    except OSError:
        return table
    aliases: list[str] = []
    for line in lines:
        match = re.match(r"\s*(Host|HostName)\s*[=\s]\s*(.+?)\s*$", line, re.I)
        if not match:
            continue
        if match.group(1).lower() == "host":
            aliases = [name.lower() for name in match.group(2).split() if not any(ch in name for ch in "*?!")]
        else:
            for alias in aliases:
                table.setdefault(alias, match.group(2).split()[0].lower())
    return table


def _resolves_to_hub(name: str) -> bool:
    """The name resolves (DNS or hosts file) to an address of the hub. It gives up after a moment: a name that does not answer in time is not refused."""
    found: list[bool] = []

    def lookup() -> None:
        try:
            infos = socket.getaddrinfo(name, None, type=socket.SOCK_STREAM)
            found.append(any(_address_number(str(info[4][0])) in _HUB_ADDRESSES for info in infos))
        except (OSError, UnicodeError):
            found.append(False)

    worker = threading.Thread(target=lookup, daemon=True)
    worker.start()
    worker.join(_DNS_TIMEOUT)
    return bool(found and found[0])


def _host_candidates(word: str) -> list[str]:
    """The host-looking pieces of one argument: user@host, host:path, ssh://user@host:port/, [v6]:path, -oHostName=host, ProxyJump a,b."""
    pieces = re.findall(r"\[([^\]]+)\]", word)
    for chunk in re.split(r"[=,]", word):
        chunk = re.sub(r"^[A-Za-z][A-Za-z0-9+.-]*://", "", chunk).split("/", 1)[0].rsplit("@", 1)[-1].strip("[]")
        pieces.append(chunk if chunk.count(":") >= 2 else chunk.split(":", 1)[0])
    return [piece.lower().rstrip(".") for piece in pieces if piece]


def _hub_target(args: list[str]) -> bool:
    """Does an ssh/scp/sftp/rsync command line reach the hub: by a name of it, by its address in any notation (10.8.1, 0x0a080001, 168296449,
    012.010.0.1, ::ffff:10.8.0.1, ::ffff:a08:1), by an alias of ~/.ssh/config whose HostName is one of those, or by a name that resolves to it."""
    words: list[str] = []
    for arg in args:
        words.append(arg)
        words.extend(piece for piece in re.split(r"[\s'\"]+", arg) if piece and piece != arg)  # a hop inside a quoted remote command
    candidates = [candidate for word in words for candidate in _host_candidates(word)]
    if any(_is_hub_literal(candidate) for candidate in candidates):
        return True
    aliases = _ssh_config_hostnames()
    if any(candidate in aliases and _is_hub_literal(aliases[candidate]) for candidate in candidates):
        return True
    names: list[str] = []
    for candidate in candidates:
        name = aliases.get(candidate, candidate)
        if _DNS_NAME.match(name) and _address_number(name) is None and not os.path.exists(name) and name not in names:
            names.append(name)
    return any(_resolves_to_hub(name) for name in names[:_DNS_LOOKUPS])
_REMOTE_SHELLS = {"ssh", "scp", "sftp", "rsync", "mosh", "autossh"}
# A script handed to a shell as base64 hides what it runs from every check here.
_BASE64_TO_SHELL = re.compile(
    r"\bbase64\b[^;&\n]*\|\s*(?:(?:env|sudo|exec)\s+)?(?:\S*/)?(?:ba|z|da|k)?sh\b"
    r"|\b(?:eval|source|(?:ba|z|da|k)?sh)\b[^;&|\n]*(?:\$\(|<\(|`)[^;&\n]*\bbase64\b"
)
_SECRET_CLI_TEXT = re.compile(
    r"\benv-catalog\b[^;&|\n]*?\b(?:set|delete|export|import-machine-env)\b"
    r"|\bplugin\s+rpc\s+call\s+(?:env-catalog\b|(?:bb-plugin-)?lane-pilot\s+(?:save_|reset_|set_|anamnesis\b|schedule_(?:upsert|delete|pause|resume|run_now|cancel_run)))"
    r"|\blane-pilot\s+schedule\s+(?:create|update|delete|pause|resume|run-now|cancel-run)\b"
    r"|\blane-pilot\s+anamnesis\s+(?:add|edit|confirm|reject|forget)\b"
)


def _names_bb(word: str) -> bool:
    """The word is the bb CLI: by name at any path (/opt/homebrew/bin/bb, ~/.local/bin/bb, bb-app, bb.js), through $BB_CLI, or the file BB_CLI points at."""
    if _BB_NAME.match(Path(word).name) or "BB_CLI" in word:
        return True
    cli = os.environ.get("BB_CLI", "")
    return bool(cli) and (word == cli or (Path(word).name == Path(cli).name and Path(cli).name not in _SECRET_CLI_RUNNERS | _SECRET_CLI_SHELLS))


def _lane_pilot_agent_session(key: str | None) -> bool:
    """Any Lane Pilot agent: the launcher sets LANE_PILOT_AGENT_TYPE for every native session (a sub-agent inherits it),
    and the role names cover the sessions that arrive with an agent_type only."""
    return bool(os.environ.get("LANE_PILOT_AGENT_TYPE")) or key in LANE_PILOT_PM_AGENT_TYPES or key in LANE_PILOT_WRITER_ROLES or is_helper_role(key)


def _anamnesis_error(sub: str, rest: list[str], strict: bool, prefix: str) -> str | None:
    """`bb lane-pilot anamnesis <sub> ...` for an agent. A non-PM agent (strict) gets none of it. The PM reads (status, list, show, history,
    whoami, card, review, host) and does not change the owner's records: add, edit, confirm, reject, forget, `sources --set`, `config --authors/--roots`,
    `load --run`. A subcommand the guard cannot read (a variable) counts as a write."""
    flags = {arg.split("=", 1)[0] for arg in rest if arg.startswith("-")}
    write = (
        sub in _ANAMNESIS_WRITES
        or any(ch in sub for ch in "$`")
        or (sub == "sources" and "--set" in flags)
        or (sub == "config" and bool(flags & {"--authors", "--roots"}))
        or (sub == "load" and "--run" in flags)
    )
    return f"bb {prefix} anamnesis {sub}".replace("  ", " ").strip() if strict or write else None


def _bb_args_error(args: list[str], strict: bool = False) -> str | None:
    """What `bb <args>` would change that only the owner may: Env Catalog entries, Lane Pilot's settings and config.
    strict (every agent but the PM): also a secret's raw value and the plugin's own admin commands."""
    if "env-catalog" in args:
        rest = [arg for arg in args[args.index("env-catalog") + 1 :] if not arg.startswith("-")]
        sub = rest[0] if rest else ""
        if sub in _ENV_CATALOG_WRITES or any(ch in sub for ch in "$`"):
            return f"bb env-catalog {sub or '(dynamic)'}"
        if any(arg == "--raw" or arg.startswith("--raw=") for arg in args):
            return " ".join(["bb env-catalog", sub, "--raw"]).replace("  ", " ")
    words = [arg for arg in args if not arg.startswith("-")]
    if strict:
        for index in range(min(len(words), 3)):
            if words[index] == "plugin" and len(words) > index + 1 and words[index + 1] in _BB_PLUGIN_ADMIN:
                return f"bb plugin {words[index + 1]}"
    for index in range(min(len(words), 3)):
        if words[index : index + 3] == ["plugin", "rpc", "call"]:
            plugin_id = words[index + 3] if len(words) > index + 3 else ""
            method = words[index + 4] if len(words) > index + 4 else ""
            if any(ch in plugin_id + method for ch in "$`"):
                return "bb plugin rpc call with a plugin or method the guard cannot read"
            if plugin_id == "env-catalog":
                return f"bb plugin rpc call env-catalog {method}".strip()
            if plugin_id in _LANE_PILOT_PLUGIN_IDS and _LANE_PILOT_RPC_WRITES.match(method):
                return f"bb plugin rpc call {plugin_id} {method}"
    if words and words[0] in _LANE_PILOT_PLUGIN_IDS | {"lane-pilot"} and len(words) > 1 and words[1] in _LANE_PILOT_CLI_WRITES:
        return f"bb {words[0]} {words[1]}"
    if words and words[0] in _LANE_PILOT_PLUGIN_IDS | {"lane-pilot"} and len(words) > 2 and words[1] == "schedule" and (words[2] in _LANE_PILOT_SCHEDULE_WRITES or any(ch in words[2] for ch in "$`")):
        return f"bb {words[0]} schedule {words[2]}"
    if words and words[0] in _LANE_PILOT_PLUGIN_IDS | {"lane-pilot"} and len(words) > 1 and words[1] == "anamnesis":
        return _anamnesis_error(words[2] if len(words) > 2 else "", args[args.index("anamnesis") + 1 :], strict, words[0])
    if len(words) > 3 and words[:3] == ["plugin", "run", "lane-pilot"] and words[3] == "anamnesis":
        return _anamnesis_error(words[4] if len(words) > 4 else "", args[args.index("anamnesis") + 1 :], strict, "plugin run lane-pilot")
    if len(words) > 3 and words[:3] == ["plugin", "run", "lane-pilot"] and words[3] in _LANE_PILOT_CLI_WRITES:
        return f"bb plugin run lane-pilot {words[3]}"
    if len(words) > 4 and words[:3] == ["plugin", "run", "lane-pilot"] and words[3] == "schedule" and (words[4] in _LANE_PILOT_SCHEDULE_WRITES or any(ch in words[4] for ch in "$`")):
        return f"bb plugin run lane-pilot schedule {words[4]}"
    return None


def _secret_cli_segment(segment: list[str], depth: int, strict: bool = False) -> str | None:
    index = 0
    while index < len(segment) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", segment[index]):
        index += 1
    tokens = segment[index:]
    for _ in range(8):
        if not tokens:
            return None
        head = Path(tokens[0]).name
        if head not in _SECRET_CLI_WRAPPERS:
            break
        value_options = _WRAPPER_VALUE_OPTS.get(head, set())
        tokens = tokens[1:]
        while tokens and (tokens[0].startswith("-") or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]) or re.fullmatch(r"[0-9.]+[smhd]?", tokens[0])):
            if head == "env" and tokens[0].startswith("--split-string="):
                # env -S 'bb env-catalog set A B': the value is a command line.
                nested = _secret_cli_error(tokens[0].split("=", 1)[1], depth + 1, strict)
                if nested:
                    return nested
            if tokens[0] in value_options and len(tokens) > 1:
                if head == "env" and tokens[0] in {"-S", "--split-string"}:
                    nested = _secret_cli_error(tokens[1], depth + 1, strict)
                    if nested:
                        return nested
                tokens = tokens[2:]
                continue
            tokens = tokens[1:]
    if not tokens:
        return None
    executable, args = tokens[0], tokens[1:]
    head = Path(executable).name
    if head in _SECRET_CLI_SHELLS:
        for position, arg in enumerate(args):
            if arg.startswith("-") and not arg.startswith("--") and "c" in arg[1:] and position + 1 < len(args):
                return _secret_cli_error(args[position + 1], depth + 1, strict)
        return None
    if head == "eval":
        return _secret_cli_error(" ".join(args), depth + 1, strict)
    if head == "find":
        for position, arg in enumerate(args):
            if arg in {"-exec", "-execdir", "-ok", "-okdir"}:
                return _secret_cli_segment(args[position + 1 :], depth, strict)
        return None
    if strict and head in _REMOTE_SHELLS and _hub_target(args):
        return f"{head} to the hub"
    if _names_bb(executable):
        return _bb_args_error(args, strict)
    if head in {"env-catalog", "plugin", "lane-pilot"}:
        # `$(which bb) env-catalog set ...`: the substitution ended the segment that named bb, and the arguments stand alone.
        return _bb_args_error(tokens, strict)
    if head in _SECRET_CLI_RUNNERS:
        # npx bb ..., pnpm dlx bb ..., node /path/to/bb ...: the first word that names bb starts its arguments.
        for position, arg in enumerate(args):
            if _names_bb(arg):
                return _bb_args_error(args[position + 1 :], strict)
            if arg.startswith("-") or arg in {"dlx", "exec", "x", "run"}:
                continue
            if head in {"node", "nodejs", "deno", "tsx", "ts-node"}:
                break
        return None
    if any(ch in head for ch in "$`*?[{"):
        # An executable the guard cannot read (a variable, a substitution, a glob) may be bb.
        return _bb_args_error(args, strict)
    return None


def _secret_cli_error(command: str, depth: int = 0, strict: bool = False) -> str | None:
    """A Lane Pilot agent's shell command that changes the Env Catalog or Lane Pilot's settings through the bb CLI.
    Reads the command as a shell would: quoting, env prefixes and wrappers, `sh -c`, substitutions, runners such as npx.
    A command it cannot read as shell text (an unbalanced quote) is looked at as text."""
    if depth > 4:
        return "a command nested too deep to read"
    if _BASE64_TO_SHELL.search(command):
        return "a base64 script run by a shell"
    text = _without_data_heredocs(command).replace("`", " ; ")
    try:
        lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|<>()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        match = _SECRET_CLI_TEXT.search(text)
        return match.group(0) if match else None
    segment: list[str] = []
    for token in [*tokens, ";"]:
        if token and all(ch in ";&|<>()" for ch in token):
            if segment:
                error = _secret_cli_segment(segment, depth, strict)
                if error:
                    return error
            segment = []
            continue
        segment.append(token)
        if ("$(" in token or "`" in token) and depth < 4:
            error = _secret_cli_error(token, depth + 1, strict)
            if error:
                return error
    # A script a shell reads from a pipe or a here-string cannot be followed token by token.
    if _SHELL_CONSUMER.search(text):
        match = _SECRET_CLI_TEXT.search(text)
        if match:
            return match.group(0)
    return None


def _env_catalog_tool(name: str) -> str | None:
    """env_get / env_list / env_set / env_delete / env_request from any spelling of the tool name
    (mcp__bb-bridge__env_set, bb-bridge.env_set, env_set)."""
    base = re.split(r"__|[./:]", name or "")[-1]
    return base if base in {"env_get", "env_list", "env_set", "env_delete", "env_request"} else None


def _env_catalog_denial(key: str | None, tool: str) -> str | None:
    """BB's session policy narrows plugins, not their tools, so Env Catalog arrives whole in a helper's session.
    This is the tool-level cut (audit 2026-10-08, S2): nobody a prompt can steer writes or deletes catalog entries
    (the owner does, in the Env Catalog tab; an agent asks with env_request), the PM never reads a value (an errand
    helper does, for the accounts the PM names), and a browser check does not list the catalog."""
    if tool in {"env_set", "env_delete"}:
        return (f"[env-guard] {tool} is not available to Lane Pilot agents: the owner changes the catalog in the Env Catalog tab; "
                "to get a missing key call env_request so the owner gets a form.")
    if key in LANE_PILOT_PM_AGENT_TYPES or (key in PM_AGENTS and os.environ.get("LANE_PILOT_AGENT_TYPE")):
        if tool == "env_get":
            return ("[env-guard] The PM does not read secret values: name the Env Catalog accounts in lane_pilot_errand `accounts` "
                    "(the helper reads them), or in a check's `secrets`. env_list and env_request are yours.")
    if key == "browser-qa" and tool == "env_list":
        return "[env-guard] A browser check does not list the catalog: read only the login its case names, with env_get and its exact name."
    return None


def main() -> None:
    p = read_payload()
    if not isinstance(p, dict):
        emit_deny(
            detect_client({}),
            "[agent-guard] malformed PreToolUse payload blocked.",
        )
    client = detect_client(p)
    name = tool_name(p)
    agent = p.get("agent_type")
    key = agent_key(agent)
    env_tool = _env_catalog_tool(name)
    if env_tool and (is_helper_role(key) or key in LANE_PILOT_PM_AGENT_TYPES or (key in PM_AGENTS and os.environ.get("LANE_PILOT_AGENT_TYPE"))):
        env_denial = _env_catalog_denial(key, env_tool)
        if env_denial:
            emit_deny(client, env_denial)
    if is_shell_tool(name) and _lane_pilot_agent_session(key):
        # The PM ships its own plugin (reload/install/update) and reads BB state; every other Lane Pilot agent gets the stricter list.
        pm_session = key in LANE_PILOT_PM_AGENT_TYPES or bool(key in PM_AGENTS and os.environ.get("LANE_PILOT_AGENT_TYPE"))
        secret_cli = _secret_cli_error(shell_command(p), strict=not pm_session)
        if secret_cli:
            emit_deny(client, f"[env-guard] {secret_cli} is not available to Lane Pilot agents: the owner changes Env Catalog entries, Lane Pilot's "
                      "settings, schedules and anamnesis (the Env Catalog tab, Lane Pilot settings, the schedule board, the owner's own terminal), not an agent's shell. For a missing key use "
                      "env_request or `bb env-catalog request <NAME>`; the owner gets a form. For a schedule use the PM tool lane_pilot_schedule: it asks the owner.")
    if is_helper_role(key):
        if is_edit_tool(name):
            path = file_path(p)
            if not path or not _helper_edit_allowed(path, p.get("cwd") or p.get("workspaceRoot"), key or ""):
                emit_deny(client, f"[helper-guard] {HELPER_DENIAL}")
            emit_allow(client)
        if name and not is_shell_tool(name):
            emit_allow(client)
        cmd = shell_command(p)
        if not cmd.strip():
            emit_deny(client, "[helper-guard] malformed shell tool payload blocked: supply a command string in command.")
        _helper_shell_checks(client, cmd, p, key or "")
        # Fall through to general safety checks (destructive SQL, permanent delete, etc.)
    elif key in LANE_PILOT_PM_AGENT_TYPES:
        if is_edit_tool(name):
            path = file_path(p)
            if not path or not _pm_edit_allowed(path, p.get("cwd") or p.get("workspaceRoot")):
                _deny_pm(client, f"{name or 'Edit'} of {path or 'this file'} is not the PM's", lane_pilot=True, path=path or "")
            emit_allow(client)
        if name and not is_shell_tool(name):
            emit_allow(client)
        cmd = shell_command(p)
        if not cmd.strip():
            emit_deny(client, "[lane-pilot-guard] malformed shell tool payload blocked: supply a command string in command.")
        # The Lane Pilot PM is the user's own chat: its shell runs under the same rules as a plain
        # claude-lane chat (deploys, compose, npm scripts, systemctl pass; the destructive list below
        # still blocks). Only BB thread control stays scoped, and writers are BB threads, not lanes.
        _lane_pilot_shell_checks(client, cmd, p)
    lane_pilot_chat = key in LANE_PILOT_PM_AGENT_TYPES or bool(key in PM_AGENTS and os.environ.get("LANE_PILOT_AGENT_TYPE"))
    if key in PM_AGENTS and is_edit_tool(name):
        path = file_path(p)
        if not path or not _pm_edit_allowed(path, p.get("cwd") or p.get("workspaceRoot")):
            _deny_pm(client, f"{name or 'Edit'} of {path or 'this file'} is not the PM's" if lane_pilot_chat else f"direct {name or 'edit'} outside PM contract files is forbidden",
                     lane_pilot=lane_pilot_chat, path=(path or "") if lane_pilot_chat else None)
        emit_allow(client)
    if name and not is_shell_tool(name):
        emit_allow(client)
    cmd = shell_command(p)
    if not cmd.strip():
        if is_shell_tool(name):
            emit_deny(client, "[agent-guard] malformed shell tool payload blocked: supply a command string in command.")
        emit_allow(client)

    # Destructive checks read commands, not report text a heredoc hands to a non-shell program.
    low = _without_data_heredocs(cmd).lower()

    # A Lane Pilot BB chat (its launcher sets LANE_PILOT_AGENT_TYPE) runs writers as BB threads,
    # and Lane Pilot itself critiques, accepts and merges them into main.
    if lane_pilot_chat and re.search(
        r"(?:^|[;&|(\n]\s*|\b(?:until|while|if|then|do|exec|command)\s+)(?:[^\s;&|()]+/)?"
        r"(?:run-controller\b|run-init\b|wt-merge-main\b|lane-ctl\s+(?:start|retry|fallback)\b|lane-bg\b|lane-exec\b)",
        _without_data_heredocs(cmd),
    ):
        emit_deny(
            client,
            "[lane-pilot-guard] In a Lane Pilot chat writer lanes are BB threads, and Lane Pilot "
            "merges accepted work into main itself. Dispatch each task with lane_pilot_dispatch_writer "
            "and poll lane_pilot_wait_writer; do not start run-controller, run-init, wt-merge-main, "
            "lane-ctl, lane-bg or lane-exec.",
        )

    if key == "dev-orchestrator" and re.search(
        r"(?:^|[;&|(\n]\s*|\b(?:until|while|if|then|do|exec|command)\s+)"
        r"(?:[^\s;&|()]+/)?run-controller\s+(?:start|watch|status)\b",
        cmd,
    ):
        emit_deny(
            client,
            "[orchestrator-guard] dev-orchestrator must not run run-controller "
            "start/watch/status directly. Dispatch exactly one Agent(run-supervisor) "
            "with RUN_DIR, PROJECT_CWD, WRITER_PROVIDER, and "
            "PM_NAME=dev-orchestrator; wait for its terminal digest. Use "
            "Agent(lane-supervisor) for manual status or recovery.",
        )

    if key in PM_AGENTS:
        # BB native PM (launcher sets LANE_PILOT_AGENT_TYPE): same shell as a
        # plain claude-lane chat — deploys and project node scripts pass. CLI
        # orchestrators without that env stay on the allowlist.
        if os.environ.get("LANE_PILOT_AGENT_TYPE"):
            _lane_pilot_shell_checks(client, cmd, p)
        else:
            error = _pm_shell_error(cmd)
            if error:
                _deny_pm(client, error)

    # git hook skip
    git_writes = _git_args(_without_data_heredocs(cmd), {"commit", "push", "merge"})
    if git_writes and (
        any("--no-verify" in args for args in git_writes) or "husky=0" in low or "husky=false" in low
    ):
        emit_deny(client, "[agent-guard] git --no-verify / HUSKY=0 blocked. Fix the failing hook instead of bypassing it.")

    # force push: flags are read inside the push command itself and case-sensitively, so
    # `git commit -F msg && git push` is not a force push; +refspec forces too.
    for args in _git_args(_without_data_heredocs(cmd), {"push"}):
        forced = any(a == "--force" or a.startswith("--force=") or re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", a) or (a.startswith("+") and len(a) > 1) for a in args)
        if forced and lane_pilot_chat:
            emit_deny(client, "[lane-pilot-guard] Force-push is not allowed in a Lane Pilot chat: origin moved, so someone else's work is there. "
                      "Run git fetch, report what differs from origin, and dispatch a writer to integrate it; push again once that is merged.")
        if forced and not any(a.startswith("--force-with-lease") for a in args):
            emit_deny(client, "[agent-guard] git push --force blocked. Use --force-with-lease after git fetch.")

    # SQL destroyers (simple)
    if re.search(r"\b(drop\s+(table|database|schema)|truncate\s+table)\b", low):
        emit_deny(client, "[agent-guard] DROP/TRUNCATE blocked. Run schema changes through project migrations or have the owner review them explicitly.")

    if re.search(r"\bdelete\s+from\s+\w+\b", low) and "where" not in low:
        emit_deny(client, "[agent-guard] DELETE without WHERE blocked. Add a WHERE clause scoping the deleted rows, or use TRUNCATE via migrations if a table wipe is intended.")

    # Deleting for good (rm, unlink, shred, find -delete) outside regenerated folders: the Trash can be undone.
    delete_error = _permanent_delete_error(_without_data_heredocs(cmd))
    if delete_error:
        emit_deny(client, delete_error)

    emit_allow(client)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        emit_deny(
            detect_client({}),
            "[agent-guard] malformed PreToolUse payload blocked.",
        )
