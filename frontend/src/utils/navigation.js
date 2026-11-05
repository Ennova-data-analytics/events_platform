// Leave the app for an external page, such as a Stripe checkout. Kept in its
// own module so tests can mock it: jsdom can't navigate.
export function goToExternalUrl(url) {
  window.location.href = url;
}
