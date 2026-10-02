# Security Protocol (shared contract — frontend and backend must match exactly)

TLS is always on. On top of TLS, **every API request and response body is encrypted at the application layer**, carries an expiry and a one-time nonce, and is rejected if replayed or late.

## 1. Session key exchange (ECDH)

WebCrypto-compatible, works in all modern browsers.

1. Client generates an ephemeral **ECDH P-256** key pair (`crypto.subtle.generateKey`).
2. `POST /api/v1/crypto/handshake` with `{ client_public_key (base64 raw), client_ts }` — the only plaintext JSON endpoint (it carries no secrets).
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

- File uploads: browser uploads directly to object storage via **pre-signed, expiring URLs** (TLS); the request that obtains the URL is enveloped. Files are encrypted at rest.
- File downloads/exports: signed, short-lived URLs.
- `/api/health` and the handshake endpoint.

## 5. Authentication tokens (Fernet)

- **Access token:** Fernet token, sent as `Authorization: Bearer <token>`. Payload: `{ sub (user uuid), tid (tenant uuid), oid (organisation uuid), sid (session uuid), jti, roles_ver, mfa: true, iat }`. Valid **15 min** (Fernet `decrypt(ttl=900)`).
- **Refresh token:** Fernet token, valid **7 days** (configurable per tenant), **single use and rotated** on every refresh. Stored server-side as a hash with a `family_id`; reuse of an old refresh token revokes the whole family (`FRM-AUTH-1012`).
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

1. Credentials (or OAuth callback) → server returns `{ challenge_id, channels }` — **no tokens yet**.
2. OTP screen: 6 digits, valid 5 min, max 5 attempts, resend after 60 s (max 3), email by default; TOTP authenticator and SMS as options. Admins must use MFA (enforced).
3. On success → access + refresh tokens issued.

## 8. Other rules

- Passwords hashed with **Argon2id**.
- Rate limiting on **every** endpoint (Redis sliding window) by IP, user, tenant and endpoint; stricter on auth, OTP and public submit.
- Security headers: HSTS, CSP (per-form `frame-ancestors` for embeds), X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
- Secrets never logged (passwords, OTPs, tokens, keys, plaintext of sensitive fields).

## 9. Honest note

App-layer encryption protects against TLS-terminating proxies, logging leaks and traffic inspection; it does not protect against a compromised browser or device. It adds CPU cost, so keep payloads lean and paginate.
