/**
 * Notifications (F14 M4, docs/API-CONTRACT.md → Notifications): which events tell whom (Settings →
 * Notifications), and each person's feed behind the bell. Texts are translated on the client from
 * `kind` + `params`; nothing personal from responses is put in them.
 */

/** `access_requested` (owner 2026-10-15): someone asks to join, through the workspace's sign-up link, a personal sign-up
 *  link or single sign-on (domains listed, new accounts off); params { name, email, via: link | invite | sso }. */
export const NOTIFICATION_EVENTS = ['response_new', 'response_duplicate', 'form_limit', 'form_closing', 'export_ready', 'webhook_failing', 'security_alert', 'access_requested'] as const
export type NotificationEvent = (typeof NOTIFICATION_EVENTS)[number]
/**
 * Events from the Formalie team (B16), in the feed only (not in Settings → Notifications): a request for
 * support access goes to the workspace's admins, a message to the people the team chose.
 */
export const PLATFORM_EVENTS = ['support_request', 'platform_message'] as const
export type FeedEvent = NotificationEvent | (typeof PLATFORM_EVENTS)[number]

/** Who hears about it: admins, everyone in the workspace, or chosen people. Export ready always goes to whoever asked. */
export type NotificationAudience = 'admins' | 'everyone' | 'people'

export interface NotificationRule {
  in_app: boolean
  email: boolean
  to: NotificationAudience
  /** Person ids when `to` is `people`. */
  people: string[]
}

export interface NotificationSettings {
  events: Record<NotificationEvent, NotificationRule>
  /** One summary email a day instead of an email each time (in-app stays instant). */
  digest: { enabled: boolean; hour: number }
}

const rule = (in_app: boolean, email: boolean, to: NotificationAudience = 'admins'): NotificationRule => ({ in_app, email, to, people: [] })

/** Each event's rule until the workspace changes it: responses in the app for everyone, problems and requests to join
 *  also by email to admins. The backend ports these (parity). */
export const DEFAULT_NOTIFICATION_RULES: Record<NotificationEvent, NotificationRule> = {
  response_new: rule(true, false, 'everyone'),
  response_duplicate: rule(true, false),
  form_limit: rule(true, true),
  form_closing: rule(true, true),
  export_ready: rule(true, false),
  webhook_failing: rule(true, true),
  security_alert: rule(true, true),
  access_requested: rule(true, true),
}

/** A saved section from before an event existed reads that event with its default rule (as the backend does). */
export function withNotificationDefaults(settings: NotificationSettings): NotificationSettings {
  const events = { ...settings.events }
  for (const key of NOTIFICATION_EVENTS) events[key] ??= structuredClone(DEFAULT_NOTIFICATION_RULES[key])
  return { ...settings, events }
}

/** One item in a person's feed. */
export interface AppNotification {
  id: string
  event: FeedEvent
  /** Values for the translated text: form name, count, export file name… */
  params: Record<string, string | number>
  /** Where clicking it goes (an in-app path). */
  link: string | null
  created_at: string
  read_at: string | null
}

/** GET /notifications */
export interface NotificationFeed {
  items: AppNotification[]
  unread: number
}
