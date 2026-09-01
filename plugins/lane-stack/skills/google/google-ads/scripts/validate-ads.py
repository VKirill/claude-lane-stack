#!/usr/bin/env python3
"""
Google Ads Creative Validator.

Validates character limits, asset counts, and required fields for all 8
Google Ads formats. Correctly handles Unicode (Cyrillic, emoji, CJK).

Usage:
    python validate-ads.py creative.yaml
    python validate-ads.py creative.json
    cat creative.yaml | python validate-ads.py -

Exit codes:
    0 — all checks passed (warnings allowed)
    1 — at least one hard fail
    2 — invalid input file
    3 — unknown format value

See references/validator-usage.md for input schema.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

# -----------------------------------------------------------------------------
# Format specifications — single source of truth, mirrors character-limits.md
# -----------------------------------------------------------------------------

FORMATS: dict[str, dict[str, Any]] = {
    "RSA": {
        "name": "Responsive Search Ad",
        "headline": {"max_chars": 30, "min_count": 3, "max_count": 15},
        "description": {"max_chars": 90, "min_count": 2, "max_count": 4},
        "path1": {"max_chars": 15, "required": False},
        "path2": {"max_chars": 15, "required": False},
        "final_url": {"required": True},
    },
    "PMAX": {
        "name": "Performance Max",
        "headline": {"max_chars": 30, "min_count": 3, "max_count": 5},
        "long_headline": {"max_chars": 90, "min_count": 1, "max_count": 5},
        "description": {"max_chars": 90, "min_count": 2, "max_count": 5},
        "short_description": {"max_chars": 60, "min_count": 1, "max_count": 1},
        "business_name": {"max_chars": 25, "required": True},
        "final_url": {"required": True},
    },
    "DISPLAY": {
        "name": "Display Responsive Ad",
        "headline": {"max_chars": 30, "min_count": 1, "max_count": 5},
        "long_headline": {"max_chars": 90, "min_count": 1, "max_count": 1},
        "description": {"max_chars": 90, "min_count": 1, "max_count": 5},
        "business_name": {"max_chars": 25, "required": True},
        "final_url": {"required": True},
    },
    "DEMAND_GEN": {
        "name": "Demand Gen Ad",
        "headline": {"max_chars": 40, "min_count": 1, "max_count": 5},
        "long_headline": {"max_chars": 90, "min_count": 1, "max_count": 1},
        "description": {"max_chars": 90, "min_count": 1, "max_count": 5},
        "business_name": {"max_chars": 25, "required": True},
        "final_url": {"required": True},
    },
    "VIDEO": {
        "name": "Video Ad (YouTube)",
        "sub_formats": ["skippable_in_stream", "bumper", "non_skippable_in_stream",
                        "in_feed", "shorts"],
    },
    "APP": {
        "name": "App Campaign (UAC)",
        "headline": {"max_chars": 30, "min_count": 1, "max_count": 5},
        "description": {"max_chars": 90, "min_count": 1, "max_count": 5},
        "final_url": {"required": False},
    },
    "CALL": {
        "name": "Call Ad",
        "business_name": {"max_chars": 25, "required": True},
        "headline": {"max_chars": 30, "min_count": 2, "max_count": 3},
        "description": {"max_chars": 90, "min_count": 2, "max_count": 2},
        "verification_url": {"required": True},
        "phone_number": {"required": True},
    },
    "SHOPPING": {
        "name": "Shopping Ad (feed)",
        "title": {"max_chars": 150, "required": True},
        "description": {"max_chars": 5000, "required": True},
        "brand": {"required": True},
        "price": {"required": True},
        "availability": {"required": True,
                         "allowed": ["in_stock", "out_of_stock",
                                     "preorder", "backorder"]},
        "condition": {"required": True,
                      "allowed": ["new", "refurbished", "used"]},
        "image_link": {"required": True},
        "google_product_category": {"required": True},
    },
}

VIDEO_SUB_FORMATS = {
    "skippable_in_stream": {
        "headline": {"max_chars": 15, "min_count": 1, "max_count": 1},
        "description": {"max_chars": 70, "min_count": 1, "max_count": 1},
        "cta": {"max_chars": 10, "required": False},
    },
    "bumper": {
        "video_duration_sec": {"exact": 6, "required": True},
    },
    "non_skippable_in_stream": {
        "headline": {"max_chars": 15, "min_count": 1, "max_count": 1},
        "description": {"max_chars": 70, "min_count": 1, "max_count": 1},
        "video_duration_sec": {"min": 15, "max": 30, "required": True},
    },
    "in_feed": {
        "headline": {"max_chars": 15, "min_count": 1, "max_count": 1},
        "description": {"max_chars": 35, "min_count": 1, "max_count": 2},
    },
    "shorts": {
        "video_duration_sec": {"min": 10, "max": 60, "required": True},
    },
}

EXTENSION_LIMITS = {
    "sitelink": {"text": 25, "description1": 35, "description2": 35},
    "callout": {"text": 25, "min_count": 2, "max_count": 20},
    "structured_snippet": {"value": 25, "min_values": 3, "max_values": 10},
}

URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
EXCESSIVE_PUNCT_RE = re.compile(r"[!?]{2,}|[★⭐]{2,}|🔥{2,}")
ALL_CAPS_WORD_RE = re.compile(r"\b[A-ZА-ЯЁ]{4,}\b")


def char_count(text: str) -> int:
    """Number of Unicode code points in text — matches Google's counting."""
    return len(text)


