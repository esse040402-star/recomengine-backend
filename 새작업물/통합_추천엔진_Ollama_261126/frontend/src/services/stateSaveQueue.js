// 저장 순서를 보장합니다. 빠른 클릭으로 과거 응답이 최신 상태를 덮어쓰지 않도록 한 요청씩 보냅니다.
export function createStateSaveQueue(save, notify = () => {}) {
  let pending, active = null, closed = false, failed = false;
  async function drain() {
    while (pending !== undefined && !closed) {
      const value = pending; pending = undefined; notify('saving');
      try { await save(value); failed = false; notify('saved'); }
      catch (error) {
        if (pending === undefined) pending = value;
        failed = true; notify('error', error); throw error;
      }
    }
  }
  function flush() {
    if (closed) return Promise.resolve();
    if (!active && pending !== undefined) active = drain().finally(() => {active = null;});
    return active || Promise.resolve();
  }
  return {
    enqueue(value) { if (!closed) pending = structuredClone(value); },
    flush,
    get dirty() { return pending !== undefined || !!active || failed; },
    close() { closed = true; pending = undefined; },
  };
}
