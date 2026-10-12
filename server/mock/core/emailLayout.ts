/**
 * The one Formalie email layout (owner-approved design, 2026-10-12), the same page the backend draws
 * (formlyBackend app/modules/emails/layout.py): an ink header with the workspace's tile and the Formalie "fields"
 * motif (its dot and the rule under the header in the workspace's colour), a white card with the subject as its
 * title, codes in a large box, answers as a table, a line ending in a link as an ink button, and a quiet centred
 * footer. Tables and inline styles only, so email apps show it the same.
 */
const INK = '#0a0a0a'
const MUTED = '#6b6b6b'
const LINE = '#e7e7e5'
const CANVAS = '#f4f4f2'
const FONT = "'Manrope',-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
/** Where the answers table goes, until the text around it is laid out. */
export const ANSWERS = '[[formalie:answers]]'
// The mock's emails are only shown inside the portal (sent log, preview), so the mark comes from its own public/brand
const ASSETS = '/brand'
const LINK_LINE = /^(?<lead>[\s\S]*?)[:：]\s*(?<url>https?:\/\/\S+)\s*$/
const RTL = new Set(['ar'])

export const escapeHtml = (text: string | number) =>
  String(text).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]!)

export interface EmailLook {
  workspace: string
  logoUrl?: string | null
  brandColor?: string | null
  /** Formalie's own email (sign-up, find workspace): the Field F mark in the tile. */
  formalie?: boolean
  footerLines: string[]
  /** The language's `layout` texts (via, tagline, privacy, open, answers, unsubscribe). */
  texts: Partial<Record<'via' | 'tagline' | 'privacy' | 'open' | 'answers' | 'unsubscribe', string>>
  language: string
  unsubscribeUrl?: string | null
}

const button = (label: string, url: string) =>
  `<table role="presentation" cellpadding="0" cellspacing="0" style="margin:6px 0 10px"><tr><td style="border-radius:10px;background:${INK}"><a href="${escapeHtml(url)}" style="display:inline-block;padding:13px 22px;font:600 14px/1 ${FONT};color:#ffffff;text-decoration:none;border-radius:10px">${escapeHtml(label)}</a></td></tr></table><p style="margin:0 0 20px;font:12px/1.5 ${FONT};color:${MUTED};word-break:break-all"><a href="${escapeHtml(url)}" style="color:${MUTED}">${escapeHtml(url)}</a></p>`

const codeBox = (code: string) =>
  `<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin:2px 0 20px"><tr><td align="center" dir="ltr" style="background:${CANVAS};border:1px solid ${LINE};border-radius:12px;padding:18px 12px;font:700 30px/1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:6px;color:${INK}">${[...code].map(escapeHtml).join('&nbsp;')}</td></tr></table>`

const answersTable = (answers: { label: string; value: string }[], title: string) =>
  `<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin:2px 0 20px;border:1px solid ${LINE};border-radius:12px;border-collapse:separate;overflow:hidden"><tr><td colspan="2" style="padding:10px 14px;background:${CANVAS};font:600 11px/1 ${FONT};color:${MUTED};text-transform:uppercase;letter-spacing:.06em">${escapeHtml(title)}</td></tr>${answers.map(item => `<tr><td style="padding:10px 14px;border-top:1px solid ${LINE};font:12px/1.45 ${FONT};color:${MUTED};width:38%;vertical-align:top">${escapeHtml(item.label)}</td><td style="padding:10px 14px;border-top:1px solid ${LINE};font:500 13px/1.45 ${FONT};color:${INK};white-space:pre-wrap;vertical-align:top">${escapeHtml(item.value)}</td></tr>`).join('')}</table>`

const paragraph = (text: string) =>
  `<p style="margin:0 0 16px;font:15px/1.6 ${FONT};color:#262626">${escapeHtml(text).replace(/(https?:\/\/[^\s<]+)/g, `<a href="$1" style="color:${INK};text-decoration:underline">$1</a>`).replace(/\n/g, '<br>')}</p>`

function blocks(body: string, vars: Record<string, string | number>, answers: { label: string; value: string }[], look: EmailLook) {
  const code = vars.code != null ? String(vars.code) : ''
  let codeShown = false
  const parts: string[] = []
  for (const raw of body.split(/\n{2,}/)) {
    const part = raw.trim()
    if (!part) continue
    if (part === ANSWERS) {
      if (answers.length) parts.push(answersTable(answers, look.texts.answers ?? 'Answers'))
      continue
    }
    const found = part.includes(ANSWERS) ? null : LINK_LINE.exec(part)
    if (found?.groups) {
      const lead = found.groups.lead!.trim()
      if (lead && lead.length <= 48 && !lead.includes('\n')) parts.push(button(lead, found.groups.url!))
      else {
        if (lead) parts.push(paragraph(lead))
        parts.push(button(look.texts.open ?? 'Open', found.groups.url!))
      }
      continue
    }
    parts.push(paragraph(part.split(ANSWERS).join('')))
    if (code && !codeShown && part.includes(code)) {
      parts.push(codeBox(code))
      codeShown = true
    }
  }
  return parts.join('')
}

