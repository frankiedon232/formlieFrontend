/**
 * Emails in the mock (F14 M4): Formalie's default texts per language (data/emailDefaults/{code}.json,
 * English when a language has none), the workspace's own texts (Settings → Email templates), and one
 * branded layout (logo or name, brand colour, footer). The mock never sends: emails land in the
 * workspace's sent log (data/outboxStore.ts) where Settings shows them.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import type { EmailTemplateKey, EmailText } from '#shared/types/emails'
import { fromAddress } from '../data/sendingStore'
import { settingsOf } from '../data/settingsStore'
import type { MockTenant } from '../data/tenants'

interface Defaults {
  templates: Record<EmailTemplateKey, EmailText>
  events: Record<string, { title: string; message: string }>
  layout: { footer: string; footer_form: string; answers: string; open: string; summary: string }
  reasons: Record<string, string>
}

const cache = new Map<string, Defaults | null>()
function load(language: string): Defaults | null {
  if (!cache.has(language)) {
    try {
      cache.set(language, JSON.parse(readFileSync(join(process.cwd(), 'server/mock/data/emailDefaults', `${language}.json`), 'utf8')) as Defaults)
    } catch {
      cache.set(language, null)
    }
  }
  return cache.get(language) ?? null
}

/** Formalie's texts in this language (English for anything missing). */
export function emailDefaults(language: string): Defaults {
  const en = load('en')!
  const own = language === 'en' ? null : load(language)
  if (!own) return en
  return { templates: { ...en.templates, ...own.templates }, events: { ...en.events, ...own.events }, layout: { ...en.layout, ...own.layout }, reasons: { ...en.reasons, ...own.reasons } }
}

/** The text a workspace sends: its own for this language, else Formalie's. */
export function templateText(tenant: MockTenant, key: EmailTemplateKey, language: string): { text: EmailText; custom: EmailText | null; fallback: EmailText } {
  const fallback = emailDefaults(language).templates[key]
  const custom = settingsOf(tenant).emails.custom[key]?.[language] ?? null
  return { text: custom ?? fallback, custom, fallback }
}

/** A date and time as the workspace shows them (its time zone), in the email's language. */
export function emailDate(tenant: MockTenant, language: string, value: Date | string = new Date()) {
  return new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short', timeZone: settingsOf(tenant).localisation.timezone }).format(new Date(value))
}

/** The language emails go out in: the one asked for when the workspace offers it, else the workspace's. */
export function emailLanguage(tenant: MockTenant, wanted?: string | null) {
  const { localisation } = settingsOf(tenant)
  return wanted && (wanted === localisation.language || localisation.form_languages.includes(wanted)) ? wanted : localisation.language
}

export const fillIn = (text: string, vars: Record<string, string | number>) => text.replace(/\{\{\s*(\w+)\s*\}\}/g, (match, name: string) => (name in vars ? String(vars[name]) : match))

/** Formalie under every email, whatever the workspace's branding (owner, 2026-10-07): its mark and name, linked. */
const FORMALIE_MARK = '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:14px auto 0"><tr><td align="center" style="font-size:11px"><a href="https://formalie.com" style="color:#6b6b6b;text-decoration:none"><span style="display:inline-block;width:16px;height:16px;line-height:16px;border-radius:4px;background:#111111;color:#ffffff;font-size:10px;font-weight:700;text-align:center;vertical-align:middle">F</span>&nbsp;<span style="vertical-align:middle;font-weight:600">Formalie</span></a></td></tr></table>'

/** Where the answers table goes, until the text around it is laid out. */
const ANSWERS = '[[formalie:answers]]'
const escape = (text: string) => text.replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]!)
const linkify = (html: string) => html.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" style="color:inherit;text-decoration:underline">$1</a>')

export interface EmailAnswer {
  label: string
  value: string
}

/** Subject, HTML and plain text, ready to send. `{{answers}}` becomes a table (HTML) or lines (text). */
export function renderEmail(tenant: MockTenant, key: EmailTemplateKey, language: string, vars: Record<string, string | number>, options: { text?: EmailText; answers?: EmailAnswer[]; footer?: 'account' | 'form' } = {}) {
  const settings = settingsOf(tenant)
  const name = settings.company.display_name || tenant.name
  const defaults = emailDefaults(language)
  const all = { workspace: name, ...vars }
  const source = options.text ?? templateText(tenant, key, language).text
  const subject = fillIn(source.subject, all).replace(/\s+/g, ' ').trim()
  const answers = options.answers ?? []
  const answersText = answers.map(item => `${item.label}: ${item.value}`).join('\n')
  const body = fillIn(source.body, { ...all, answers: ANSWERS })
  const color = settings.branding.brand_color ?? '#111111'
  const footer = [settings.emails.footer, fillIn(options.footer === 'form' ? defaults.layout.footer_form : defaults.layout.footer, all)].filter(Boolean) as string[]

  const table = answers.length
    ? `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:8px 0 16px;border:1px solid #e5e5e5;border-radius:8px">${answers.map(item => `<tr><td style="padding:8px 12px;border-bottom:1px solid #eee;color:#666;font-size:13px;width:40%;vertical-align:top">${escape(item.label)}</td><td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:13px;color:#111;white-space:pre-wrap">${escape(item.value)}</td></tr>`).join('')}</table>`
    : ''
  const paragraphs = body
    .split(/\n{2,}/)
    .map(part => (part.trim() === ANSWERS ? table : `<p style="margin:0 0 14px;line-height:1.55">${linkify(escape(part.split(ANSWERS).join(''))).replace(/\n/g, '<br>')}</p>`))
    .join('')
  const logo = settings.branding.logo_url ? `<img src="${escape(settings.branding.logo_url)}" alt="" height="28" style="height:28px;max-width:160px;object-fit:contain;vertical-align:middle">` : ''
  const html = `<!doctype html><html><body style="margin:0;padding:24px;background:#f4f4f5;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#111"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e5e5e5"><tr><td style="height:4px;background:${escape(color)}"></td></tr><tr><td style="padding:20px 28px 4px;font-weight:600;font-size:15px">${logo}${logo ? '&nbsp;&nbsp;' : ''}<span style="vertical-align:middle">${escape(name)}</span></td></tr><tr><td style="padding:12px 28px 8px;font-size:14px">${paragraphs}</td></tr><tr><td style="padding:16px 28px 22px;border-top:1px solid #eee;color:#888;font-size:12px;line-height:1.5">${footer.map(line => escape(line)).join('<br>')}</td></tr></table>${FORMALIE_MARK}</body></html>`
  const text = `${body.split(ANSWERS).join(answersText)}\n\n--\n${footer.join('\n')}\n\nFormalie · https://formalie.com`
  return { subject, html, text, from: `${settings.emails.sender_name || name} <${fromAddress(tenant)}>`, reply_to: settings.emails.reply_to }
}
