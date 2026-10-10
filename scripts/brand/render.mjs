// Renders the Formalie brand kit (docs/brand/) from its SVG sources: PNG sizes, web icons, favicon.ico,
// the OG image and the zip-ready folder. Uses headless Chrome on port 9333 (see scripts/site-screenshots/README.md).
//   node scripts/brand/render.mjs
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { connect } from '../site-screenshots/cdp.mjs'

const ROOT = 'docs/brand'
const svg = name => readFileSync(`${ROOT}/svg/${name}.svg`, 'utf8')
const square = (tile, glyph) => svg('formalie-mark').replace('rx="16" fill="#0a0a0a"', `rx="0" fill="${tile}"`).replaceAll('fill="#fff"', `fill="${glyph}"`)
const FONT = '<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700&display=block" rel="stylesheet">'

const cdp = await connect()
await cdp.send('Emulation.setDefaultBackgroundColorOverride', { color: { r: 0, g: 0, b: 0, a: 0 } })

async function shoot(html, width, height, file) {
  await cdp.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false })
  const page = `<!doctype html><html><head><meta charset="utf-8">${FONT}<style>html,body{margin:0;background:transparent}body>*{display:block}body>svg{width:${width}px;height:${height}px}</style></head><body>${html}</body></html>`
  await cdp.navigate(`data:text/html;base64,${Buffer.from(page).toString('base64')}`)
  await cdp.waitFor('document.fonts.status === "loaded" && document.readyState === "complete"')
  await cdp.sleep(150)
  const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width, height, scale: 1 } })
  writeFileSync(file, Buffer.from(data, 'base64'))
  return Buffer.from(data, 'base64')
}

// favicon.ico with PNG entries (valid in every current browser and Windows)
function ico(pngs) {
  const head = Buffer.alloc(6 + 16 * pngs.length)
  head.writeUInt16LE(0, 0)
  head.writeUInt16LE(1, 2)
  head.writeUInt16LE(pngs.length, 4)
  let offset = head.length
  pngs.forEach(({ size, data }, i) => {
    const at = 6 + 16 * i
    head.writeUInt8(size >= 256 ? 0 : size, at)
    head.writeUInt8(size >= 256 ? 0 : size, at + 1)
    head.writeUInt16LE(1, at + 4)
    head.writeUInt16LE(32, at + 6)
    head.writeUInt32LE(data.length, at + 8)
    head.writeUInt32LE(offset, at + 12)
    offset += data.length
  })
  return Buffer.concat([head, ...pngs.map(p => p.data)])
}

mkdirSync(`${ROOT}/png`, { recursive: true })
mkdirSync(`${ROOT}/web`, { recursive: true })

for (const size of [16, 32, 48, 64, 128, 256, 512, 1024]) await shoot(svg('formalie-mark'), size, size, `${ROOT}/png/formalie-mark-${size}.png`)
for (const name of ['formalie-mark-inverse', 'formalie-mark-accent']) await shoot(svg(name), 512, 512, `${ROOT}/png/${name}-512.png`)
for (const name of ['formalie-glyph', 'formalie-glyph-white']) await shoot(svg(name), 512, 512, `${ROOT}/png/${name}-512.png`)
for (const name of ['formalie-lockup-light', 'formalie-lockup-dark'])
  for (const scale of [2, 4]) await shoot(svg(name), 300 * scale, 64 * scale, `${ROOT}/png/${name}@${scale}x.png`)

const icons = []
for (const size of [16, 32, 48]) icons.push({ size, data: await shoot(svg('formalie-mark'), size, size, `${ROOT}/web/favicon-${size}.png`) })
writeFileSync(`${ROOT}/web/favicon.ico`, ico(icons))
await shoot(square('#0a0a0a', '#fff'), 180, 180, `${ROOT}/web/apple-touch-icon.png`)
await shoot(svg('formalie-mark'), 192, 192, `${ROOT}/web/icon-192.png`)
await shoot(svg('formalie-mark'), 512, 512, `${ROOT}/web/icon-512.png`)
await shoot(square('#0a0a0a', '#fff'), 512, 512, `${ROOT}/web/icon-maskable-512.png`)

// Social preview (1200 × 630): the lockup on paper with the line people read under it
const og = `<div style="width:1200px;height:630px;box-sizing:border-box;padding:96px;background:#fff;font-family:Manrope,system-ui,sans-serif;color:#0a0a0a;display:flex;flex-direction:column;justify-content:space-between">
  <div style="width:520px;height:111px">${svg('formalie-lockup-light').replace('width="300" height="64"', 'width="520" height="111"')}</div>
  <div style="font-size:60px;font-weight:700;letter-spacing:-0.035em;line-height:1.08;max-width:900px">Forms, data and access, under your control.</div>
  <div style="display:flex;align-items:center;gap:14px;font-size:24px;font-weight:500;color:#525252"><span style="width:14px;height:14px;border-radius:50%;background:#7c3aed"></span>formalie.com</div>
</div>`
await shoot(og, 1200, 630, `${ROOT}/web/og-image.png`)

cdp.close()
console.log('brand kit rendered')
