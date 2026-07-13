export function connectEvents({ onStatus, onUpdate }) {
  let source = null;
  let retryTimer = null;
  let attempts = 0;
  let stopped = false;

  const scheduleReconnect = () => {
    if (stopped || retryTimer) return;
    const delay = Math.min(1000 * 2 ** attempts, 30000);
    attempts += 1;
    retryTimer = window.setTimeout(() => {
      retryTimer = null;
      open();
    }, delay);
  };

  const handleUpdate = () => {
    onUpdate();
  };

  const open = () => {
    if (stopped) return;
    if (source) source.close();
    source = new EventSource("/api/events");
    source.onopen = () => {
      attempts = 0;
      onStatus("connected");
    };
    source.onmessage = handleUpdate;
    source.addEventListener("update", handleUpdate);
    source.addEventListener("change", handleUpdate);
    source.onerror = () => {
      onStatus("disconnected");
      source.close();
      source = null;
      scheduleReconnect();
    };
  };

  open();
  return () => {
    stopped = true;
    if (retryTimer) window.clearTimeout(retryTimer);
    if (source) source.close();
  };
}
