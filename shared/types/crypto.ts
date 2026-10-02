/** Wire format of the encryption envelope (docs/SECURITY-PROTOCOL.md §2). */
export interface Envelope {
  kid: string
  iv: string
  ts: number
  nonce: string
  ct: string
}

/** Decrypted request payload. Method + path are bound inside the ciphertext. */
export interface EnvelopeRequestPayload<TBody = unknown> {
  method: string
  path: string
  query: Record<string, unknown>
  body: TBody | null
}

export interface HandshakeRequest {
  client_public_key: string
  client_ts: number
}

export interface HandshakeResponse {
  key_id: string
  server_public_key: string
  salt: string
  expires_at: string
}
