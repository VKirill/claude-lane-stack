#!/usr/bin/env python3
"""PreToolUse: block destructive shell across CLIs."""
from __future__ import annotations
import os, re, shlex, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_payload import (  # type: ignore
    read_payload, detect_client, tool_name, shell_command, file_path,
    is_shell_tool, is_edit_tool, emit_allow, emit_deny,
)

PM_AGENTS = {"dev-orchestrator", "frontend-orchestrator", "marketing-orchestrator"}
PM_READ_COMMANDS = {
    "cat", "cd", "cmp", "cut", "date", "df", "du", "echo", "file", "find",
    "gitnexus", "grep", "head", "journalctl", "jq", "ls", "lsof", "pgrep",
    "printf", "ps", "pstree", "pwd", "readlink", "realpath", "rg", "sed",
    "sha256sum", "sort", "stat", "tail", "test", "true", "false", "type",
    "uniq", "wc", "which", "yq",
}
# Typed control-plane CLIs the PM may run directly (not writer lifecycle).
# lane-ctl / run-controller start|watch|status stay delegated to supervisors.
PM_CONTROL_COMMANDS = {
    "agents-doctor",
    "lane-stall-check",
    "resume-project",
    "run-board",
    "run-finalize",
    "run-init",
    "run-validate",
    "wt-create",
    "wt-merge-main",
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
_PM_TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".txt"}
SQL_MUTATION = re.compile(
    r"\b(?:insert|update|delete|merge|create|alter|drop|truncate|grant|revoke|"
    r"comment|vacuum|reindex|cluster|refresh)\b",
    re.I,
)


def _deny_pm(client: str, detail: str) -> None:
    emit_deny(
        client,
        "[orchestrator-guard] "
        f"{detail}. Keep PM work read-only/control-plane-only; delegate mutations "
        "to the run supervisor and its writer/recovery lane.",
    )


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

    Aligns with SOLO/dev-orchestrator: `.agents/**`, `docs/plans/**`,
    `PROGRESS.md` / `LESSONS.md`, and dotenv (`.env*`) for secrets the human
    trusts the PM with. Machine lifecycle receipts under a run (controller,
    artifacts, events, sessions) stay tool-owned.
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
    if requested.is_absolute() and target.is_relative_to(Path("/tmp")):
        return suffix in _PM_TEXT_SUFFIXES
    if not target.is_relative_to(root):
        return False
    relative = target.relative_to(root)
    normalized = relative.as_posix()
    if normalized in {"PROGRESS.md", "LESSONS.md"}:
        return True
    if _is_env_secret_file(normalized):
        return True
    if normalized.startswith("docs/plans/"):
        return suffix in _PM_TEXT_SUFFIXES
    if normalized.startswith(".agents/"):
        if _PM_RUN_MACHINE_RECEIPT.search(normalized):
            return False
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


def _pm_segment_error(segment: list[str]) -> str | None:
    if not segment:
        return None
    executable = Path(segment[0]).name
    args = segment[1:]

    if executable == "export":
        if args and all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", arg) for arg in args):
            return None
        return "unsupported export command"
    if executable in PM_CONTROL_COMMANDS:
        return None
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
        if command in {"images", "inspect", "logs", "ps", "stats", "top", "version"}:
            return None
        if command == "compose":
            offset = args.index("compose") + 1
            compose = _subcommand(args[offset:], {"-f", "--file", "-p", "--project-name"})
            return None if compose in {"config", "images", "logs", "ps", "top"} else (
                f"docker compose {compose or '<missing>'} is not read-only"
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
        return f"docker {command or '<missing>'} is not read-only"
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
    for token in tokens:
        if token in {"&&", "||", ";", "|"}:
            segments.append([])
        elif any(char in token for char in "<>") or token == "&":
            return "redirection or background shell execution is forbidden"
        else:
            segments[-1].append(token)
    for segment in segments:
        error = _pm_segment_error(segment)
        if error:
            return error
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
    if agent in PM_AGENTS and is_edit_tool(name):
        path = file_path(p)
        if not path or not _pm_edit_allowed(path, p.get("cwd") or p.get("workspaceRoot")):
            _deny_pm(client, f"direct {name or 'edit'} outside PM contract files is forbidden")
        emit_allow(client)
    if name and not is_shell_tool(name):
        emit_allow(client)
    cmd = shell_command(p)
    if not cmd.strip():
        if is_shell_tool(name):
            emit_deny(client, "[agent-guard] malformed shell tool payload blocked.")
        emit_allow(client)

    low = cmd.lower()

    if p.get("agent_type") == "dev-orchestrator" and re.search(
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

    if agent in PM_AGENTS:
        error = _pm_shell_error(cmd)
        if error:
            _deny_pm(client, error)

    # git hook skip
    if re.search(r"\bgit\s+(commit|push|merge)\b", low) and (
        "--no-verify" in low or "husky=0" in low or "husky=false" in low
    ):
        emit_deny(client, "[agent-guard] git --no-verify / HUSKY=0 blocked. Fix the failing hook instead of bypassing it.")

    # force push
    if re.search(r"\bgit\s+push\b", low) and (
        re.search(r"(^|[\s])--force($|[\s=])", low) or re.search(r"(^|[\s])-f($|[\s])", low)
    ) and "--force-with-lease" not in low:
        emit_deny(client, "[agent-guard] git push --force blocked. Use --force-with-lease after git fetch.")

    # SQL destroyers (simple)
    if re.search(r"\b(drop\s+(table|database|schema)|truncate\s+table)\b", low):
        emit_deny(client, "[agent-guard] DROP/TRUNCATE blocked. Use migrations / explicit review.")

    if re.search(r"\bdelete\s+from\s+\w+\s*;?\s*$", low) and "where" not in low:
        emit_deny(client, "[agent-guard] DELETE without WHERE blocked.")

    # rm -rf outside known build dirs
    if re.search(r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*|--force).*-[a-zA-Z]*r|rm\s+-rf\b|rm\s+-fr\b", low):
        safe = any(x in low for x in (
            "node_modules", "/tmp/", ".next", "dist", "build", ".cache", "coverage", ".turbo",
        ))
        if not safe:
            emit_deny(client, "[agent-guard] rm -rf blocked (use gio trash or whitelist build/tmp paths).")

    emit_allow(client)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        emit_deny(
            detect_client({}),
            "[agent-guard] malformed PreToolUse payload blocked.",
        )
