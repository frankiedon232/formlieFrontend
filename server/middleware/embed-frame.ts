/**
 * DEVELOPMENT ONLY (the dev server; a static production build has no server, the Worker in
 * edge/worker.ts sets the embed's headers there). `/{formKey}/embed` is shown inside other
 * websites and the portal's own windows, so it drops the page-wide `X-Frame-Options: SAMEORIGIN`
 * from the route rules. The per-form list of allowed websites is enforced in production.
 */
export default defineEventHandler(event => {
  if (/^\/[^/]+\/embed\/?$/.test(event.path.split('?')[0]!)) event.node.res.removeHeader('x-frame-options')
})
