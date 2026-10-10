// Captures the help screenshots at 1440x900 (light mode) with a watermark baked into the pixels.
// Usage: node capture.mjs <plan.json> [id ...]   (run from the project root; the headless browser is signed in)
import fs from 'node:fs'
import { connect } from './cdp.mjs'

const [planFile, ...only] = process.argv.slice(2)
const OUT = process.env.OUT || 'site-shots'
const plan = JSON.parse(fs.readFileSync(planFile, 'utf8'))
const ids = { JOB: plan.JOB, EMP: plan.EMP }
const c = await connect()
await c.send('Page.enable')
await c.send('Runtime.enable')
await c.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 2, mobile: false })
await c.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: 'light' }] })

// A tiled diagonal "Formalie · formalie.com" plus a corner mark: light enough to read the page through it
const tile = color => encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="420" height="260"><g transform="rotate(-24 210 130)" font-family="Manrope, Segoe UI, Arial, sans-serif" font-size="22" font-weight="700" fill="${color}"><text x="40" y="120">Formalie · formalie.com</text><text x="250" y="250">Formalie</text></g></svg>`,
)
const WATERMARK = rect => `((rect) => {
  document.querySelectorAll('#nuxt-devtools-container, [id^="nuxt-devtools"], #__formalie_wm').forEach(e => e.remove());
  [...document.querySelectorAll('img')].filter(i => i.src.startsWith('data:image/jpeg') || i.src.startsWith('data:image/png')).forEach(i => i.dispatchEvent(new Event('error')));
  const w = document.createElement('div');
  w.id = '__formalie_wm';
  w.style.cssText = 'position:fixed;inset:0;z-index:2147483647;pointer-events:none;background-image:url("data:image/svg+xml,' + (document.documentElement.classList.contains('dark') ? '${tile('rgba(255,255,255,0.07)')}' : '${tile('rgba(17,17,17,0.055)')}') + '");background-repeat:repeat';
  const mark = document.createElement('div');
  const strip = document.createElement('div'); const isDark = document.documentElement.classList.contains('dark'); strip.style.cssText = 'position:absolute;left:' + rect.x + 'px;top:' + (rect.y + rect.height - 30) + 'px;width:' + rect.width + 'px;height:30px;background:' + (isDark ? '#18181b' : '#fff') + ';border-top:1px solid ' + (isDark ? '#27272a' : '#ececec') + ';display:flex;align-items:center;justify-content:flex-end;padding:0 10px;box-sizing:border-box'; w.appendChild(strip);
  mark.style.cssText = 'display:flex;align-items:center;gap:6px;padding:4px 9px;border-radius:999px;background:rgba(17,17,17,0.78);color:#fff;font:600 11px/1 Manrope,Segoe UI,Arial,sans-serif;letter-spacing:.01em';
  mark.innerHTML = '<span style="display:inline-flex;width:14px;height:14px;border-radius:4px;background:#fff;color:#111;align-items:center;justify-content:center;font-size:9px;font-weight:800">F</span>Formalie · formalie.com';
  strip.appendChild(mark);
  document.body.appendChild(w);
  return true;
})(${JSON.stringify(rect)})`


// Finds the part of the page an article is about and returns its box (CSS pixels, padded, inside the viewport)
const LOCATE = target => `(() => {
  const panel = () => document.querySelector('[id^=formalie-layout-panel]');
  const body = () => panel()?.querySelector('[data-slot=body]') || panel();
  const leaf = t => [...document.querySelectorAll('h1,h2,h3,h4,p,span,div,dt,label,a,button,li')].find(e => e.textContent.trim() === t && [...e.children].every(ch => ch.textContent.trim() !== t));
  const has = t => [...document.querySelectorAll('h2,h3,span,p')].find(e => e.textContent.trim().startsWith(t));
  const card = t => { let e = leaf(t); while (e && !(/rounded/.test(e.className) && /(border|ring)/.test(e.className) && e.getBoundingClientRect().height > 80)) e = e.parentElement; return e };
  const column = t => { let e = leaf(t); while (e && !(e.getBoundingClientRect().height > 500 && e.getBoundingClientRect().width < 420)) e = e.parentElement; return e };
  const box = e => e && e.getBoundingClientRect();
  const parts = ${JSON.stringify(target)}.split('+').map(spec => {
    const [kind, ...rest] = spec.split(':'); const arg = rest.join(':');
    if (kind === 'rect') { const [x, y, w, h] = arg.split(',').map(Number); return { x, y, width: w, height: h, pad: 0 } }
    if (kind === 'body' || kind === 'panel') { const b = box(kind === 'body' ? body() : panel()); return { x: b.x, y: b.y, width: b.width, height: Math.min(b.height, Number(arg)), pad: 0 } }
    if (kind === 'gridcards') { const g = document.querySelector('.grid[aria-busy]'); g.scrollIntoView({ block: 'start' }); body().scrollBy(0, -110); const hb = box(panel().querySelector('header') || panel().firstElementChild); const b0 = box(g); const top = Math.max(b0.y - 14, hb ? hb.bottom + 2 : 0); const b = { x: b0.x, y: top + 14, width: b0.width, height: b0.bottom - top - 14 }; return { x: b.x, y: Math.max(b.y - 14, 0), width: b.width, height: Math.min(b.height, Number(arg)), pad: 14 } }
    if (kind === 'dialog') { const b = box([...document.querySelectorAll('[role=dialog]')].pop()); return { ...b.toJSON(), pad: 0 } }
    if (kind === 'header') { const b = box(panel().querySelector('[data-slot=root] ,header') || panel().firstElementChild); return { x: b.x, y: b.y, width: b.width, height: b.height, pad: 0 } }
    let el = kind === 'card' ? card(arg) : kind === 'column' ? column(arg) : kind === 'section' ? leaf(arg)?.closest('section') : kind === 'sectionHas' ? has(arg)?.closest('section') : document.querySelector(arg);
    if (!el) return null;
    el.scrollIntoView({ block: 'center' });
    return { ...box(el).toJSON(), pad: 14 };
  });
  if (parts.some(p => !p)) return null;
  const x0 = Math.min(...parts.map(p => p.x - p.pad)), y0 = Math.min(...parts.map(p => p.y - p.pad));
  const x1 = Math.max(...parts.map(p => p.x + p.width + p.pad)), y1 = Math.max(...parts.map(p => p.y + p.height + p.pad));
  const x = Math.max(0, x0), y = Math.max(0, y0);
  return { x, y, width: Math.min(innerWidth, x1) - x, height: Math.min(innerHeight, y1 + 30) - y };
})()`

const ready = `!document.querySelector('.animate-pulse') && !!document.querySelector('main, [id]') && document.readyState === 'complete'`
const click = selectorJs => c.evaluate(`(() => { const el = ${selectorJs}; if (!el) return false; el.click(); return true })()`)
const byText = (text, tag = 'button, a, [role=tab], [role=button]') => `[...document.querySelectorAll('${tag}')].find(e => e.textContent.trim() === ${JSON.stringify(text)})`

fs.mkdirSync(OUT, { recursive: true })
const done = new Map()
for (const shot of plan.shots) {
  if (only.length && !only.includes(shot.id)) continue
  const path = shot.path.replace('JOB', ids.JOB).replace('EMP', ids.EMP)
  const key = `${path}|${shot.open ?? ''}|${shot.target ?? ''}|${shot.mode ?? 'light'}`
  if (done.has(key)) {
    fs.copyFileSync(done.get(key), `${OUT}/${shot.id}.jpg`)
    console.log(shot.id, 'same as', done.get(key))
    continue
  }
  const dark = shot.mode === 'dark'
  await c.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: dark ? 'dark' : 'light' }] })
  await c.evaluate(`(() => { try { localStorage.setItem('nuxt-color-mode', '${dark ? 'dark' : 'light'}') } catch {} return 1 })()`).catch(() => 0)
  await c.navigate(`https://localhost:2202${path}`)
  await c.waitFor(ready, 20000)
  await c.sleep(2500)
  if (shot.open === 'row') {
    for (let tries = 0; tries < 3; tries++) {
      await click(`document.querySelector('tbody tr td:nth-child(3)') || document.querySelector('tbody tr')`)
      if (await c.waitFor("!!document.querySelector('[role=dialog]')", 6000)) break
    }
    await c.sleep(2000)
  }
  if (shot.open === 'grid') {
    await c.evaluate(`(() => { const b = [...document.querySelectorAll('button[role=tab]')].find(e => e.textContent.trim() === 'Grid'); ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t => b.dispatchEvent(new MouseEvent(t, { bubbles: true, button: 0 }))); return 1 })()`)
    await c.sleep(2500)
  }
  if (shot.open === 'table') {
    await click(byText('Table', 'button, [role=tab], [role=radio], span, div'))
    await c.sleep(1500)
  }
  if (shot.open === 'firstTable') {
    await click(`[...document.querySelectorAll('button, a, li, div')].find(e => e.children.length < 3 && /^clients/.test(e.textContent.trim()))`)
    await c.sleep(3000)
  }
  await c.sleep(600)
  const rect = await c.evaluate(LOCATE(shot.target ?? 'body:900'))
  if (!rect) { console.log(shot.id, 'TARGET NOT FOUND', shot.target); continue }
  await c.sleep(500)
  const again = (await c.evaluate(LOCATE(shot.target ?? 'body:900'))) ?? rect
  // Neutral sample names instead of real keys, test names and people (website shots, owner 2026-10-10: show nothing private)
  await c.evaluate(`((map) => {
    const swap = text => Object.entries(map).reduce((out, [from, to]) => out.split(from).join(to), text)
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
    for (let n = walker.nextNode(); n; n = walker.nextNode()) { const next = swap(n.nodeValue); if (next !== n.nodeValue) n.nodeValue = next }
    document.querySelectorAll('input, textarea').forEach(i => { const next = swap(i.value); if (next !== i.value) i.value = next })
    document.querySelectorAll('img[alt]').forEach(i => { i.alt = swap(i.alt) })
    // No tour offers in pictures; uploaded logos and photos (real people, the owner's company) become a neutral monogram
    if (!document.getElementById('__no_tips')) { const st = document.createElement('style'); st.id = '__no_tips'; st.textContent = '[role=dialog][aria-live=polite]{display:none!important}'; document.head.appendChild(st) }
    const mono = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" rx="14" fill="#18181b"/><text x="32" y="42" text-anchor="middle" font-family="Manrope,Segoe UI,Arial" font-size="30" font-weight="700" fill="#fff">N</text></svg>')
    document.querySelectorAll('img').forEach(i => { const src = i.getAttribute('src') || ''; if (['/api/v1/files', '/uploads', 'blob:', 'data:image/jpeg', 'data:image/png', 'data:image/webp'].some(part => src.includes(part))) { i.src = mono; i.srcset = '' } })
    return 1
  })(${JSON.stringify(plan.replace ?? {})})`)
  await c.sleep(150)
  await c.evaluate(WATERMARK(again))
  await c.sleep(300)
  const { data } = await c.send('Page.captureScreenshot', { format: 'jpeg', quality: 84, clip: { ...again, scale: 1 } })
  const file = `${OUT}/${shot.id}.jpg`
  fs.writeFileSync(file, Buffer.from(data, 'base64'))
  done.set(key, file)
  console.log(shot.id, Math.round(again.width) + 'x' + Math.round(again.height), Math.round(Buffer.from(data, 'base64').length / 1024) + ' KB')
}
c.close()
