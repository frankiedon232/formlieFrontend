/**
 * Notifications (F14 M4, docs/API-CONTRACT.md → Notifications): which events tell whom (Settings →
 * Notifications), and each person's feed behind the bell. Texts are translated on the client from
 * `kind` + `params`; nothing personal from responses is put in them.
 */

export const NOTIFICATION_EVENTS = ['response_new', 'response_duplicate', 'form_limit', 'form_closing', 'export_ready', 'webhook_failing', 'security_alert'] as const
export type NotificationEvent = (typeof NOTIFICATION_EVENTS)[number]

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

/** One item in a person's feed. */
export interface AppNotification {
  id: string
  event: NotificationEvent
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
