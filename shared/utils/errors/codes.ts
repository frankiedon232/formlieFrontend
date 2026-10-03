/**
 * Error catalogue mirrored from docs/ERROR-CODES.md.
 * `message` is the English default; the portal shows a translated
 * `errors.<code>` message when one exists (see useErrorHandler).
 */
export interface ErrorCodeDefinition {
  status: number
  message: string
}

export const ERROR_CODES = {
  'FRM-GEN-1001': { status: 400, message: 'Invalid request.' },
  'FRM-GEN-1002': { status: 422, message: 'Some fields are invalid.' },
  'FRM-GEN-1004': { status: 404, message: 'Not found.' },
  'FRM-GEN-1009': { status: 409, message: 'This item was changed by someone else. Reload and try again.' },
  'FRM-GEN-1029': { status: 429, message: 'Too many requests. Please slow down.' },
  'FRM-GEN-5000': { status: 500, message: 'Something went wrong. Our team has been notified.' },
  'FRM-GEN-5003': { status: 503, message: 'Service temporarily unavailable.' },
  'FRM-SEC-1001': { status: 400, message: 'Secure channel required.' },
  'FRM-SEC-1002': { status: 400, message: 'Request expired.' },
  'FRM-SEC-1003': { status: 400, message: 'Duplicate request rejected.' },
  'FRM-SEC-1004': { status: 401, message: 'Secure session expired.' },
  'FRM-SEC-1005': { status: 400, message: 'Request integrity check failed.' },
  'FRM-SEC-1006': { status: 403, message: 'Security token expired. Refresh the page.' },
  'FRM-SEC-1007': { status: 403, message: 'Request blocked.' },
  'FRM-AUTH-1001': { status: 401, message: 'Session expired.' },
  'FRM-AUTH-1002': { status: 401, message: 'Invalid email or password.' },
  'FRM-AUTH-1003': { status: 401, message: 'Invalid or expired code.' },
  'FRM-AUTH-1004': { status: 429, message: 'Too many attempts. Try again later.' },
  'FRM-AUTH-1005': { status: 403, message: 'Account disabled. Contact your administrator.' },
  'FRM-AUTH-1006': { status: 403, message: 'Multi-factor authentication required.' },
  'FRM-AUTH-1007': { status: 400, message: 'Password does not meet the policy.' },
  'FRM-AUTH-1008': { status: 400, message: 'This sign-in method is not enabled for this workspace.' },
  'FRM-AUTH-1010': { status: 401, message: 'Invalid token.' },
  'FRM-AUTH-1011': { status: 401, message: 'Session revoked.' },
  'FRM-AUTH-1012': { status: 401, message: 'Session ended for security reasons.' },
  'FRM-PERM-1001': { status: 403, message: "You don't have access to this." },
  'FRM-TEN-1001': { status: 404, message: 'Workspace not found.' },
  'FRM-TEN-1002': { status: 403, message: 'Workspace suspended.' },
  'FRM-TEN-1003': { status: 403, message: 'Access denied for this workspace.' },
  'FRM-TEN-1004': { status: 409, message: 'Subdomain not available.' },
  'FRM-FORM-1001': { status: 404, message: 'Form not found or not published.' },
  'FRM-FORM-1002': { status: 400, message: 'Form is closed.' },
  'FRM-FORM-1003': { status: 400, message: 'Form has reached its response limit.' },
  'FRM-FORM-1004': { status: 422, message: 'Form cannot be published: fix the listed issues.' },
  'FRM-FORM-1005': { status: 403, message: 'Password required.' },
  'FRM-FORM-1006': { status: 409, message: 'Slug already in use.' },
  'FRM-FORM-1007': { status: 409, message: "This isn't possible while the form is in its current state." },
  'FRM-FORM-1008': { status: 409, message: 'A folder with this name already exists.' },
  'FRM-FORM-1009': { status: 409, message: 'A list with this name already exists.' },
  'FRM-FORM-1010': { status: 409, message: 'A theme with this name already exists.' },
  'FRM-FORM-1011': { status: 403, message: 'System templates can’t be changed. Duplicate it to make your own.' },
  'FRM-FORM-1012': { status: 409, message: 'A template with this name already exists.' },
  'FRM-FORM-1013': { status: 409, message: 'This folder still has forms. Move them to another folder first.' },
  'FRM-FORM-1014': { status: 403, message: 'System themes can’t be changed. Duplicate it to make your own.' },
  'FRM-RESP-1001': { status: 422, message: 'Submission is invalid.' },
  'FRM-RESP-1002': { status: 400, message: 'Verification failed.' },
  'FRM-RESP-1003': { status: 409, message: 'This form was already submitted from this session.' },
  'FRM-FILE-1001': { status: 400, message: 'File type not allowed.' },
  'FRM-FILE-1002': { status: 413, message: 'File too large.' },
  'FRM-FILE-1003': { status: 400, message: 'File failed security scan.' },
  'FRM-EXP-1001': { status: 404, message: 'Export not found or expired.' },
  'FRM-DEST-1001': { status: 400, message: 'Could not connect to destination database.' },
  'FRM-PLAN-1001': { status: 402, message: 'Your plan limit has been reached. Upgrade to continue.' },
  'FRM-PLAN-1002': { status: 402, message: 'This feature is not included in your plan.' },
} as const satisfies Record<string, ErrorCodeDefinition>

export type ErrorCode = keyof typeof ERROR_CODES
