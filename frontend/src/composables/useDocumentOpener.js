import { ref } from 'vue';

/**
 * Opens recruitment documents that live in a private S3 bucket.
 *
 * The files aren't publicly reachable, so a click has to fetch a short-lived
 * presigned URL before it can navigate anywhere.
 */
export function useDocumentOpener(onError) {
  // Which document is currently being fetched, for per-button loading state.
  const openingDoc = ref(null);

  async function openDocument(key, fetchUrl) {
    // The tab must be opened synchronously inside the click handler. Opening it
    // after the await would be treated as a popup and blocked.
    const tab = window.open('', '_blank');
    if (tab) tab.opener = null;
    openingDoc.value = key;
    try {
      const url = await fetchUrl();
      if (tab) tab.location = url;
      else window.location.href = url;
    } catch (err) {
      console.error('Failed to open document:', err);
      tab?.close();
      onError?.(err.response?.data?.detail || 'Could not open the document');
    } finally {
      openingDoc.value = null;
    }
  }

  return { openingDoc, openDocument };
}