def count_all_caps_words(text: str) -> int:
    return len(ALL_CAPS_WORD_RE.findall(text))


@dataclass
class Finding:
    severity: str  # "OK" | "FAIL" | "WARN"
    field: str
    index: int | None
    message: str
    chars: int | None = None
    limit: int | None = None
    value_preview: str | None = None


@dataclass
class Report:
    format_name: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def fails(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "FAIL"]

    @property
    def warns(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "WARN"]

    def add(self, severity: str, field_name: str, message: str,
            index: int | None = None, chars: int | None = None,
            limit: int | None = None, value: str | None = None) -> None:
        preview = None
        if value is not None:
            preview = value if len(value) <= 60 else value[:57] + "..."
        self.findings.append(Finding(severity, field_name, index, message,
                                     chars, limit, preview))


def validate_text_list(
    items: list[str] | None, spec: dict[str, Any], field_name: str,
    report: Report,
) -> None:
    items = items or []
    max_chars = spec.get("max_chars")
    min_count = spec.get("min_count", 0)
    max_count = spec.get("max_count", 999)

    if len(items) < min_count:
        report.add("FAIL", field_name,
                   f"Need at least {min_count} {field_name}(s), got {len(items)}")
    if len(items) > max_count:
        report.add("FAIL", field_name,
                   f"Max {max_count} {field_name}(s) allowed, got {len(items)}")

    for i, item in enumerate(items, start=1):
        if not isinstance(item, str):
            report.add("FAIL", field_name,
                       f"{field_name}[{i}] is not a string", index=i)
            continue
        n = char_count(item)
        if max_chars and n > max_chars:
            report.add("FAIL", field_name,
                       f"{n} chars exceeds limit {max_chars} (trim {n - max_chars})",
                       index=i, chars=n, limit=max_chars, value=item)
        elif max_chars:
            report.add("OK", field_name,
                       f"{n} chars", index=i, chars=n, limit=max_chars, value=item)

        if EXCESSIVE_PUNCT_RE.search(item):
            report.add("WARN", field_name,
                       "Excessive punctuation — automatic disapproval risk",
                       index=i, value=item)
        if count_all_caps_words(item) > 1:
            report.add("WARN", field_name,
                       "Multiple ALL-CAPS words — editorial review risk",
                       index=i, value=item)


def validate_single_text(
    text: str | None, spec: dict[str, Any], field_name: str, report: Report,
) -> None:
    required = spec.get("required", False)
    if text is None:
        if required:
            report.add("FAIL", field_name, "Required field missing")
        return
    if not isinstance(text, str):
        report.add("FAIL", field_name, "Must be a string")
        return
    max_chars = spec.get("max_chars")
    n = char_count(text)
    if max_chars and n > max_chars:
        report.add("FAIL", field_name,
                   f"{n} chars exceeds limit {max_chars} (trim {n - max_chars})",
                   chars=n, limit=max_chars, value=text)
    elif max_chars:
        report.add("OK", field_name,
                   f"{n} chars", chars=n, limit=max_chars, value=text)


def validate_url(url: str | None, field_name: str, report: Report,
                 required: bool = True) -> None:
    if url is None:
        if required:
            report.add("FAIL", field_name, "Required URL missing")
        return
    if not isinstance(url, str) or not URL_RE.match(url):
        report.add("FAIL", field_name,
                   "Invalid URL format (must be http:// or https://)")
    else:
        report.add("OK", field_name, "valid URL")


def validate_enum(value: str | None, allowed: list[str], field_name: str,
                  report: Report, required: bool = True) -> None:
    if value is None:
        if required:
            report.add("FAIL", field_name, "Required field missing")
        return
    if value not in allowed:
        report.add("FAIL", field_name,
                   f"Value '{value}' not in allowed {allowed}")


