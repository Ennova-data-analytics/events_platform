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
// Blob#text is in every browser but not in jsdom; axios hands blob error bodies over as Blobs.
if (!Blob.prototype.text) {
  Blob.prototype.text = function text() {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsText(this);
    });
  };
}
