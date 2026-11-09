// Saving files the API sends back (requested with responseType: 'blob').

export function saveBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

// The name the server gave the file, if the browser lets us read the header.
export function filenameFromHeaders(headers) {
  const disposition = headers?.['content-disposition'] || '';
  const match = disposition.match(/filename="?([^";]+)"?/i);
  return match ? match[1] : null;
}

// With responseType 'blob' an error body arrives as a Blob, not parsed JSON.
export async function blobErrorDetail(error) {
  let data = error?.response?.data;
  if (data instanceof Blob) {
    try {
      data = JSON.parse(await data.text());
    } catch {
      return null;
    }
  }
  return typeof data?.detail === 'string' ? data.detail : null;
}
