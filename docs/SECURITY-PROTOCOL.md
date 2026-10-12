# Security Protocol, Platform Admin

The platform admin can see and change the whole of Formalie, so it uses Formalie's security model **plus** stricter rules for staff. Front end and backend must match this file exactly.

## 1. Transport and envelope (same as Formalie)

- TLS always (HSTS, TLS 1.2+). Production with a valid certificate; mkcert only in development.
- Every request and response body is encrypted at the application layer exactly as in Formalie's SECURITY-PROTOCOL §1 to §3 (ECDH P-256 handshake, HKDF-SHA256, AES-256-GCM, `kid / iv / ts / nonce / ct`, method and path inside the ciphertext, AAD `kid|ts|nonce`, 60 s expiry, Redis nonce replay check), with the HKDF info string **`formalie-platform-envelope-v1`** so a Formalie envelope can never be used here and the other way round.
- Handshake `POST /api/v1/crypto/handshake` and `/api/health` are the only plaintext endpoints.
- Session keys in memory only; re-handshake on expiry (`PLT-SEC-1004`).

## 2. Staff accounts

- Only invited staff: the platform owner (or a role with `staff.manage`) adds a profile; the person activates it by email, chooses a password and **must set up an authenticator app (TOTP)** before the first sign-in completes. Ten single-use recovery codes, stored as hashes.
- Passwords: Argon2id, at least 14 characters, checked against a breached-password list kept locally (no outside call), no reuse of the last 10, no expiry unless compromised.
- Sign-in: email + password → TOTP code (or recovery code) → tokens. No SMS, no email codes for staff. 5 failed attempts lock the account for 15 minutes (owner unlocks earlier); every attempt is recorded.
- Optional later: passkeys / hardware keys (open question 3).

## 3. Tokens and sessions

- Fernet tokens like Formalie, with the platform's **own** `FERNET_KEYS` (MultiFernet, rotation): access token 10 minutes, refresh token 12 hours, single use and rotated, family revoked on reuse.
- **Idle timeout 30 minutes**, absolute session limit 12 hours (sign in again daily).
- Access token in memory; refresh token in an `HttpOnly; Secure; SameSite=Strict` cookie scoped to the platform host only (never `.formalie.com`), path `/api/v1/auth/refresh`.
- Sessions list per staff member; sign out one or all; a role or permission change ends the person's sessions.
- CSRF exactly as Formalie §6 (Fernet CSRF token, `X-CSRF-Token` on every change).

## 4. Network

- Optional IP allowlist (office / VPN ranges) at the edge **and** in the API, per role if needed (`PLT-SEC-1010` when refused).
- No CORS: front end and API are same-origin through the platform's Nginx in production (or a single allowed origin when the API is on its own host).
- Strict security headers: CSP without `unsafe-inline` scripts, `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy` all off, `X-Robots-Tag: noindex, nofollow`.

## 5. Step-up confirmation

Sensitive actions ask for the TOTP code again if the last confirmation is older than 5 minutes (`PLT-AUTH-1020` → the app shows a code prompt and retries): revealing personal data, support access, changing roles, approving, money actions, publishing to Formalie, platform settings, exports of personal data.

## 6. Approvals (maker-checker)

Dangerous actions are requested by one staff member and carried out only when **another** staff member with the right permission approves (never the same person, never someone without the permission). The request stores the action, its exact parameters, the reason and an expiry (24 h). Approving runs the action with both names in the audit trail; rejecting closes it with a reason.

Suggested list (owner to confirm, open question 4):

| Action | Approval |
| --- | --- |
| Suspend, close or schedule deletion of a workspace | yes |
| Disable a person on the platform, reset their two-step | yes |
| Support access with write rights | yes (plus the workspace's consent) |
| Manual subscription activation, extension, credit or refund above the threshold | yes |
| Change plan prices or limits, publish plans | yes |
| Change staff roles or permissions, add a platform owner | yes |
| Publish Formalie default data or platform settings | yes (content editors' help articles: optional) |
| Export personal data | yes |

## 7. Permissions

Granular like Formalie's F22 (actions with reach where it applies), checked on every call by address and per item, and followed by every menu, page and button in the front end. Catalogue in API-CONTRACT.md → Roles & access. The built-in **Platform owner** role has everything and can't be changed.

## 8. Audit trail (immutable)

- Every staff action (including reads of personal data, reveals, exports and failed attempts) is recorded: who, role, what, target, before / after, reason, approval id, IP, country, device, request id, time.
- Append-only table: the API's database role can insert but not update or delete; each row carries a hash chained to the previous row (`prev_hash`, `hash = sha256(prev_hash + row)`) so tampering is detectable; a daily job verifies the chain and alerts.
- Kept at least 7 years (configurable); exported to cold storage monthly.
- Actions done in Formalie through the internal admin API are also recorded in Formalie's own audit trail, marked as Formalie support with the staff member's name.

## 9. Data protection

- Least data: lists show names and emails masked (`a•••n@example.org`) until revealed (permission + step-up, audited).
- Respondents' answers, files and submitted data are never shown in the platform, never in analytics.
- No passwords, tokens, secrets, card numbers or full IP addresses in logs; analytics store IP-derived country / city only, never the IP.
- Encrypted id references (Formalie §10) with the platform's own key for platform records; Formalie references passed through as they are.

## 10. Calling Formalie

- Internal admin API: private network only, mutual TLS (client certificate) plus HMAC-SHA256 request signing (key id, timestamp, body hash, 5-minute window, nonce), idempotency key on every change, staff id + approval id + reason in signed headers. See FORMALIE-INTEGRATION.md.
- Database roles: `platform_reader` (read-only, replica, statement time-out 15 s, row cap), `platform_writer` (insert / update only on the platform-owned global tables). Credentials in the secret store, rotated quarterly.

## 11. Honest note

These controls make misuse hard and visible; they don't make a compromised staff device safe. Staff use managed devices, the platform is reachable only from allowed networks where possible, and the owner reviews the audit trail and security events regularly.
