// Fixed order and colours, so a source looks the same on every chart. Validated
// for colour-blind separation against white; the aqua falls below 3:1 contrast,
// so these charts always carry visible values or a table view alongside.
export const REVENUE_SERIES = [
  { key: 'ticket_revenue', label: 'Ticket revenue', color: '#2a78d6' },
  { key: 'charity_ticket_revenue', label: 'Charity tickets', color: '#eb6834' },
  { key: 'donations', label: 'Donations', color: '#1baf7a' },
];

export function formatEuros(amount, { cents = false } = {}) {
  return Number(amount || 0).toLocaleString('en-IE', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: cents ? 2 : 0,
    maximumFractionDigits: cents ? 2 : 0,
  });
}