def validate_extensions(creative: dict[str, Any], report: Report) -> None:
    sitelinks = creative.get("sitelinks") or []
    for i, sl in enumerate(sitelinks, start=1):
        text = sl.get("text", "")
        n = char_count(text)
        if n > EXTENSION_LIMITS["sitelink"]["text"]:
            report.add("FAIL", "sitelink",
                       f"text {n} > 25 chars", index=i, value=text)
        else:
            report.add("OK", "sitelink", f"text {n} chars",
                       index=i, value=text)
        for d_field in ("description1", "description2"):
            d = sl.get(d_field)
            if d is None:
                continue
            n = char_count(d)
            if n > EXTENSION_LIMITS["sitelink"][d_field]:
                report.add("FAIL", f"sitelink.{d_field}",
                           f"{n} > 35 chars", index=i, value=d)

    callouts = creative.get("callouts") or []
    for i, c in enumerate(callouts, start=1):
        if not isinstance(c, str):
            continue
        n = char_count(c)
        if n > EXTENSION_LIMITS["callout"]["text"]:
            report.add("FAIL", "callout",
                       f"{n} > 25 chars", index=i, value=c)
        else:
            report.add("OK", "callout", f"{n} chars",
                       index=i, value=c)
    if 0 < len(callouts) < EXTENSION_LIMITS["callout"]["min_count"]:
        report.add("WARN", "callouts",
                   f"Need ≥{EXTENSION_LIMITS['callout']['min_count']} for display, "
                   f"got {len(callouts)}")

    snippets = creative.get("structured_snippets") or []
    for i, sn in enumerate(snippets, start=1):
        values = sn.get("values", [])
        if len(values) < EXTENSION_LIMITS["structured_snippet"]["min_values"]:
            report.add("FAIL", "structured_snippet",
                       f"Need ≥3 values, got {len(values)}", index=i)
        if len(values) > EXTENSION_LIMITS["structured_snippet"]["max_values"]:
            report.add("FAIL", "structured_snippet",
                       f"Max 10 values, got {len(values)}", index=i)
        for j, v in enumerate(values, start=1):
            if not isinstance(v, str):
                continue
            n = char_count(v)
            if n > EXTENSION_LIMITS["structured_snippet"]["value"]:
                report.add("FAIL", f"snippet[{i}].value",
                           f"value[{j}] {n} > 25 chars", index=j, value=v)


def validate_video(creative: dict[str, Any], report: Report) -> None:
    sub = creative.get("sub_format")
    if sub not in VIDEO_SUB_FORMATS:
        report.add("FAIL", "sub_format",
                   f"Required: one of {list(VIDEO_SUB_FORMATS)}")
        return
    spec = VIDEO_SUB_FORMATS[sub]
    for key, rules in spec.items():
        if key == "video_duration_sec":
            dur = creative.get("video_duration_sec")
            if dur is None:
                if rules.get("required"):
                    report.add("FAIL", key, "Required field missing")
                continue
            if "exact" in rules and dur != rules["exact"]:
                report.add("FAIL", key,
                           f"Must be exactly {rules['exact']}s, got {dur}s")
                continue
            if "min" in rules and dur < rules["min"]:
                report.add("FAIL", key,
                           f"Min {rules['min']}s, got {dur}s")
                continue
            if "max" in rules and dur > rules["max"]:
                report.add("FAIL", key,
                           f"Max {rules['max']}s, got {dur}s")
                continue
            report.add("OK", key, f"{dur}s")
            continue
        value = creative.get(key)
        if "min_count" in rules:
            items = value if isinstance(value, list) else (
                [value] if isinstance(value, str) else []
            )
            validate_text_list(items, rules, key, report)
        else:
            validate_single_text(value, rules, key, report)


def validate_shopping(creative: dict[str, Any], report: Report) -> None:
    spec = FORMATS["SHOPPING"]
    for key, rules in spec.items():
        if key == "name":
            continue
        value = creative.get(key)
        if "allowed" in rules:
            validate_enum(value, rules["allowed"], key, report,
                          rules.get("required", False))
        elif "max_chars" in rules:
            validate_single_text(value, rules, key, report)
        else:
            if rules.get("required") and value is None:
                report.add("FAIL", key, "Required field missing")
            elif value is not None:
                report.add("OK", key, "present")
    image_link = creative.get("image_link")
    if image_link:
        validate_url(image_link, "image_link", report, required=True)
    title = creative.get("title", "")
    if title and char_count(title) > 70:
        report.add("WARN", "title",
                   "First 70 chars are critical for CTR — ensure key attributes "
                   "(brand + model + key attribute) appear early")


