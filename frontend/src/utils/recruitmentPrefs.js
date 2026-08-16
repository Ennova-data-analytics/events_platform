// Per-user recruitment preferences, persisted to localStorage so choices such
// as the department filter survive across sessions (the HR user shouldn't have
// to re-apply their filter every time they open the board). Also stores the
// per-department Calendly links the admin configures for interview invites.
//
// Scoped by user id so shared machines don't leak one reviewer's prefs to
// another. In the real build this could move server-side; the shape stays.

const KEY = 'ennova.recruitment.prefs';

const DEFAULTS = {
  departmentFilter: null, // locked department filter (null = all)
  viewMode: 'kanban',
  calendlyLinks: {}, // { [departmentId]: url }
};

function readAll() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || {};
  } catch {
    return {};
  }
}

function writeAll(all) {
  try {
    localStorage.setItem(KEY, JSON.stringify(all));
  } catch {
    /* storage unavailable - non-critical */
  }
}

export function loadPrefs(userId = 'anon') {
  const all = readAll();
  return { ...DEFAULTS, ...(all[userId] || {}) };
}

export function savePrefs(userId = 'anon', patch = {}) {
  const all = readAll();
  all[userId] = { ...DEFAULTS, ...(all[userId] || {}), ...patch };
  writeAll(all);
  return all[userId];
}

export function getCalendlyLink(userId, departmentId, fallback = '') {
  const prefs = loadPrefs(userId);
  return prefs.calendlyLinks?.[departmentId] || fallback;
}

export function setCalendlyLink(userId, departmentId, url) {
  const prefs = loadPrefs(userId);
  const calendlyLinks = { ...prefs.calendlyLinks, [departmentId]: url };
  return savePrefs(userId, { calendlyLinks });
}
