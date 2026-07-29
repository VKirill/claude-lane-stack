import assert from 'node:assert/strict';
import test from 'node:test';
import { connectEvents } from './sse.js';

test('refresh SSE events notify the board', () => {
  const originalWindow = globalThis.window;
  const originalEventSource = globalThis.EventSource;
  let source;
  class FakeEventSource {
    constructor() {
      this.listeners = new Map();
      source = this;
    }
    addEventListener(name, listener) { this.listeners.set(name, listener); }
    close() {}
  }
  globalThis.window = { setTimeout, clearTimeout };
  globalThis.EventSource = FakeEventSource;
  try {
    let updates = 0;
    const stop = connectEvents({ onStatus() {}, onUpdate() { updates += 1; } });
    source.listeners.get('refresh')();
    assert.equal(updates, 1);
    stop();
  } finally {
    globalThis.window = originalWindow;
    globalThis.EventSource = originalEventSource;
  }
});
