import { useAuthStore } from '@/stores/auth.store';

export function generateGoogleCalendarUrl(event) {
  const baseUrl = 'https://calendar.google.com/calendar/render';

  const formatGoogleDate = (date) => {
    const d = new Date(date);
    return d.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
  };

  const startDate = formatGoogleDate(event.event_date_start);

  let endDate;
  if (event.event_date_end) {
    endDate = formatGoogleDate(event.event_date_end);
  } else {
    const defaultEnd = new Date(event.event_date_start);
    defaultEnd.setHours(defaultEnd.getHours() + 2);
    endDate = formatGoogleDate(defaultEnd);
  }

  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: event.event_name,
    dates: `${startDate}/${endDate}`,
    details: event.description || '',
    location: event.location || '',
  });

  return `${baseUrl}?${params.toString()}`;
}

export function generateIcsDownloadUrl(eventId) {
  return `/api/events/${eventId}/calendar.ics`;
}


export async function downloadIcsFile(eventId) {
  try {
    const authStore = useAuthStore();
    const token = authStore.token;

    if (!token) {
      throw new Error('Authentication required');
    }

    const url = generateIcsDownloadUrl(eventId);

    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to download calendar file');
    }

    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `event-${eventId}.ics`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error('Error downloading ICS file:', error);
    throw error;
  }
}