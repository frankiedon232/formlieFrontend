// A local webhook receiver for testing Formalie webhooks while developing (no dependencies). It behaves like a
// real receiver must: every call has to carry the webhook token, anything else is refused with 401.
//   WEBHOOK_TOKEN=formalie_hook_live_… pnpm webhook:listen   listen on http://localhost:4000/hooks (token required)
//   FAIL=500                                                 also answer 500 to good calls, to see retries and auto-pause
// Every call carries the same headers as an API call: Authorization: Bearer <webhook token>,
// Content-Type: application/json and Formalie-Key (the delivery id, the same on every retry).
import { timingSafeEqual } from 'node:crypto'
import { createServer } from 'node:http'

const PORT = Number(process.env.PORT ?? 4000)
const TOKEN = (process.env.WEBHOOK_TOKEN ?? '').trim()
const FAIL = Number(process.env.FAIL ?? 0)

// No token, no receiver: a webhook without its token check accepts calls from anyone
if (!TOKEN) {
  console.error('WEBHOOK_TOKEN is required: the receiver refuses every call that does not carry it.')
  console.error('Copy the webhook token (Tokens & headers -> the webhook token -> Show), then:')
  console.error('  PowerShell:  $env:WEBHOOK_TOKEN="formalie_hook_live_..."; pnpm webhook:listen')
  console.error('  Bash:        WEBHOOK_TOKEN=formalie_hook_live_... pnpm webhook:listen')
  process.exit(1)
}

const seen = new Set()
let count = 0
const expected = Buffer.from(`Bearer ${TOKEN}`)
const tokenOk = header => header.length === expected.length && timingSafeEqual(Buffer.from(header), expected)

createServer((req, res) => {
  let body = ''
  req.on('data', chunk => (body += chunk))
  req.on('end', () => {
    count++
    const h = req.headers
    const answer = (status, reply) => {
      res.writeHead(status, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify(reply))
      console.log(`  answered      ${status}`)
    }
    console.log(`\n#${count} ${new Date().toLocaleTimeString()}  ${req.method} ${req.url}`)
    // 1 · The token first: nothing is read or trusted before it matches
    if (!tokenOk(String(h.authorization ?? ''))) {
      console.log(`  token         ${h.authorization ? 'WRONG' : 'MISSING'}: refused, the body was not read`)
      return answer(401, { error: 'unauthorized' })
    }
    console.log('  token         valid')
    // 2 · The Formalie-Key: a retry of a delivery already handled is answered, not handled again
    const key = String(h['formalie-key'] ?? '')
    if (seen.has(key)) {
      console.log(`  Formalie-Key  ${key}  (seen before: a retry, not handled again)`)
      return answer(200, { received: true, duplicate: true })
    }
    let json
    try {
      json = JSON.parse(body)
    } catch {
      console.log('  body          not JSON: refused')
      return answer(400, { error: 'bad_json' })
    }
    console.log(`  event         ${json.type ?? '-'}`)
    console.log(`  Formalie-Key  ${key}`)
    console.log(JSON.stringify(json, null, 2).replace(/^/gm, '  '))
    if (FAIL) return answer(FAIL, { received: false })
    seen.add(key)
    answer(200, { received: true })
  })
}).listen(PORT, () =>
  console.log(
    `Webhook receiver on http://localhost:${PORT}/hooks (token required${FAIL ? `, answering ${FAIL}` : ''})`,
  ),
)
