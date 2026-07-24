"""Test package bootstrap.

Gate scripts (check-owns-paths, run-validate, lane-ctl) append every evaluation
to a global ~/.agents/logs/gate-events.jsonl. Tests exercise those scripts as
subprocesses and would otherwise pollute the real observability log with /tmp
fixtures, so disable gate-event logging by default. Tests that need the log opt
back in by passing an explicit path (see tests/test_gate_log.py).
"""
import os

os.environ.setdefault("CLAUDE_LANE_GATE_LOG", "off")
