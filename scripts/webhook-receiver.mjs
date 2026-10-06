// A local webhook receiver for testing Formalie webhooks while developing (no dependencies).
//   pnpm webhook:listen                       listen on http://localhost:4000/hooks
//   WEBHOOK_SECRET=formalie_hook_… pnpm webhook:listen   also check each signature
//   FAIL=500 pnpm webhook:listen               answer 500 to see retries and auto-pause
// Prints each delivery: event, delivery id, signature check and the JSON body.
import { createHmac, timingSafeEqual } from 'node:crypto'
import { createServer } from 'node:http'

const PORT = Number(process.env.PORT ?? 4000)
const SECRET = process.env.WEBHOOK_SECRET ?? ''
const FAIL = Number(process.env.FAIL ?? 0)
let count = 0

function signatureOk(timestamp, body, header) {
  if (!SECRET) return 'not checked (set WEBHOOK_SECRET)'
  const expected = `sha256=${createHmac('sha256', SECRET).update(`${timestamp}.${body}`).digest('hex')}`
  const same = header.length === expected.length && timingSafeEqual(Buffer.from(header), Buffer.from(expected))
  const age = Math.abs(Date.now() / 1000 - Number(timestamp))
  return same ? (age > 300 ? `valid but ${Math.round(age)} s old (refuse after 5 minutes)` : 'valid') : 'WRONG'
}

createServer((req, res) => {
  let body = ''
  req.on('data', chunk => (body += chunk))
  req.on('end', () => {
    count++
    const h = req.headers
    const timestamp = String(h['x-formalie-timestamp'] ?? '')
    console.log(`\n#${count} ${new Date().toLocaleTimeString()}  ${req.method} ${req.url}`)
    console.log(`  event      ${h['x-formalie-event'] ?? '-'}`)
    console.log(`  delivery   ${h['x-formalie-delivery'] ?? '-'}`)
    console.log(`  signature  ${signatureOk(timestamp, body, String(h['x-formalie-signature'] ?? ''))}`)
    try {
      console.log(JSON.stringify(JSON.parse(body), null, 2).replace(/^/gm, '  '))
    } catch {
      console.log(`  ${body.slice(0, 500)}`)
    }
    const status = FAIL || 200
    res.writeHead(status, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ received: status < 300 }))
    console.log(`  answered   ${status}`)
  })
}).listen(PORT, () => console.log(`Webhook receiver on http://localhost:${PORT}/hooks${FAIL ? ` (answering ${FAIL})` : ''}${SECRET ? ' (checking signatures)' : ''}`))
