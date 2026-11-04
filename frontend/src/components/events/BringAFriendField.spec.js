import { afterEach, describe, expect, it } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { byTest, mountWithVuetify } from '@/test/mountWithVuetify.js';
import BringAFriendField from './BringAFriendField.vue';

describe('BringAFriendField', () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
  });

  function mountIt(props = {}) {
    wrapper = mountWithVuetify(BringAFriendField, {
      props: { modelValue: '', buyerEmail: 'bea@example.com', ...props },
    });
  }

  it('explains which email to use', () => {
    mountIt();
    expect(byTest('bring-a-friend-field').textContent).toContain('The one they use for Ennova');
  });

  it('passes typing up', async () => {
    mountIt();
    const input = byTest('friend-email').querySelector('input');
    input.value = 'fay@example.com';
    input.dispatchEvent(new Event('input'));
    await flushPromises();

    expect(wrapper.emitted('update:modelValue').at(-1)).toEqual(['fay@example.com']);
  });

  it('holds its errors until the buyer leaves the field or tries to pay', async () => {
    mountIt({ modelValue: 'bea@example.com' });
    expect(byTest('bring-a-friend-field').textContent).not.toContain('your own email');

    await wrapper.setProps({ showErrors: true });

    expect(byTest('bring-a-friend-field').textContent).toContain("That's your own email");
  });
});
