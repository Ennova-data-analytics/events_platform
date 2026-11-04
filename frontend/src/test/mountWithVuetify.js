import { mount } from '@vue/test-utils';
import { createVuetify } from 'vuetify';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';

// Dialogs teleport to <body>, so components are attached to the document and
// assertions on dialog content query document.body.
export function mountWithVuetify(component, options = {}) {
  const vuetify = createVuetify({ components, directives });
  return mount(component, {
    attachTo: document.body,
    ...options,
    global: { plugins: [vuetify], ...(options.global || {}) },
  });
}

export function byTest(name) {
  return document.body.querySelector(`[data-test="${name}"]`);
}

export function allByTest(name) {
  return [...document.body.querySelectorAll(`[data-test="${name}"]`)];
}