def validate_creative(creative: dict[str, Any]) -> Report:
    fmt_raw = creative.get("format", "").upper().replace("-", "_")
    if fmt_raw not in FORMATS:
        report = Report(format_name=f"Unknown ({fmt_raw or 'missing'})")
        report.add("FAIL", "format",
                   f"Unknown format. Allowed: {list(FORMATS)}")
        return report

    spec = FORMATS[fmt_raw]
    report = Report(format_name=f"{fmt_raw} — {spec.get('name', '')}")

    if fmt_raw == "VIDEO":
        validate_video(creative, report)
        return report

    if fmt_raw == "SHOPPING":
        validate_shopping(creative, report)
        return report

    if "headline" in spec:
        validate_text_list(creative.get("headlines"), spec["headline"],
                           "headline", report)
    if "description" in spec:
        validate_text_list(creative.get("descriptions"), spec["description"],
                           "description", report)
    if "long_headline" in spec:
        lh = creative.get("long_headline")
        items = lh if isinstance(lh, list) else ([lh] if isinstance(lh, str) else [])
        validate_text_list(items, spec["long_headline"], "long_headline", report)
    if "short_description" in spec:
        validate_single_text(creative.get("short_description"),
                             spec["short_description"], "short_description", report)
    if "business_name" in spec:
        validate_single_text(creative.get("business_name"),
                             spec["business_name"], "business_name", report)
    if "path1" in spec:
        validate_single_text(creative.get("path1"), spec["path1"],
                             "path1", report)
    if "path2" in spec:
        validate_single_text(creative.get("path2"), spec["path2"],
                             "path2", report)
    if "final_url" in spec:
        validate_url(creative.get("final_url"), "final_url", report,
                     spec["final_url"].get("required", False))
    if "verification_url" in spec:
        validate_url(creative.get("verification_url"), "verification_url",
                     report, spec["verification_url"].get("required", False))
    if "phone_number" in spec:
        phone = creative.get("phone_number")
        if not phone:
            report.add("FAIL", "phone_number", "Required field missing")
        else:
            report.add("OK", "phone_number", "present")

    validate_extensions(creative, report)

    headlines = creative.get("headlines") or []
    if 0 < len(headlines) < 8 and fmt_raw == "RSA":
        report.add("WARN", "headlines",
                   f"Only {len(headlines)} headlines — Google recommends 8-10 "
                   "for best ad strength")
    descriptions = creative.get("descriptions") or []
    if 0 < len(descriptions) < 3 and fmt_raw == "RSA":
        report.add("WARN", "descriptions",
                   f"Only {len(descriptions)} descriptions — recommend 3-4")

    return report


def render_report(report: Report) -> str:
    out = []
    out.append("=" * 64)
    out.append("=== Google Ads Creative Validator ===")
    out.append("=" * 64)
    out.append(f"Format: {report.format_name}")
    out.append("")

    grouped: dict[str, list[Finding]] = {}
    for f in report.findings:
        grouped.setdefault(f.field, []).append(f)

    for field_name, findings in grouped.items():
        out.append(f"{field_name}:")
        for f in findings:
            marker = {"OK": "  ✓ OK ", "FAIL": "  ✗ FAIL", "WARN": "  ! WARN"}.get(
                f.severity, f"  {f.severity}")
            idx_str = f"[{f.index}]" if f.index is not None else "   "
            chars_str = ""
            if f.chars is not None and f.limit is not None:
                chars_str = f" {f.chars}/{f.limit}"
            elif f.chars is not None:
                chars_str = f" {f.chars}c"
            val_str = f'  "{f.value_preview}"' if f.value_preview else ""
            line = f"{marker} {idx_str}{chars_str}  {f.message}{val_str}"
            out.append(line)
        out.append("")

    out.append("=" * 64)
    n_fails = len(report.fails)
    n_warns = len(report.warns)
    if n_fails == 0 and n_warns == 0:
        verdict = "ALL CHECKS PASSED"
    elif n_fails == 0:
        verdict = f"PASSED with {n_warns} warning(s) (review optional)"
    else:
        verdict = f"{n_fails} hard fail(s), {n_warns} warning(s). Fix before launch."
    out.append(f"VERDICT: {verdict}")
    out.append("=" * 64)
    return "\n".join(out)


def load_creative(source: str) -> dict[str, Any]:
    if source == "-":
        raw = sys.stdin.read()
    else:
        with open(source, encoding="utf-8") as fh:
            raw = fh.read()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        print("ERROR: PyYAML not installed. Install with `pip install pyyaml`, "
              "or pass input as JSON.", file=sys.stderr)
        sys.exit(2)
    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError as e:
        print(f"ERROR: Failed to parse YAML: {e}", file=sys.stderr)
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Google Ads creative against character limits.",
    )
    parser.add_argument(
        "source",
        help="Path to YAML/JSON file, or '-' for stdin.",
    )
    args = parser.parse_args()

    creative = load_creative(args.source)
    if not isinstance(creative, dict):
        print("ERROR: Input must be a YAML/JSON object (dict) at the top level.",
              file=sys.stderr)
        return 2

    report = validate_creative(creative)
    print(render_report(report))

    if any(f.field == "format" and f.severity == "FAIL"
           for f in report.findings):
        return 3
    return 1 if report.fails else 0


if __name__ == "__main__":
    sys.exit(main())
