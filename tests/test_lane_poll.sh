#!/usr/bin/env bash
# Smoke tests for lane-poll progressive accept helper.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
POLL="$ROOT/bin/lane-poll"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/run/artifacts/001" "$TMP/run/artifacts/002" "$TMP/run/artifacts/003"

# 001 running
echo 999999 > "$TMP/run/artifacts/001/lane-bg.pid"
# fake dead pid → will be unknown or we use a live sleep
# start a real background sleep for 001
sleep 120 &
echo $! > "$TMP/run/artifacts/001/lane-bg.pid"

# 002 done, no report → finish_ready
echo 0 > "$TMP/run/artifacts/002/lane-bg.exit"
echo "[lane-bg] exit=0" > "$TMP/run/artifacts/002/lane-bg.supervisor.log"

# 003 done with report → accepted already
echo 0 > "$TMP/run/artifacts/003/lane-bg.exit"
echo "STATUS: complete" > "$TMP/run/artifacts/003/report.md"

set +e
out="$("$POLL" --run-dir "$TMP/run" 2>&1)"
ec=$?
set -e

echo "$out"
echo "exit=$ec"

echo "$out" | grep -q 'finish_ready=1' || { echo "FAIL: expected finish_ready=1"; exit 1; }
echo "$out" | grep -q 'task=002 status=done report=no' || { echo "FAIL: 002 finish-ready line"; exit 1; }
echo "$out" | grep -q 'task=003 status=done report=yes' || { echo "FAIL: 003 accepted line"; exit 1; }
echo "$out" | grep -q 'task=001 status=running' || { echo "FAIL: 001 running"; exit 1; }
[[ "$ec" -eq 0 ]] || { echo "FAIL: exit should be 0 when finish_ready>0"; exit 1; }

# kill sleep
kill "$(cat "$TMP/run/artifacts/001/lane-bg.pid")" 2>/dev/null || true

# only running, no finish_ready
rm -rf "$TMP/run/artifacts/002" "$TMP/run/artifacts/003"
sleep 60 &
echo $! > "$TMP/run/artifacts/001/lane-bg.pid"
set +e
out2="$("$POLL" --run-dir "$TMP/run" 2>&1)"
ec2=$?
set -e
kill "$(cat "$TMP/run/artifacts/001/lane-bg.pid")" 2>/dev/null || true
echo "$out2"
[[ "$ec2" -eq 2 ]] || { echo "FAIL: expected exit 2 when only running"; exit 1; }

# empty
rm -rf "$TMP/empty/artifacts"
mkdir -p "$TMP/empty"
set +e
"$POLL" --run-dir "$TMP/empty" >/dev/null 2>&1
ec3=$?
set -e
[[ "$ec3" -eq 3 ]] || { echo "FAIL: expected exit 3 empty"; exit 1; }

echo "OK: lane-poll tests passed"
