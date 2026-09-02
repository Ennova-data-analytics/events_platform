// Event lifecycle states, mirroring the check constraint on events.status.
// Only 'Published' events are visible to the public.
export const EVENT_STATUSES = ['Draft', 'Published', 'Cancelled', 'Archived'];

const STATUS_COLORS = {
  Draft: 'default',
  Published: 'success',
  Cancelled: 'error',
  Archived: 'secondary',
};

export function statusColor(status) {
  return STATUS_COLORS[status] || 'default';
}

export function isPublished(status) {
  return status === 'Published';
}
