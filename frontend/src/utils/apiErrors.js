// Turns an axios error into something a candidate can act on.
//
// The application form is the one place in the app where the person hitting an
// error can't ask us what happened - they just close the tab. So every failure
// mode gets a message that says what went wrong and what to do about it.

// Field names as the API knows them → how a candidate would describe them.
const FIELD_LABELS = {
  full_name: 'your full name',
  email: 'your email address',
  phone: 'your phone number',
  degree: 'your programme',
  year: 'your year',
  department_applied_id: 'your chosen department',
  department_ranking: 'your department ranking',
  cv_s3_key: 'your CV',
  gdpr_consent: 'the consent checkbox',
  answers: 'your answers',
  materials: 'your attached files',
};

// FastAPI 422s carry a list of {loc, msg} objects rather than a string, so
// rendering `detail` directly gives the candidate "[object Object]".
function describeValidationErrors(detail) {
  if (!Array.isArray(detail) || !detail.length) return null;
  const fields = detail
    .map((e) => {
      const name = (e.loc || []).filter((p) => p !== 'body').pop();
      return FIELD_LABELS[name] || (typeof name === 'string' ? name.replace(/_/g, ' ') : null);
    })
    .filter(Boolean);
  const unique = [...new Set(fields)];
  if (!unique.length) return 'Some of the details need checking before we can submit this.';
  if (unique.length === 1) return `Please check ${unique[0]} - it doesn't look quite right.`;
  return `Please check these before submitting: ${unique.join(', ')}.`;
}

/**
 * @param {Error} err     axios error
 * @param {string} what   optional label for the item that failed, e.g. "Your CV"
 */
export function describeSubmissionError(err, what) {
  // No response at all: DNS, offline, CORS, or the server is down.
  if (!err?.response) {
    return "We couldn't reach the server. Check your connection and try again - "
      + 'nothing has been submitted yet.';
  }

  const { status, data } = err.response;
  const detail = typeof data?.detail === 'string' ? data.detail : null;
  const subject = what || 'That file';

  switch (status) {
    case 400:
      return detail || 'Something in the form was missing. Please check and try again.';
    case 409:
      // Cohort closed or not open - most likely for someone who left the form
      // open a while, and completely invisible from their side otherwise.
      return detail
        ? `${detail} If you think this is wrong, reply to our email and we'll sort it out.`
        : 'Applications are closed for this cohort.';
    case 413:
      return `${subject} is too large. Files must be under 10 MB - try compressing it.`;
    case 415:
      return detail ? `${subject}: ${detail}` : `${subject} isn't a supported file type.`;
    case 422:
      return describeValidationErrors(data?.detail)
        || 'Some of the details need checking before we can submit this.';
    case 429:
      return 'Too many submissions from your network in the last few minutes. '
        + 'Wait a minute and try again - this is a limit on our side, not a problem with your application.';
    default:
      if (status >= 500) {
        return 'Something went wrong on our side, not with your application. '
          + "We've been notified - please try again in a minute.";
      }
      return detail || 'Something went wrong. Please try again.';
  }
}
