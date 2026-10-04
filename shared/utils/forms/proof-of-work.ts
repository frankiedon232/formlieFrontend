/**
 * Invisible spam check for public forms (F10 M2, decision 89), no third-party captcha, no
 * tracking, nothing for people to click. The server hands out a signed challenge when the form
 * opens; the browser finds a number whose SHA-256 with the challenge's salt starts with
 * `difficulty` zero bits (well under a second on a phone, done in the background while the person
 * fills in). Sending many responses becomes expensive for bots, cheap for people.
 */

const encoder = new TextEncoder()

async function sha256(text: string): Promise<Uint8Array> {
  return new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(text)))
}

/** Does the hash start with this many zero bits? */
export function hasLeadingZeroBits(hash: Uint8Array, bits: number): boolean {
  let left = bits
  for (const byte of hash) {
    if (left <= 0) return true
    if (left >= 8) {
      if (byte !== 0) return false
      left -= 8
    } else return byte >> (8 - left) === 0
  }
  return left <= 0
}

/** The proof for a salt: a counter whose hash meets the difficulty. Gives up (null) after `limit` tries. */
export async function solveWork(salt: string, difficulty: number, limit = 5_000_000): Promise<number | null> {
  for (let nonce = 0; nonce < limit; nonce++) if (hasLeadingZeroBits(await sha256(`${salt}:${nonce}`), difficulty)) return nonce
  return null
}

export async function checkWork(salt: string, difficulty: number, nonce: number): Promise<boolean> {
  return Number.isInteger(nonce) && nonce >= 0 && hasLeadingZeroBits(await sha256(`${salt}:${nonce}`), difficulty)
}
