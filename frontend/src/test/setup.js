// jsdom lacks a few browser APIs Vuetify relies on.
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserver;
globalThis.CSS ??= { supports: () => false };
if (!globalThis.visualViewport) {
  globalThis.visualViewport = { width: 1280, height: 800, addEventListener() {}, removeEventListener() {} };
}
