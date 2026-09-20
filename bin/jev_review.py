#!/usr/bin/env python3
"""Staged Jev diff review (devagrawal09/jev-review workflow, our client).

Code parses git diff. Jev only judges: screen noul → hunk choice → mechanism
→ severity. Findings are review prompts, not proof. Fail-open without a key.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from jev_decisions import (
    JevCritiqueError,
    call_jev,
    choice,
    clip,
    jev_enabled,
    noul,
    score_value,
    typesafe_key,
)

SCREEN_THRESHOLD = 0.7
MIN_LOCATION_CONFIDENCE = 0.55
MAX_FOLLOW_UPS = 8
MAX_PROFILES = 5
MAX_FILES = 20
MAX_PATCH = 6000
BLOCKING_SEVERITY = 2.0
ROUTE_SEVERITY = 1.5
SKIP_NAMES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Cargo.lock",
    "poetry.lock",
    "uv.lock",
}
SKIP_SUFFIX = (".min.js", ".map", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".woff", ".woff2")
SKIP_DIR = ("node_modules/", "dist/", "vendor/", ".git/", ".agents/")
TEST_FILE = re.compile(
    r"(?:^|/)(?:tests?|__tests__)(?:/|$)|(?:^|/)test_[^/]+\.[a-z]+$|\.(?:spec|test)\.[a-z]+$",
    re.I,
)
HUNK_RE = re.compile(r"^@@ .*\+(\d+)")

DIMENSIONS = {
    "correctness": "incorrect runtime behavior",
    "security": "weakened security boundary",
    "reliability": "crash, race, leak, deadlock, or poor recovery",
    "compatibility": "broken caller, format, protocol, or public behavior",
    "testGap": "important behavior lacks targeted tests",
}
MECHANISMS = {
    "correctness": {
        "condition": "A condition handles the wrong cases",
        "state": "State is read, updated, or retained incorrectly",
        "dataflow": "Data is transformed or passed incorrectly",
        "asynccontrol": "Asynchronous ordering or error handling is incorrect",
        "other": "Another concrete correctness mechanism",
        "noissue": "The selected evidence does not support a concrete correctness issue",
    },
    "security": {
        "authorization": "Authorization or trust boundaries are weakened",
        "injection": "Untrusted input can reach an unsafe interpreter or sink",
        "exposure": "Sensitive data can be disclosed",
        "unsafedefault": "A default configuration creates avoidable exposure",
        "other": "Another concrete security mechanism",
        "noissue": "The selected evidence does not support a concrete security issue",
    },
    "reliability": {
        "cleanup": "A resource or side effect is not cleaned up",
        "concurrency": "Concurrency can race, deadlock, or lose work",
        "recovery": "Failure or cancellation recovery is incomplete",
        "crash": "A realistic path can throw or terminate unexpectedly",
        "other": "Another concrete reliability mechanism",
        "noissue": "The selected evidence does not support a concrete reliability issue",
    },
    "compatibility": {
        "api": "A public API or type contract changes incompatibly",
        "behavior": "Existing callers observe changed behavior",
        "dataformat": "A persisted or exchanged format changes incompatibly",
        "protocol": "An external command or protocol contract changes",
        "other": "Another concrete compatibility mechanism",
        "noissue": "The selected evidence does not support a concrete compatibility issue",
    },
    "testGap": {
        "branch": "An important branch lacks targeted coverage",
        "failure": "A failure or cancellation path lacks coverage",
        "boundary": "A boundary or edge case lacks coverage",
        "integration": "An interaction between components lacks coverage",
        "other": "Another concrete test gap",
        "noissue": "The selected evidence does not support a concrete test gap",
    },
}
CHANGE_TYPES = {
    "behavior": "Adds or changes runtime behavior",
    "interface": "Changes an exported API, type, protocol, or data shape",
    "infrastructure": "Changes execution, scheduling, build, or operational plumbing",
    "observability": "Changes events, logging, monitoring, or diagnostics",
    "refactor": "Restructures implementation without intending behavior changes",
    "routine": "A small routine change that fits none of the other categories",
}
OWNERS = {
    "security": "Security, authentication, authorization, or data exposure",
    "api": "Public APIs, compatibility, schemas, or protocols",
    "runtime": "Execution, concurrency, resources, or failure recovery",
    "testing": "Coverage strategy, fixtures, or regression testing",
    "maintainer": "The owning domain or feature maintainer",
}
PRIORITY_RUBRIC = [
    "Routine review is sufficient",
    "A focused review of the changed behavior is useful",
    "Careful review is needed before merge",
    "Specialist or immediate review is needed",
]
SEVERITY_RUBRIC = [
    "No meaningful impact or no supported issue",
    "Minor or narrowly limited impact",
    "Significant correctness, reliability, compatibility, or security impact",
    "Critical security, data-loss, or widespread outage impact",
]


class JevReviewBlock(RuntimeError):
    """Accept/night gate: Jev found a blocking finding."""


def parse_hunks(patch: str) -> list[dict[str, Any]]:
    hunks: list[dict[str, Any]] = []
    current: list[str] | None = None
    start = 1

    def flush() -> None:
        if current:
            hunks.append(
                {
                    "id": f"hunk_{len(hunks) + 1}",
                    "startLine": start,
                    "patch": clip("\n".join(current), 1800),
                }
            )

    for line in (patch or "").splitlines():
        if line.startswith("@@ "):
            flush()
            match = HUNK_RE.search(line)
            start = int(match.group(1)) if match else 1
            current = [line]
        elif current is not None:
            current.append(line)
    flush()
    return hunks


def parse_changed_files(diff_text: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in (diff_text or "").splitlines():
        if line.startswith("diff --git "):
            if current and current.get("patch"):
                files.append(current)
            parts = line.split(" b/", 1)
            path = parts[1] if len(parts) == 2 else line.split()[-1]
            current = {"path": path, "patch": ""}
            continue
        if current is None:
            continue
        if line.startswith("Binary files") or line.startswith("GIT binary"):
            current = None
            continue
        current["patch"] += line + "\n"
    if current and current.get("patch"):
        files.append(current)
    return files


def skip_path(path: str) -> bool:
    name = Path(path).name
    if name in SKIP_NAMES or name.endswith(SKIP_SUFFIX):
        return True
    return any(part in path.replace("\\", "/") for part in SKIP_DIR)


def collect_diff(repo: Path, base: str | None = None) -> str:
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout if result.returncode == 0 else ""

    if base:
        return git("diff", "--no-ext-diff", "--unified=8", base)
    unstaged = git("diff", "--no-ext-diff", "--unified=8", "HEAD")
    staged = git("diff", "--no-ext-diff", "--unified=8", "--cached")
    return (unstaged + "\n" + staged).strip()


def _noul_q(question: str, yes: str, no: str) -> dict[str, Any]:
    return {
        "type": "noul",
        "instructions": question,
        "criteria": {"true": yes, "false": no},
    }


def screen_file(file: dict[str, Any], tests: list[dict[str, Any]]) -> dict[str, float]:
    raw = call_jev(
        {
            "file": {"path": file["path"], "patch": clip(file["patch"], MAX_PATCH)},
            "changedTests": [
                {"path": item["path"], "patch": clip(item["patch"], 2500)}
                for item in tests[:6]
            ],
        },
        {
            "correctness": _noul_q(
                "Does file.patch directly support that this change likely introduces incorrect runtime behavior? Inspect file.patch. Ignore style and naming.",
                "The patch contains a realistic path to a wrong runtime result",
                "The patch is correct, non-behavioral, or lacks direct evidence of a bug",
            ),
            "security": _noul_q(
                "Does file.patch directly support that this change introduces or weakens a security boundary?",
                "The patch creates a concrete path around a security control or into an unsafe sink",
                "No security boundary is weakened by the patch",
            ),
            "reliability": _noul_q(
                "Does file.patch directly support that this change can crash, race, leak, deadlock, or recover poorly?",
                "A changed path can lose work, leak resources, hang, crash, or leave inconsistent state",
                "The patch preserves safe lifecycle and failure handling",
            ),
            "compatibility": _noul_q(
                "Does file.patch directly support that this change can break an existing caller, format, protocol, or public behavior?",
                "An existing consumer can fail because a contract changed without a safe migration",
                "The changed contract remains compatible or is entirely internal",
            ),
            "testGap": _noul_q(
                "Does file.patch change important behavior without adequate targeted evidence in changedTests?",
                "Important changed behavior has no targeted changed test",
                "Changed tests exercise the important behavior, or the patch is non-behavioral",
            ),
        },
        title="lane-stack jev-review-screen",
    )
    answers = raw.get("answers") if isinstance(raw.get("answers"), dict) else {}
    return {name: noul(answers, name) for name in DIMENSIONS}


def profile_file(file: dict[str, Any], probabilities: dict[str, float]) -> dict[str, Any]:
    raw = call_jev(
        {
            "file": {"path": file["path"], "patch": clip(file["patch"], MAX_PATCH)},
            "screeningProbabilities": probabilities,
        },
        {
            "category": {
                "type": "choice",
                "instructions": "Which category best describes file.patch? Focus on the primary purpose of the change.",
                "criteria": CHANGE_TYPES,
            },
            "reviewPriority": {
                "type": "score",
                "instructions": "Rate how closely a human should review file.patch, considering the code and screeningProbabilities.",
                "criteria": PRIORITY_RUBRIC,
            },
        },
        title="lane-stack jev-review-profile",
    )
    answers = raw.get("answers") if isinstance(raw.get("answers"), dict) else {}
    category, cat_conf = choice(
        answers, "category", set(CHANGE_TYPES), "routine"
    )
    priority, pri_conf = score_value(answers, "reviewPriority", 0.0)
    return {
        "file": file["path"],
        "category": category,
        "categoryConfidence": cat_conf,
        "reviewPriority": priority,
        "reviewPriorityConfidence": pri_conf,
    }


def locate_signal(
    file: dict[str, Any], dimension: str, probability: float
) -> dict[str, Any] | None:
    hunks = parse_hunks(file.get("patch") or "")
    if not hunks:
        return None
    criteria = {hunk["id"]: f"Candidate beginning at line {hunk['startLine']}" for hunk in hunks}
    criteria["nomatch"] = "No candidate hunk directly supports the suspected concern"
    located = call_jev(
        {
            "file": file["path"],
            "suspectedConcern": {
                "dimension": dimension,
                "definition": DIMENSIONS[dimension],
                "screeningProbability": probability,
            },
            "candidateHunks": hunks,
        },
        {
            "evidence": {
                "type": "choice",
                "instructions": (
                    "Which candidate hunk provides the strongest direct evidence "
                    "for suspectedConcern? Select noMatch when none does."
                ),
                "criteria": criteria,
            }
        },
        title="lane-stack jev-review-hunk",
    )
    answers = located.get("answers") if isinstance(located.get("answers"), dict) else {}
    picked, loc_conf = choice(
        answers, "evidence", set(criteria), "nomatch"
    )
    if picked == "nomatch" or loc_conf < MIN_LOCATION_CONFIDENCE:
        return None
    hunk = next((item for item in hunks if item["id"] == picked), None)
    if hunk is None:
        return None
    classified = call_jev(
        {
            "file": file["path"],
            "suspectedConcern": {"dimension": dimension, "definition": DIMENSIONS[dimension]},
            "selectedEvidence": hunk,
        },
        {
            "mechanism": {
                "type": "choice",
                "instructions": "Which mechanism best describes the suspected concern supported by selectedEvidence?",
                "criteria": MECHANISMS[dimension],
            }
        },
        title="lane-stack jev-review-mechanism",
    )
    mech_answers = classified.get("answers") if isinstance(classified.get("answers"), dict) else {}
    mechanism, mech_conf = choice(
        mech_answers, "mechanism", set(MECHANISMS[dimension]), "noissue"
    )
    if mechanism == "noissue":
        return None
    impact = call_jev(
        {
            "file": file["path"],
            "suspectedConcern": {"dimension": dimension, "definition": DIMENSIONS[dimension]},
            "selectedEvidence": hunk,
        },
        {
            "severity": {
                "type": "score",
                "instructions": "Assuming selectedEvidence exhibits suspectedConcern, rate the likely production impact.",
                "criteria": SEVERITY_RUBRIC,
            }
        },
        title="lane-stack jev-review-severity",
    )
    sev_answers = impact.get("answers") if isinstance(impact.get("answers"), dict) else {}
    severity, sev_conf = score_value(sev_answers, "severity", 0.0)
    owner = ""
    owner_conf = 0.0
    if severity >= ROUTE_SEVERITY:
        routed = call_jev(
            {
                "file": file["path"],
                "concern": {
                    "dimension": dimension,
                    "mechanism": mechanism,
                    "severity": severity,
                },
                "selectedEvidence": hunk,
            },
            {
                "owner": {
                    "type": "choice",
                    "instructions": "Which reviewer is best suited to investigate this concern?",
                    "criteria": OWNERS,
                }
            },
            title="lane-stack jev-review-owner",
        )
        own_answers = routed.get("answers") if isinstance(routed.get("answers"), dict) else {}
        owner, owner_conf = choice(own_answers, "owner", set(OWNERS), "maintainer")
    return {
        "file": file["path"],
        "dimension": dimension,
        "probability": probability,
        "line": hunk["startLine"],
        "locationConfidence": loc_conf,
        "mechanism": mechanism,
        "mechanismConfidence": mech_conf,
        "severity": severity,
        "severityConfidence": sev_conf,
        "owner": owner,
        "ownerConfidence": owner_conf,
        "action": "request_changes" if severity >= BLOCKING_SEVERITY else "comment",
    }


def path_owned(path: str, owns: list[str] | None) -> bool:
    """Prefix/glob-prefix match against task owns_paths. Empty owns = everything."""
    if not owns:
        return True
    norm = path.replace("\\", "/").lstrip("./")
    for rule in owns:
        raw = str(rule).replace("\\", "/").strip()
        if raw.endswith("/**"):
            raw = raw[:-3]
        raw = raw.rstrip("/")
        if not raw:
            continue
        if norm == raw or norm.startswith(raw + "/"):
            return True
    return False


def review_changes(
    repo: Path, *, base: str | None = None, owns_paths: list[str] | None = None
) -> dict[str, Any]:
    files = [item for item in parse_changed_files(collect_diff(repo, base)) if not skip_path(item["path"])]
    tests = [item for item in files if TEST_FILE.search(item["path"])]
    sources = [
        item
        for item in files
        if not TEST_FILE.search(item["path"]) and path_owned(item["path"], owns_paths)
    ][:MAX_FILES]
    empty = {
        "schema_version": 1,
        "mode": "changes",
        "scope": str(repo),
        "base": base or "HEAD",
        "screenedFiles": 0,
        "matrix": [],
        "profiles": [],
        "findings": [],
        "verdict": "skip",
        "blocking": 0,
    }
    if not sources:
        return empty
    if not jev_enabled():
        empty["verdict"] = "disabled"
        return empty
    matrix: list[dict[str, Any]] = []
    signals: list[tuple[dict[str, Any], str, float]] = []
    for file in sources:
        try:
            probabilities = screen_file(file, tests)
        except JevCritiqueError:
            continue
        matrix.append({"file": file["path"], **probabilities})
        for name, value in probabilities.items():
            if value >= SCREEN_THRESHOLD:
                signals.append((file, name, value))
    signals.sort(key=lambda item: item[2], reverse=True)
    profiled = sorted(
        matrix, key=lambda row: max(float(row.get(name) or 0) for name in DIMENSIONS), reverse=True
    )[:MAX_PROFILES]
    profiles: list[dict[str, Any]] = []
    by_path = {item["path"]: item for item in sources}
    for row in profiled:
        file = by_path.get(str(row["file"]))
        if not file:
            continue
        try:
            profiles.append(
                profile_file(file, {name: float(row.get(name) or 0) for name in DIMENSIONS})
            )
        except JevCritiqueError:
            continue
    findings: list[dict[str, Any]] = []
    for file, dimension, probability in signals[:MAX_FOLLOW_UPS]:
        try:
            found = locate_signal(file, dimension, probability)
        except JevCritiqueError:
            continue
        if found:
            findings.append(found)
    findings.sort(key=lambda item: float(item.get("severity") or 0), reverse=True)
    blocking = sum(1 for item in findings if item.get("action") == "request_changes")
    if blocking:
        verdict = "request_changes"
    elif findings:
        verdict = "comment"
    else:
        verdict = "clean"
    return {
        "schema_version": 1,
        "mode": "changes",
        "scope": str(repo),
        "base": base or "HEAD",
        "screenedFiles": len(sources),
        "matrix": matrix,
        "profiles": profiles,
        "findings": findings,
        "verdict": verdict,
        "blocking": blocking,
    }


AUDIT_MARK = "<!-- jev-review-audit -->"


def accept_review_mode() -> str:
    raw = (os.environ.get("LANE_JEV_REVIEW") or "").strip().lower()
    if raw in {"0", "off", "false", "no"}:
        return "off"
    if raw == "advisory":
        return "advisory"
    if raw in {"gate", "retry"}:
        return "retry"
    if "unittest" in sys.modules:
        return "off"
    if typesafe_key():
        return "retry"
    return "off"


def render_audit(report: dict[str, Any]) -> str:
    """Template from typed findings. Jev does not generate issue text."""
    lines = [
        AUDIT_MARK,
        "",
        "## Jev review — fix these, then stop",
        "",
        f"Verdict: {report.get('verdict')}",
        "Same session, one rewrite. Do not expand scope.",
        "",
    ]
    blocking = [
        item
        for item in (report.get("findings") or [])
        if item.get("action") == "request_changes"
        or float(item.get("severity") or 0) >= BLOCKING_SEVERITY
    ]
    if not blocking:
        lines.append("Blocking verdict without a located hunk. Re-read jev-review.json.")
    for index, item in enumerate(blocking[:8], 1):
        lines.append(
            f"{index}. {item.get('dimension')} / {item.get('mechanism')} "
            f"@ {item.get('file')}:{item.get('line')} sev={item.get('severity')}"
        )
        hunk = item.get("hunk") or item.get("patch") or ""
        if hunk:
            lines.append("```")
            lines.append(clip(str(hunk), 800))
            lines.append("```")
    lines.append("")
    lines.append("Do not argue the review. Change the code or add a targeted test.")
    return "\n".join(lines) + "\n"


def apply_accept_review(
    project_cwd: Path,
    artifact: Path,
    *,
    attempt: int = 1,
    owns_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Write jev-review.json. next=accept|jev_retry|blocked. Fail-open."""
    mode = accept_review_mode()
    if mode == "off" or not jev_enabled():
        return {"verdict": "skip", "next": "accept", "mode": mode}
    try:
        report = review_changes(Path(project_cwd), owns_paths=owns_paths)
    except Exception:
        return {"verdict": "error", "next": "accept", "mode": mode}
    out = Path(artifact) / "jev-review.json"
    out.write_text(__import__("json").dumps(report, indent=2, ensure_ascii=False) + "\n")
    decision = {**report, "mode": mode, "next": "accept"}
    if report.get("verdict") != "request_changes" or mode == "advisory":
        return decision
    used = int(attempt or 1) >= 2 or (Path(artifact) / "jev-audit.applied.md").is_file()
    if used:
        decision["next"] = "blocked"
        return decision
    (Path(artifact) / "jev-audit.md").write_text(render_audit(report), encoding="utf-8")
    decision["next"] = "jev_retry"
    return decision


def merge_audit_into_prompt(prompt: bytes, artifact: Path) -> bytes:
    """Append jev-audit.md once. Idempotent if AUDIT_MARK already in prompt."""
    audit_path = Path(artifact) / "jev-audit.md"
    if not audit_path.is_file():
        return prompt
    text = prompt.decode("utf-8")
    if AUDIT_MARK in text:
        return prompt
    audit = audit_path.read_text(encoding="utf-8")
    (Path(artifact) / "jev-audit.applied.md").write_text(audit, encoding="utf-8")
    return (text.rstrip() + "\n\n" + audit).encode("utf-8")


def maybe_accept_review(
    project_cwd: Path,
    artifact: Path,
    *,
    attempt: int = 1,
    owns_paths: list[str] | None = None,
) -> dict[str, Any] | None:
    """Accept hook. Does not raise; apply_accept_review owns gate/retry."""
    decision = apply_accept_review(
        project_cwd, artifact, attempt=attempt, owns_paths=owns_paths
    )
    if decision.get("verdict") in {"skip", "disabled"}:
        return None
    return decision
