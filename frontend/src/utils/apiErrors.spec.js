import { describe, expect, it } from 'vitest';
import { apiErrorMessage } from './apiErrors.js';

const failed = (status, data) => ({ response: { status, data } });

describe('apiErrorMessage', () => {
  it("adds the server's reason to what failed", () => {
    const err = failed(400, { detail: "Discount code 'SAVE10' already exists for this event" });
    expect(apiErrorMessage(err, 'Failed to create discount code'))
      .toBe("Failed to create discount code: Discount code 'SAVE10' already exists for this event");
  });

  it('passes a permission refusal through', () => {
    const err = failed(403, { detail: "You don't have permission to create discount codes for this event" });
    expect(apiErrorMessage(err, 'Failed to create discount code'))
      .toBe("Failed to create discount code: You don't have permission to create discount codes for this event");
  });

  it('turns validation errors into readable text instead of [object Object]', () => {
    const err = failed(422, {
      detail: [
        { loc: ['body', 'discount_value'], msg: 'Input should be greater than 0' },
        { loc: ['body', 'max_uses'], msg: 'Input should be greater than 0' },
      ],
    });
    expect(apiErrorMessage(err, 'Failed to create discount code')).toBe(
      'Failed to create discount code: discount value: Input should be greater than 0; '
      + 'max uses: Input should be greater than 0',
    );
  });

  it('says when the server could not be reached', () => {
    expect(apiErrorMessage(new Error('Network Error'), 'Failed to delete discount code'))
      .toBe("Failed to delete discount code: couldn't reach the server. Check your connection and try again.");
  });

  it("doesn't show server internals on a 500", () => {
    expect(apiErrorMessage(failed(500, { detail: 'Traceback ...' }), 'Failed to load discount codes'))
      .toBe('Failed to load discount codes: something went wrong on the server. Please try again.');
  });

  it('falls back to what failed when there is no reason', () => {
    expect(apiErrorMessage(failed(404, {}), 'Failed to load usage details')).toBe('Failed to load usage details');
  });
});
