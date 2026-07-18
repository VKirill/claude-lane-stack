import assert from 'node:assert/strict';
import { test } from 'node:test';
import { controllerFacts, lifecycleLabel, runtimeFacts } from './lifecycle.mjs';

test('lifecycle labels distinguish every operator-relevant task phase', () => {
  assert.deepEqual([
    'running',
    'provider_incomplete',
    'awaiting_verification',
    'verifying',
    'accepted',
    'blocked',
  ].map(lifecycleLabel), [
    'Provider running',
    'Provider incomplete',
    'Awaiting verification',
    'Verifying',
    'Accepted',
    'Blocked',
  ]);
});

test('runtime facts expose provider, failure, process, report, and next action', () => {
  assert.deepEqual(runtimeFacts({
    attempt: 2,
    provider: 'grok',
    model: 'grok-4.5',
    failure_class: 'grok_rate_limited',
    fallback_eligible: true,
    pid: 4321,
    running: true,
    exit_code: null,
    heartbeat_age_seconds: 12,
    report_complete: false,
    reason: 'provider_running',
    next_action: 'wait',
  }), [
    'attempt 2',
    'provider grok · grok-4.5',
    'failure grok_rate_limited · fallback eligible',
    'pid 4321 running',
    'exit —',
    'heartbeat 12s',
    'report incomplete',
    'reason provider_running',
    'next wait',
  ]);
  assert.equal(runtimeFacts({
    report_complete: true,
    report_trusted: true,
  })[6], 'report complete (trusted)');
  assert.equal(runtimeFacts({
    report_complete: false,
    report_trusted: false,
    report_reason: 'report_digest_mismatch',
  })[6], 'report incomplete (untrusted:report_digest_mismatch)');
});

test('controller facts summarize the durable run controller', () => {
  assert.deepEqual(controllerFacts({
    status: 'running',
    stage: 'running',
    counts: { total: 4, accepted: 1, blocked: 0, running: 2, pending: 1 },
    last_event: { event: 'task_started', task_id: '003' },
    next_action: 'poll',
    pid: 9001,
    updated_at: '2026-07-18T06:00:00Z',
  }), [
    'status running',
    'stage running',
    'accepted 1/4',
    'blocked 0',
    'running 2',
    'pending 1',
    'last task_started · 003',
    'pid 9001',
    'next poll',
    'updated 2026-07-18T06:00:00Z',
  ]);
  assert.deepEqual(controllerFacts(null), []);
});
