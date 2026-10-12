# Error Codes, Platform Admin

Format: `PLT-<DOMAIN>-<NNNN>` (different prefix from Formalie's `FRM-` so logs never mix them). Ranges: 1000–1999 client / validation, 5000–5999 server. Each code has an HTTP status, a default message safe to show, and a log level. Add new codes here first, then to `app/core/errors/codes.py` and the front end's error map.

| Code | HTTP | Message | Level |
| --- | --- | --- | --- |
| PLT-GEN-1001 | 400 | Invalid request. | WARNING |
| PLT-GEN-1002 | 422 | Some fields are invalid. | INFO |
| PLT-GEN-1004 | 404 | Not found. | INFO |
| PLT-GEN-1009 | 409 | This item was changed by someone else. Reload and try again. | INFO |
| PLT-GEN-1029 | 429 | Too many requests. Please slow down. | WARNING |
| PLT-GEN-5000 | 500 | Something went wrong. The team has been notified. | ERROR |
| PLT-GEN-5003 | 503 | Service temporarily unavailable. | CRITICAL |
| PLT-SEC-1001 | 400 | Secure channel required. | WARNING |
| PLT-SEC-1002 | 400 | Request expired. | WARNING |
| PLT-SEC-1003 | 400 | Duplicate request rejected. | WARNING |
| PLT-SEC-1004 | 401 | Secure session expired. | INFO |
| PLT-SEC-1005 | 400 | Request integrity check failed. | WARNING |
| PLT-SEC-1006 | 403 | Security token expired. Refresh the page. | INFO |
| PLT-SEC-1010 | 403 | This network is not allowed. | WARNING |
| PLT-AUTH-1001 | 401 | Session expired. | INFO |
| PLT-AUTH-1002 | 401 | Invalid email or password. | INFO |
| PLT-AUTH-1003 | 401 | Invalid or expired code. | INFO |
| PLT-AUTH-1004 | 429 | Too many attempts. Try again later. | WARNING |
| PLT-AUTH-1005 | 403 | Account locked. Ask the platform owner. | WARNING |
| PLT-AUTH-1006 | 403 | Set up your authenticator app to continue. | INFO |
| PLT-AUTH-1007 | 400 | Password does not meet the policy. | INFO |
| PLT-AUTH-1008 | 410 | This activation link has expired. | INFO |
| PLT-AUTH-1011 | 401 | Session revoked. | INFO |
| PLT-AUTH-1012 | 401 | Session revoked for safety. Sign in again. | WARNING |
| PLT-AUTH-1020 | 401 | Confirm with your authenticator code to continue. (step-up) | INFO |
| PLT-PERM-1001 | 403 | Your role doesn't allow this. | INFO |
| PLT-APPR-1001 | 202 | Sent for approval. | INFO |
| PLT-APPR-1002 | 403 | You can't approve your own request. | INFO |
| PLT-APPR-1003 | 409 | This request was already decided or has expired. | INFO |
| PLT-STAFF-1001 | 409 | This email already belongs to a staff member. | INFO |
| PLT-STAFF-1002 | 409 | The platform needs at least one active owner. | INFO |
| PLT-FRM-1001 | 502 | Formalie didn't answer. The action is queued and will be retried. | WARNING |
| PLT-FRM-1002 | 409 | Formalie refused this action. | INFO |
| PLT-FRM-1003 | 403 | The workspace hasn't allowed support access. | INFO |
| PLT-PUB-1001 | 409 | Publishing is already running for this item. | INFO |
| PLT-PUB-1002 | 422 | Some translations are missing. Publish anyway or finish them. | INFO |
| PLT-BILL-1001 | 422 | The amount is above your limit. It needs approval. | INFO |
| PLT-BILL-1002 | 502 | The payment processor refused this action. | WARNING |
| PLT-AN-1001 | 422 | This report asks for too much at once. Narrow the date range or dimensions. | INFO |
