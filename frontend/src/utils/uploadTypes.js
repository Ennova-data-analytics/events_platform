// Mirrors ALLOWED_UPLOAD_TYPES in backend/api/routers/recruitment.py. The
// backend is the authority - this only drives the file picker's filter and the
// hints shown next to it, so a mismatch means a confusing rejection rather than
// a security hole. Keep the two in step.
export const ACCEPTED_UPLOAD_MIME = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'image/png',
  'image/jpeg',
].join(',');

// Short form for field labels and hints.
export const ACCEPTED_UPLOAD_LABEL = 'PDF, Word, PowerPoint, PNG or JPEG';

export const MAX_UPLOAD_MB = 10;