function header(look: EmailLook) {
  const dot = look.brandColor || '#ffffff'
  const rule = look.brandColor || INK
  const inner = look.formalie
    ? `<img src="${ASSETS}/formalie-glyph-512.png" alt="" width="28" height="28" style="display:block;margin:6px;width:28px;height:28px">`
    : look.logoUrl
      ? `<img src="${escapeHtml(look.logoUrl)}" alt="" width="28" height="28" style="display:block;margin:6px;width:28px;height:28px;object-fit:contain;border-radius:6px">`
      : `<span style="font:800 17px/40px ${FONT};color:${INK}">${escapeHtml((look.workspace.trim() || 'F').slice(0, 1).toUpperCase())}</span>`
  const via = look.formalie ? '' : `<div style="font:500 12px/1.4 ${FONT};color:#9a9a9a">${escapeHtml(look.texts.via ?? 'Sent with Formalie')}</div>`
  const motif = `<td align="right" style="vertical-align:middle"><table role="presentation" cellpadding="0" cellspacing="0"><tr><td style="padding:0 0 6px"><div style="width:58px;height:9px;border-radius:9px;background:#2b2b2b"></div></td><td></td></tr><tr><td><div style="width:38px;height:9px;border-radius:9px;background:#2b2b2b"></div></td><td style="padding:0 0 0 6px"><div style="width:9px;height:9px;border-radius:9px;background:${escapeHtml(dot)}"></div></td></tr></table></td>`
  return `<tr><td style="background:${INK};border-radius:18px 18px 0 0;padding:22px 28px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td style="width:40px;height:40px;background:#ffffff;border-radius:11px;text-align:center;vertical-align:middle">${inner}</td><td style="padding-inline-start:12px;vertical-align:middle"><div style="font:700 16px/1.25 ${FONT};color:#ffffff">${escapeHtml(look.workspace)}</div>${via}</td>${motif}</tr></table></td></tr><tr><td style="height:3px;line-height:3px;font-size:0;background:${escapeHtml(rule)}">&nbsp;</td></tr>`
}

function footer(look: EmailLook) {
  const reason = look.footerLines.map(line => `<p style="margin:0 0 4px;font:12px/1.6 ${FONT};color:${MUTED}">${escapeHtml(line)}</p>`).join('')
  const links = [
    `<a href="https://formalie.com/privacy" style="color:${MUTED};text-decoration:underline">${escapeHtml(look.texts.privacy ?? 'Privacy')}</a>`,
    `<a href="https://formalie.com" style="color:${MUTED};text-decoration:none">formalie.com</a>`,
    ...(look.unsubscribeUrl ? [`<a href="${escapeHtml(look.unsubscribeUrl)}" style="color:${MUTED};text-decoration:underline">${escapeHtml(look.texts.unsubscribe ?? 'Unsubscribe')}</a>`] : []),
  ]
  return `<tr><td style="padding:26px 12px 6px" align="center"><a href="https://formalie.com" style="text-decoration:none"><table role="presentation" cellpadding="0" cellspacing="0"><tr><td style="vertical-align:middle"><img src="${ASSETS}/formalie-mark-64.png" alt="" width="22" height="22" style="display:block;border-radius:6px"></td><td style="padding-inline-start:8px;vertical-align:middle;font:700 14px/1 ${FONT};letter-spacing:-.02em;color:${INK}">Formalie</td></tr></table></a><p style="margin:10px 0 14px;font:12px/1.5 ${FONT};color:${MUTED}">${escapeHtml(look.texts.tagline ?? 'Forms, data and access, under your control.')}</p><div style="width:40px;height:1px;background:${LINE};margin:0 auto 14px"></div>${reason}<p style="margin:10px 0 0;font:12px/1.6 ${FONT}">${links.join('<span style="color:#c4c4c0">&nbsp;&nbsp;·&nbsp;&nbsp;</span>')}</p></td></tr>`
}

/** → { html, text }. `body` is filled in except `{{answers}}` (as ANSWERS). */
export function emailPage(subject: string, body: string, vars: Record<string, string | number>, look: EmailLook, answers: { label: string; value: string }[] = []) {
  const dir = RTL.has(look.language.split('-')[0]!) ? ' dir="rtl"' : ''
  const html = `<!doctype html><html${dir}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light"><title>${escapeHtml(subject)}</title></head><body style="margin:0;padding:0;background:${CANVAS};-webkit-text-size-adjust:100%"><div style="display:none;max-height:0;overflow:hidden;opacity:0">${escapeHtml(subject)}</div><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${CANVAS}"><tr><td align="center" style="padding:36px 14px 28px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:580px"><tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid ${LINE};border-radius:18px;border-collapse:separate">${header(look)}<tr><td style="padding:30px 32px 12px"><h1 style="margin:0 0 16px;font:800 23px/1.3 ${FONT};letter-spacing:-.02em;color:${INK}">${escapeHtml(subject)}</h1>${blocks(body, vars, answers, look)}</td></tr></table></td></tr>${footer(look)}</table></td></tr></table></body></html>`
  const answersText = answers.map(item => `${item.label}: ${item.value}`).join('\n')
  const unsubscribe = look.unsubscribeUrl ? `\n${look.texts.unsubscribe ?? 'Unsubscribe'}: ${look.unsubscribeUrl}` : ''
  const text = `${body.split(ANSWERS).join(answersText)}\n\n--\n${look.footerLines.join('\n')}\n\nFormalie · https://formalie.com${unsubscribe}`
  return { html, text }
}
