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
import { ANSWERS, emailPage } from './emailLayout'

interface Defaults {
  templates: Record<EmailTemplateKey, EmailText>
  events: Record<string, { title: string; message: string }>
  layout: { footer: string; footer_form: string; answers: string; open: string; summary: string; via?: string; tagline?: string; privacy?: string; unsubscribe?: string }
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
  const body = fillIn(source.body, { ...all, answers: ANSWERS })
  const footer = [settings.emails.footer, fillIn(options.footer === 'form' ? defaults.layout.footer_form : defaults.layout.footer, all)].filter(Boolean) as string[]
  const { html, text } = emailPage(subject, body, all, { workspace: name, logoUrl: settings.branding.logo_url, brandColor: settings.branding.brand_color, footerLines: footer, texts: defaults.layout, language }, answers)
  return { subject, html, text, from: `${settings.emails.sender_name || name} <${fromAddress(tenant)}>`, reply_to: settings.emails.reply_to }
}
