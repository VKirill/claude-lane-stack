#!/usr/bin/env bash
# Progressive accept + anti-join + detached heartbeat fixtures.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/." && pwd)"
export PATH="$ROOT/bin:$PATH"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

RUN="$TMP/.agents/runs/prog-demo"
mkdir -p "$RUN/tasks" "$RUN/artifacts/001" "$RUN/artifacts/002" "$RUN/artifacts/003"

# --- 1) lane-mode-check: multi-task refuses full ---
cat > "$RUN/tasks/001-a.yaml" <<'Y'
id: "001"
title: task a
status: pending
lane: grok
Y
cat > "$RUN/tasks/002-b.yaml" <<'Y'
id: "002"
title: task b
status: pending
lane: grok
Y

set +e
out="$(lane-mode-check --run-dir "$RUN" --mode full --task 001 2>&1)"
ec=$?
set -e
echo "$out"
[[ "$ec" -eq 2 ]] || { echo "FAIL: expected refuse full on multi"; exit 1; }
echo "$out" | grep -q refused_full_on_multi_task || true

set +e
out2="$(lane-mode-check --run-dir "$RUN" --mode start --task 001 2>&1)"
ec2=$?
set -e
[[ "$ec2" -eq 0 ]] || { echo "FAIL: start must be ok: $out2"; exit 1; }

set +e
out3="$(LANE_ALLOW_FULL=1 lane-mode-check --run-dir "$RUN" --mode full --task 001 2>&1)"
ec3=$?
set -e
[[ "$ec3" -eq 0 ]] || { echo "FAIL: override must allow full"; exit 1; }

# single-task full ok
RUN1="$TMP/.agents/runs/single"
mkdir -p "$RUN1/tasks"
cat > "$RUN1/tasks/001-only.yaml" <<'Y'
id: "001"
title: only
status: pending
Y
set +e
lane-mode-check --run-dir "$RUN1" --mode full --task 001 >/dev/null
ec4=$?
set -e
[[ "$ec4" -eq 0 ]] || { echo "FAIL: single-task full should ok"; exit 1; }

# --- 2) progressive poll fixture: accept A while B runs ---
# 001 done no report → finish_ready
echo 0 > "$RUN/artifacts/001/lane-bg.exit"
echo "[lane-bg] exit=0" > "$RUN/artifacts/001/lane-bg.supervisor.log"
# 002 still running
sleep 90 &
echo $! > "$RUN/artifacts/002/lane-bg.pid"
# 003 already accepted
echo 0 > "$RUN/artifacts/003/lane-bg.exit"
echo "STATUS: complete" > "$RUN/artifacts/003/report.md"

set +e
poll_out="$(lane-poll --run-dir "$RUN" 2>&1)"
poll_ec=$?
set -e
echo "$poll_out"
echo "$poll_out" | grep -q 'finish_ready=1' || { echo "FAIL: finish_ready"; exit 1; }
echo "$poll_out" | grep -q 'task=001 status=done report=no' || { echo "FAIL: 001 finish_ready line"; exit 1; }
echo "$poll_out" | grep -q 'task=002 status=running' || { echo "FAIL: 002 running"; exit 1; }
[[ "$poll_ec" -eq 0 ]] || { echo "FAIL: poll exit for finish_ready"; exit 1; }

# simulate MODE=finish + accept 001 without waiting for 002
echo "STATUS: complete
VERIFIED: fixture
" > "$RUN/artifacts/001/report.md"
# sed status on task file
sed -i 's/status: pending/status: done/' "$RUN/tasks/001-a.yaml"

set +e
poll2="$(lane-poll --run-dir "$RUN" 2>&1)"
poll2_ec=$?
set -e
echo "$poll2"
# 001 no longer finish_ready; only 002 running → exit 2
echo "$poll2" | grep -q 'finish_ready=0' || { echo "FAIL: after accept finish_ready=0"; exit 1; }
[[ "$poll2_ec" -eq 2 ]] || { echo "FAIL: expected exit 2 while 002 runs (got $poll2_ec)"; exit 1; }

kill "$(cat "$RUN/artifacts/002/lane-bg.pid")" 2>/dev/null || true

# --- 3) lane-exec auto-heartbeat on activity ---
HB="$TMP/hb/heartbeat.json"
mkdir -p "$TMP/hb"
# short command that prints then sleeps (activity then quiet)
# use low idle so we don't hang; heartbeat-interval 5
set +e
lane-exec --idle 60 --max 30 --label test-hb \
  --heartbeat "$HB" --heartbeat-interval 5 \
  --log "$TMP/hb/exec.log" \
  -- bash -c 'echo hello; sleep 2; echo world; sleep 1' >/dev/null 2>&1
ec_exec=$?
set -e
[[ -f "$HB" ]] || { echo "FAIL: heartbeat not written"; exit 1; }
grep -q 'lane-exec' "$HB" || { echo "FAIL: heartbeat source"; cat "$HB"; exit 1; }
grep -q '"status": "running"' "$HB" || { echo "FAIL: heartbeat status"; cat "$HB"; exit 1; }
echo "heartbeat ok: $(cat "$HB")"

echo "OK: progressive accept fixtures passed"
