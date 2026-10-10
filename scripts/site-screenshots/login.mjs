// Signs the headless browser in to the local dev app with a seeded test account (seed password from
// server/mock/data/tenants.ts, read from the project, never printed). The code comes from the dev code screen.
import fs from 'node:fs'
import { connect } from './cdp.mjs'

const email = process.argv[2]
const seed = fs.readFileSync('server/mock/data/tenants.ts', 'utf8').match(/MOCK_PASSWORD = '([^']+)'/)[1]
const c = await connect()
await c.send('Page.enable')
await c.send('Runtime.enable')
await c.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })
await c.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: 'light' }] })
await c.navigate('https://localhost:2202/auth/login?tenant=remedylegal')
await c.evaluate("localStorage.setItem('nuxt-color-mode','light'); 1")
await c.navigate('https://localhost:2202/auth/login?tenant=remedylegal')
if (!(await c.waitFor("!!document.querySelector('input[type=email]')", 30000))) throw new Error('no login form: ' + (await c.evaluate('location.href')))
await c.evaluate("document.querySelector('input[type=email]').focus(); 1")
await c.type(email)
await c.evaluate("document.querySelector('input[type=password]').focus(); 1")
await c.type(seed)
await c.evaluate("document.querySelector('form button[type=submit]').click(); 1")
if (!(await c.waitFor("location.pathname.includes('/auth/otp')", 20000))) {
  console.log('stayed on', await c.evaluate('location.href'), await c.evaluate("document.body.innerText.slice(0,400)"))
  process.exit(1)
}
await c.sleep(1500)
// The dev code is shown on the screen in the mock
const code = await c.evaluate("(document.body.innerText.match(/\\b(\\d{6})\\b/)||[])[1] || ''")
if (!code) throw new Error('no dev code on the screen')
await c.evaluate("(document.querySelector('input[autocomplete=one-time-code]') || document.querySelector('input')).focus(); 1")
await c.type(code)
await c.sleep(500)
await c.evaluate("const b=[...document.querySelectorAll('button[type=submit]')].pop(); b && b.click(); 1")
const ok = await c.waitFor("!location.pathname.startsWith('/auth')", 20000)
console.log(ok ? 'signed in' : 'not signed in', await c.evaluate('location.pathname'))
c.close()
