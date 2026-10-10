# Security Protocol (shared contract, frontend and backend must match exactly)

TLS is always on. On top of TLS, **every API request and response body is encrypted at the application layer**, carries an expiry and a one-time nonce, and is rejected if replayed or late.

## 1. Session key exchange (ECDH)

WebCrypto-compatible, works in all modern browsers.

1. Client generates an ephemeral **ECDH P-256** key pair (`crypto.subtle.generateKey`).
2. `POST /api/v1/crypto/handshake` with `{ client_public_key (base64 raw), client_ts }`, the only plaintext JSON endpoint (it carries no secrets).
3. Server generates its own ephemeral P-256 key pair, derives the shared secret, runs **HKDF-SHA256** (salt = random 32 bytes, info = `formalie-envelope-v1`) → 256-bit key. Stores `{key_id → key, tenant_host, expires_at}` in Redis (TTL 30 min, sliding).
4. Response: `{ key_id, server_public_key, salt, expires_at }`. Client derives the same key and keeps it **in memory only** (never localStorage).
5. When the key expires or the server returns `FRM-SEC-1004`, the client re-handshakes transparently and retries once.

Anonymous public-form respondents perform the same handshake (scoped to the form's tenant host).

## 2. Request envelope

All methods (GET, POST, PUT, PATCH, DELETE):

```json
{
  "kid": "key id from handshake",
  "iv": "base64 12-byte random",
  "ts": 1790000000000,
  "nonce": "base64 16-byte random",
  "ct": "base64 AES-256-GCM ciphertext of the JSON payload"
}
```

- Payload = `{ "method": "POST", "path": "/api/v1/forms", "query": {...}, "body": {...} }`. Binding method + path inside the ciphertext stops an envelope being replayed against another endpoint.
- AAD (additional authenticated data) = `kid|ts|nonce`.
- **GET/DELETE:** envelope sent in header `X-Formalie-Envelope` (base64url JSON); real query params live inside the ciphertext, not in the URL.
- **POST/PUT/PATCH:** envelope is the body, `Content-Type: application/vnd.formalie.enc+json`.
- **Expiry:** server rejects if `|now − ts| > 60 s` (`FRM-SEC-1002`).
- **Replay:** server stores `nonce` in Redis with `SET NX EX 120`; already present → reject (`FRM-SEC-1003`).

## 3. Response envelope

Same structure (`kid, iv, ts, nonce, ct`), encrypted with the session key. Client checks `ts` freshness and decrypts. Error responses are encrypted too, except handshake failures.

## 4. Exceptions (explicit, documented)

- File uploads: browser uploads directly to object storage via **pre-signed, expiring URLs** (TLS); the request that obtains the URL is enveloped. Files are encrypted at rest. Respondents' files (public forms) are checked by their bytes (real pictures for image questions, no programs for file questions), never served from a public address, and attached to exactly one response (03-DECISIONS → 88).
- File downloads/exports: signed, short-lived URLs.
- `/api/health` and the handshake endpoint.

## 5. Authentication tokens (Fernet)

- **Access token:** Fernet token, sent as `Authorization: Bearer <token>`. Payload: `{ sub (user uuid), tid (tenant uuid), oid (organisation uuid), sid (session uuid), jti, roles_ver, mfa: true, iat }`. Valid **15 min** (Fernet `decrypt(ttl=900)`).
- **Refresh token:** Fernet token, valid **7 days** (configurable per tenant), **single use and rotated** on every refresh. Stored server-side as a hash with a `family_id`; reuse of an old refresh token revokes the whole family (`FRM-AUTH-1012`).
- **Idle timeout:** a session ends after **60 minutes without activity** (sliding: every API call and every refresh counts as activity; owner, 2026-10-02, at least 1 hour). Absolute limit = refresh-token lifetime (7 days). Default per workspace, adjustable in Settings → Security. An idle-expired refresh answers `FRM-AUTH-1001`, and the client shows sign-in with "Your session expired".
- An unknown or expired access token answers `FRM-AUTH-1001` (never `1010`), so the client always tries the refresh cookie before signing anyone out.
- Fernet tokens include a timestamp and random IV, so **two tokens are never identical even for the same payload**.
- Access tokens can be revoked early via a session (`sid`) deny-list in Redis (logout, password change, admin reset).
- Browser storage: access token in memory; refresh token in an `HttpOnly; Secure; SameSite=Strict` cookie scoped to the tenant subdomain, path `/api/v1/auth/refresh`.
- Keys: `FERNET_KEYS` list (MultiFernet) to allow key rotation.

## 6. CSRF

- `GET /api/v1/auth/csrf` returns a CSRF token = Fernet token `{ sid, nonce, iat }`, **TTL 2 h**.
- Sent in header `X-CSRF-Token` on every state-changing request; must match the session; expired → `FRM-SEC-1006`.
- Pre-login forms (login, signup, OTP, forgot password, public form submit) use a pre-session CSRF token bound to the handshake `kid`.
- Client order: obtain the CSRF token **before** sealing a state-changing envelope (fetching it may re-handshake; the envelope must use the final key).

## 7. Login and OTP

1. Credentials (or OAuth callback) → server returns `{ challenge_id, channels }`, **no tokens yet**.
2. OTP screen: 6 digits, valid 5 min, max 5 attempts, resend after 60 s (max 3), email by default; TOTP authenticator and SMS as options. Admins must use MFA (enforced).
3. On success → access + refresh tokens issued.

## 8. Other rules

- Passwords hashed with **Argon2id**.
- Rate limiting on **every** endpoint (Redis sliding window) by IP, user, tenant and endpoint; stricter on auth, OTP and public submit.
- Security headers: HSTS, CSP (per-form `frame-ancestors` for embeds), X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
- Secrets never logged (passwords, OTPs, tokens, keys, plaintext of sensitive fields).

## 9. API service (third-party callers, F13)

Applications call form endpoints at `https://api.formalie.com/{apiKey}/{endpoint}` (development `api.formalie.dev`). These callers are other organisations' software, so the API service uses standard, widely supported protections instead of the portal envelope:

- **TLS only** (HSTS); plain HTTP refused.
- **Address ≠ secret.** `{apiKey}` is a random public routing handle (not an id, not encrypted, 03-DECISIONS → 61).
- **Bearer tokens:** static tokens (shown once, stored as a hash, test / live prefix, expiry, scopes) or dynamic tokens (client id + secret → short-lived signed token from `/{apiKey}/token`). Token and URL must belong to the same organisation.
- **Optional request signing:** HMAC-SHA256 of method, path, timestamp and body with a per-client secret; requests older than 5 minutes or replayed are refused.
- **Access rules:** allow / block by IP / range, domain (browser callers via Origin), region and country; block wins. Rate limits per token, IP and endpoint (`429` with `Retry-After`).
- **Least data:** POST / PUT accept only the chosen fields (validated with the form's own rules); GET returns only the chosen fields.
- **Audit and logs:** every management change audited (`api.*`); request logs never store tokens; bodies only when switched on, with sensitive fields masked.

## 10. Encrypted references, no real ids outside the server (owner, 2026-10-03)

- The API never sends a database id to a browser. Every id in every response (`id`, `*_id`, ids inside lists, file addresses such as `/files/{ref}`) is an **encrypted reference**: one AES-256 block of the id under a server-only key plus a 4-byte HMAC-SHA256 tag, base64url → 27 characters (`server/mock/core/ids.ts` is the reference implementation).
- Stable: the same record always has the same reference, so bookmarks and shared portal links keep working. Opaque: a reference reveals nothing about the id, and without the key nobody can make one for another record.
- Requests: references in route params, query and body are decrypted at the API edge; a reference with a wrong tag is rejected before any lookup; a raw id typed into an address is **never** accepted.
- Public form links use a separate random `public_key` (decision 80), not an encrypted id.
- Keys live only on the API (managed secret, versioned for rotation). Access checks still run on every request, references stop guessing and leaking ids; permissions decide access.
- Not secret on purpose: catalogue names (`risk_assessment`, `sys_preset_soft`) and plain list options in the address bar (`?status=draft`, `?view=table`), they carry no record ids or personal data.

## 11. Payments: no double charge, idempotency (F24, owner 2026-10-10)

Payments go through the processor (Payoneer). Formalie never sees, stores or logs a card number; it keeps the brand, the last four digits, the expiry and the processor's reference. The rules below are in the mock today (`server/mock/billing/`, tested in `test/billing/safety.test.ts`) and the backend must follow them exactly.

1. **The server decides the amount.** The app only says which plan and period; the price, the credit for unused time and the total are worked out on the server. No request carries an amount the server trusts.
2. **One decision, one request key.** Every request that can move money (`POST /billing/change`, `/billing/checkout`, `/billing/checkout/{id}/complete`) carries `request_key`, made by the app once per decision (the confirm dialog makes it when it opens; a checkout's completion uses the checkout's id). The server remembers keys for 24 hours per workspace: the same key with the same request answers with the first result and does nothing again; the same key with a different request is refused (`409 FRM-BILL-1005`); a missing key is refused (`FRM-GEN-1002`). Double clicks, two tabs, a retry after a dropped connection: all one charge.
3. **One billing change at a time per workspace.** A lock is held while a change runs; a second change at the same moment (two admins) is refused (`409 FRM-BILL-1004`). The backend uses a database row lock (or advisory lock) on the workspace's subscription.
4. **One open checkout per workspace.** Starting a checkout cancels any open one (its pending payment becomes failed), so two checkouts can never both be paid. A checkout expires after 30 minutes (`410 FRM-BILL-1002`) and completes at most once.
5. **Every charge is written down first, under one reference.** Before the processor is asked, a payment is saved as `pending` with a unique reference: `checkout:{checkout id}`, `upgrade:{request key}` or `renew:{workspace}:{period end}`. The same reference is sent to the processor as its idempotency key / merchant transaction id, so the processor refuses a duplicate too. A crash between the two steps leaves a `pending` payment that is completed or failed by the processor's notification or the daily reconciliation, never charged again. A renewal of the same period can only be charged once, however often the renewal job runs.
6. **Payments only move forward.** pending → paid / failed, failed → paid (a retry of the same reference, e.g. a card added while past due), paid → refunded. A late or repeated event never undoes a later state.
7. **Only the processor's signed notification confirms a payment** (backend), never the browser coming back from the checkout. Webhook `POST /billing/webhooks/payoneer`: HMAC-SHA256 signature over `{timestamp}.{raw body}` with the shared secret (`NUXT_PAYONEER_WEBHOOK_SECRET`; none configured = everything refused), compared in constant time, at most 5 minutes old; each event id handled once; the payment found by its reference with the amount and currency matching what was written down; the backend also asks the processor for the payment's status before acting. Anything that fails → `400 FRM-BILL-1006`, logged as a warning, nothing changes. The signature scheme is a placeholder until Payoneer's own is known; the checks stay the same.
8. **Daily reconciliation** (backend): our payments and invoices against the processor's transactions; differences (paid there, pending here; charged twice; amount mismatch) are flagged to Formalie staff in the platform admin.
9. **Refunds** only by Formalie staff in the platform admin, audited, through the processor (never by editing our records).
10. **The checkout frame** only loads the processor's own pages (Content-Security-Policy `frame-src` limited to Payoneer's hosts when connected).
11. **Access and record.** Reading billing needs `settings.view`, changing it `settings.manage`; every change, payment and notification is in the audit trail (notifications as the system actor "Payoneer").

## 12. Custom CSS on forms (leftovers L5, owner 2026-10-10)

Code written by customers runs on Formalie's pages, so it is never trusted:

- **Cleaned the same way everywhere** (`shared/utils/forms/custom-css.ts`): in the designer (to show what was left out) and wherever a form is drawn. Only the cleaned version is ever served; what the person wrote is stored so they can keep editing it.
- **Fenced:** every selector is placed inside the form box (`[data-form-css]`, the form's `<main>`); `:root`, `html` and `body` mean the box. The box has `contain: paint`, so nothing is drawn outside it. The page frame (organisation bar, "Secured by Formalie") can't be restyled or covered.
- **Left out:** every at-rule except @media, @supports and @container (no @import, @font-face, @keyframes …); anything that loads from elsewhere (url(), image-set(), src()), so there is no tracking or data leakage through requests; script-like values (expression(), javascript:, behavior, -moz-binding); backslash escapes (they can spell any of these); `<` (it could close the style element); fixed positioning.
- **Limits:** 20,000 characters, 500 rules. **Plan feature** (Professional and up): saving a change needs the plan (FRM-PLAN-1002), and public pages leave the CSS out while the plan doesn't include it. **Audited:** every change (`forms.custom_css_changed`, with its length and how much was left out).

## 13. Honest note

App-layer encryption protects against TLS-terminating proxies, logging leaks and traffic inspection; it does not protect against a compromised browser or device. It adds CPU cost, so keep payloads lean and paginate.
