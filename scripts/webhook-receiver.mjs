// A local webhook receiver for testing Formalie webhooks while developing (no dependencies).
//   pnpm webhook:listen                                  listen on http://localhost:4000/hooks
//   WEBHOOK_TOKEN=formalie_hook_live_… pnpm webhook:listen   also check the token on each call
//   FAIL=500 pnpm webhook:listen                         answer 500 to see retries and auto-pause
// Every call carries the same headers as an API call: Authorization: Bearer <webhook token>,
// Content-Type: application/json and Formalie-Key (the delivery id, the same on every retry).
// Prints each delivery: the event, the Formalie-Key (and whether it was seen before), the token check, the JSON.
import { timingSafeEqual } from 'node:crypto'
import { createServer } from 'node:http'

const PORT = Number(process.env.PORT ?? 4000)
const TOKEN = process.env.WEBHOOK_TOKEN ?? ''
const FAIL = Number(process.env.FAIL ?? 0)
const seen = new Set()
let count = 0

function tokenOk(header) {
  if (!TOKEN) return 'not checked (set WEBHOOK_TOKEN)'
  const expected = `Bearer ${TOKEN}`
  return header.length === expected.length && timingSafeEqual(Buffer.from(header), Buffer.from(expected)) ? 'valid' : 'WRONG'
}

createServer((req, res) => {
  let body = ''
  req.on('data', chunk => (body += chunk))
  req.on('end', () => {
    count++
    const h = req.headers
    const key = String(h['formalie-key'] ?? '-')
    let event = '-'
    let json = null
    try {
      json = JSON.parse(body)
      event = json.type ?? '-'
    } catch {
      // not JSON: printed as text below
    }
    console.log(`\n#${count} ${new Date().toLocaleTimeString()}  ${req.method} ${req.url}`)
    console.log(`  event         ${event}`)
    console.log(`  Formalie-Key  ${key}${seen.has(key) ? '  (seen before: a retry, skip the work)' : ''}`)
    console.log(`  token         ${tokenOk(String(h.authorization ?? ''))}`)
    console.log(json ? JSON.stringify(json, null, 2).replace(/^/gm, '  ') : `  ${body.slice(0, 500)}`)
    seen.add(key)
    const status = FAIL || 200
    res.writeHead(status, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ received: status < 300 }))
    console.log(`  answered      ${status}`)
  })
}).listen(PORT, () => console.log(`Webhook receiver on http://localhost:${PORT}/hooks${FAIL ? ` (answering ${FAIL})` : ''}${TOKEN ? ' (checking the token)' : ''}`))
