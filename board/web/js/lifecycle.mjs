const LIFECYCLE_LABELS = Object.freeze({
  accepted: 'Accepted',
  awaiting_verification: 'Awaiting verification',
  blocked: 'Blocked',
  cancelled: 'Cancelled',
  failed: 'Provider failed',
  launching: 'Provider starting',
  not_started: 'Not started',
  provider_incomplete: 'Provider incomplete',
  running: 'Provider running',
  stalled: 'Provider stalled',
  unknown: 'Provider state unknown',
  verified: 'Verified; awaiting acceptance',
  verification_failed: 'Verification failed',
  verifying: 'Verifying',
});

export function lifecycleLabel(status) {
  const normalized = String(status ?? '').trim().toLowerCase();
  if (LIFECYCLE_LABELS[normalized]) return LIFECYCLE_LABELS[normalized];
  if (!normalized) return 'Runtime unavailable';
  return normalized.replaceAll('_', ' ').replace(/^./, (character) => character.toUpperCase());
}

export function runtimeFacts(runtime) {
  if (!runtime || typeof runtime !== 'object') return [];
  const attempt = Number.isInteger(runtime.attempt) ? runtime.attempt : '—';
  const pid = Number.isInteger(runtime.pid) ? runtime.pid : '—';
  const process = runtime.running === true ? `${pid} running` : String(pid);
  const exit = Number.isInteger(runtime.exit_code) ? runtime.exit_code : '—';
  const heartbeat = Number.isFinite(runtime.heartbeat_age_seconds)
    ? `${Math.max(0, Math.floor(runtime.heartbeat_age_seconds))}s`
    : '—';
  const report = runtime.report_complete === true
    ? 'complete'
    : runtime.report_complete === false ? 'incomplete' : '—';
  const reportTrust = runtime.report_trusted === true
    ? 'trusted'
    : runtime.report_trusted === false ? `untrusted:${runtime.report_reason || 'unknown'}` : null;
  return [
    `attempt ${attempt}`,
    `pid ${process}`,
    `exit ${exit}`,
    `heartbeat ${heartbeat}`,
    `report ${report}${reportTrust ? ` (${reportTrust})` : ''}`,
    `reason ${runtime.reason || '—'}`,
    `next ${runtime.next_action || '—'}`,
  ];
}

function lastEventLabel(lastEvent) {
  if (typeof lastEvent === 'string') return lastEvent;
  if (!lastEvent || typeof lastEvent !== 'object') return '—';
  const event = lastEvent.event || lastEvent.type || 'event';
  return lastEvent.task_id ? `${event} · ${lastEvent.task_id}` : String(event);
}

export function controllerFacts(controller) {
  if (!controller || typeof controller !== 'object') return [];
  const counts = controller.counts && typeof controller.counts === 'object' ? controller.counts : {};
  const total = Number.isInteger(counts.total) ? counts.total : '—';
  const accepted = Number.isInteger(counts.accepted) ? counts.accepted : '—';
  return [
    `status ${controller.status || '—'}`,
    `stage ${controller.stage || '—'}`,
    `accepted ${accepted}/${total}`,
    `blocked ${Number.isInteger(counts.blocked) ? counts.blocked : '—'}`,
    `running ${Number.isInteger(counts.running) ? counts.running : '—'}`,
    `pending ${Number.isInteger(counts.pending) ? counts.pending : '—'}`,
    `last ${lastEventLabel(controller.last_event)}`,
    `pid ${Number.isInteger(controller.pid) ? controller.pid : '—'}`,
    `next ${controller.next_action || '—'}`,
    `updated ${controller.updated_at || '—'}`,
  ];
}
