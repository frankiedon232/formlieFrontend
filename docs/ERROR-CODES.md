# Error Codes, Formalie

Format: `FRM-<DOMAIN>-<NNNN>`. Ranges: 1000–1999 client/validation, 5000–5999 server. Each code has an HTTP status, default message (safe for users), and log level. Add new codes here first, then to `app/core/errors/codes.py` and the `error_codes` table seed.

| Code          | HTTP | Message                                                           | Level    |
| ------------- | ---- | ----------------------------------------------------------------- | -------- |
| FRM-GEN-1001  | 400  | Invalid request.                                                  | WARNING  |
| FRM-GEN-1002  | 422  | Some fields are invalid.                                          | INFO     |
| FRM-GEN-1004  | 404  | Not found.                                                        | INFO     |
| FRM-GEN-1009  | 409  | This item was changed by someone else. Reload and try again.      | INFO     |
| FRM-GEN-1029  | 429  | Too many requests. Please slow down.                              | WARNING  |
| FRM-GEN-5000  | 500  | Something went wrong. Our team has been notified.                 | ERROR    |
| FRM-GEN-5003  | 503  | Service temporarily unavailable.                                  | CRITICAL |
| FRM-SEC-1001  | 400  | Secure channel required. (missing/invalid envelope)               | WARNING  |
| FRM-SEC-1002  | 400  | Request expired.                                                  | WARNING  |
| FRM-SEC-1003  | 400  | Duplicate request rejected. (replay)                              | WARNING  |
| FRM-SEC-1004  | 401  | Secure session expired. (re-handshake)                            | INFO     |
| FRM-SEC-1005  | 400  | Request integrity check failed. (decrypt/AAD/path mismatch)       | WARNING  |
| FRM-SEC-1006  | 403  | Security token expired. Refresh the page. (CSRF)                  | INFO     |
| FRM-SEC-1007  | 403  | Request blocked. (suspicious payload)                             | WARNING  |
| FRM-AUTH-1001 | 401  | Session expired. (access token expired → refresh)                 | INFO     |
| FRM-AUTH-1002 | 401  | Invalid email or password.                                        | INFO     |
| FRM-AUTH-1003 | 401  | Invalid or expired code.                                          | INFO     |
| FRM-AUTH-1004 | 429  | Too many attempts. Try again later.                               | WARNING  |
| FRM-AUTH-1005 | 403  | Account disabled. Contact your administrator.                     | INFO     |
| FRM-AUTH-1006 | 403  | Multi-factor authentication required.                             | INFO     |
| FRM-AUTH-1007 | 400  | Password does not meet the policy.                                | INFO     |
| FRM-AUTH-1008 | 400  | This sign-in method is not enabled for this workspace.            | INFO     |
| FRM-AUTH-1010 | 401  | Invalid token.                                                    | WARNING  |
| FRM-AUTH-1011 | 401  | Session revoked.                                                  | INFO     |
| FRM-AUTH-1012 | 401  | Session ended for security reasons. (refresh reuse)               | CRITICAL |
| FRM-AUTH-1013 | 422  | That password is not right. (confirming before a secret is shown) | WARNING  |
| FRM-AUTH-1014 | 403  | This email address can't sign in to this workspace. (allowed domains) | NOTICE   |
| FRM-AUTH-1015 | 403  | Your password has expired. Set a new one. (sign-in opens the reset) | NOTICE   |
| FRM-AUTH-1016 | 403  | Sign-in isn't allowed from this network. (IP allowlist, sign-in and every request) | WARNING  |
| FRM-AUTH-1017 | 409  | This change would lock you out. (`own_domain` / `own_ip`)        | INFO     |
| FRM-AUTH-1018 | 422  | You used this password recently. Choose another one.             | INFO     |
| FRM-PERM-1001 | 403  | You don't have access to this.                                    | WARNING  |
| FRM-TEN-1001  | 404  | Workspace not found.                                              | INFO     |
| FRM-TEN-1002  | 403  | Workspace suspended.                                              | WARNING  |
| FRM-TEN-1003  | 403  | Access denied for this workspace. (token/subdomain mismatch)      | CRITICAL |
| FRM-TEN-1004  | 409  | Subdomain not available.                                          | INFO     |
| FRM-FORM-1001 | 404  | Form not found or not published.                                  | INFO     |
| FRM-FORM-1002 | 400  | Form is closed.                                                   | INFO     |
| FRM-FORM-1003 | 400  | Form has reached its response limit.                              | INFO     |
| FRM-FORM-1004 | 422  | Form cannot be published: fix the listed issues.                  | INFO     |
| FRM-FORM-1005 | 403  | Password required.                                                | INFO     |
| FRM-FORM-1006 | 409  | Slug already in use.                                              | INFO     |
| FRM-FORM-1007 | 409  | This isn't possible while the form is in its current state.       | INFO     |
| FRM-FORM-1008 | 409  | A folder with this name already exists.                           | INFO     |
| FRM-FORM-1009 | 409  | A list with this name already exists.                             | INFO     |
| FRM-FORM-1010 | 409  | A theme with this name already exists.                            | INFO     |
| FRM-FORM-1011 | 403  | System templates can’t be changed. Duplicate it to make your own. | INFO     |
| FRM-FORM-1012 | 409  | A template with this name already exists.                         | INFO     |
| FRM-FORM-1013 | 409  | This folder still has forms. Move them to another folder first.   | INFO     |
| FRM-FORM-1014 | 403  | System themes can’t be changed. Duplicate it to make your own.    | INFO     |
| FRM-FORM-1020 | 422  | Two options share the same value. Each value must be different.  | INFO     |
| FRM-FORM-1021 | 422  | An option has no option above it. Choose where it belongs.       | INFO     |
| FRM-FORM-1022 | 422  | This list has more options than it can hold: 20,000, or 200,000 when it is large. | INFO |
| FRM-RESP-1001 | 422  | Submission is invalid.                                            | INFO     |
| FRM-RESP-1002 | 400  | Verification failed. (captcha)                                    | WARNING  |
| FRM-RESP-1003 | 409  | This form was already submitted from this session.                | WARNING  |
| FRM-FILE-1001 | 400  | File type not allowed.                                            | INFO     |
| FRM-FILE-1002 | 413  | File too large.                                                   | INFO     |
| FRM-FILE-1003 | 400  | File failed security scan.                                        | WARNING  |
| FRM-EXP-1001  | 404  | Export not found or expired.                                      | INFO     |
| FRM-DEST-1001 | 400  | Could not connect to destination database.                        | WARNING  |
| FRM-API-1001  | 409  | This endpoint name is already used in your organisation.          | INFO     |
| FRM-API-1002  | 422  | Publish the form before it can be an endpoint.                    | INFO     |
| FRM-API-1003  | 409  | A service with this name already exists.                          | INFO     |
| FRM-API-1004  | 409  | This token was revoked and can no longer be changed.              | INFO     |
| FRM-API-1005  | 409  | Revoke the token before deleting it.                              | INFO     |
| FRM-API-1006  | 404  | There is no endpoint at this address.                             | INFO     |
| FRM-API-1007  | 503  | This endpoint is switched off.                                    | INFO     |
| FRM-API-1008  | 405  | This endpoint does not answer this method.                        | INFO     |
| FRM-API-1009  | 403  | This token may not call this endpoint or method.                  | WARNING  |
| FRM-API-1010  | 401  | Send a valid token as Authorization: Bearer <token>.              | WARNING  |
| FRM-API-1011  | 400  | The Formalie-Key header is missing (POST) or not valid (short, weak, wrong characters). | INFO     |
| FRM-API-1012  | 401  | Retired 2026-10-06 (signed calls removed); kept so it is not reused. | WARNING  |
| FRM-API-1013  | 404  | There is no record with this id.                                  | INFO     |
| FRM-API-1014  | 422  | Some fields can not be sent to this endpoint.                     | INFO     |
| FRM-API-1015  | 403  | This caller is not allowed by the access rules.                   | WARNING  |
| FRM-API-1016  | 409  | This secret can not be shown (made before secrets were viewable). | INFO     |
| FRM-API-1017  | 415  | Retired 2026-10-06 (bodies are read as JSON whatever is sent).    | INFO     |
| FRM-API-1019  | 422  | This form is not open to the API service (Share → Where people can answer). | INFO     |
| FRM-API-1020  | 409  | This Formalie-Key was already used for a different request (within 24 hours). | INFO     |
| FRM-API-1018  | 413  | The body is too large (1 MB at most; files via the upload step).  | INFO     |
| FRM-ORG-1001  | 409  | An entry with this name already exists.                          | INFO     |
| FRM-ORG-1002  | 409  | Forms still use it. Archive it, or merge it into another one.    | INFO     |
| FRM-PLAN-1001 | 402  | Your plan limit has been reached. Upgrade to continue.            | INFO     |
| FRM-PLAN-1002 | 402  | This feature is not included in your plan.                        | INFO     |

### Client-side codes (raised by the portal, never sent by the server)

| Code         | When                                     | Message                                        |
| ------------ | ---------------------------------------- | ---------------------------------------------- |
| FRM-NET-1000 | fetch failed (offline, DNS, TLS)         | Can't reach the server. Check your connection. |
| FRM-NET-1001 | request aborted (navigation, new query)  | Request cancelled. (never shown)               |
| FRM-NET-1002 | response is neither an envelope nor JSON | Unexpected response from the server.           |

Every code (server + client) needs `errors.<code>` in all `i18n/locales/*.json`; `test/i18n/locales.test.ts` enforces it.
