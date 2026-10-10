// Minimal Chrome DevTools Protocol helper (Node's built-in WebSocket), for capturing help screenshots.
export async function connect(port = 9333) {
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  let page = targets.find(t => t.type === 'page')
  if (!page) page = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json()
  const ws = new WebSocket(page.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => ((ws.onopen = resolve), (ws.onerror = reject)))
  let id = 0
  const waiting = new Map()
  const listeners = new Set()
  ws.onmessage = event => {
    const msg = JSON.parse(event.data)
    if (msg.id && waiting.has(msg.id)) {
      const { resolve, reject } = waiting.get(msg.id)
      waiting.delete(msg.id)
      msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result)
    } else for (const fn of listeners) fn(msg)
  }
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const n = ++id
      waiting.set(n, { resolve, reject })
      ws.send(JSON.stringify({ id: n, method, params }))
    })
  const evaluate = async expression => {
    const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text)
    return r.result.value
  }
  const sleep = ms => new Promise(r => setTimeout(r, ms))
  const waitFor = async (expression, timeout = 15000) => {
    const end = Date.now() + timeout
    while (Date.now() < end) {
      try {
        if (await evaluate(expression)) return true
      } catch {
        // The page is still loading: try again
      }
      await sleep(250)
    }
    return false
  }
  const navigate = async url => {
    await send('Page.navigate', { url })
    await sleep(800)
  }
  const type = async text => send('Input.insertText', { text })
  const close = () => ws.close()
  const listen = fn => listeners.add(fn)
  return { send, evaluate, waitFor, navigate, type, sleep, close, listen }
}
