/**
 * Starter templates offered in onboarding (and later at the top of the Templates gallery, F9).
 * Names / descriptions live in i18n under `templates.starter.<key>`; the full schemas arrive with F9.
 */
export const STARTER_TEMPLATES = [
  { key: 'customer_feedback', icon: 'i-lucide-message-square-heart', fields: 8 },
  { key: 'event_registration', icon: 'i-lucide-calendar-check', fields: 10 },
  { key: 'job_application', icon: 'i-lucide-briefcase', fields: 12 },
  { key: 'employee_onboarding', icon: 'i-lucide-user-round-plus', fields: 15 },
  { key: 'contact_lead', icon: 'i-lucide-contact', fields: 6 },
  { key: 'incident_report', icon: 'i-lucide-triangle-alert', fields: 11 },
] as const

export type StarterTemplateKey = (typeof STARTER_TEMPLATES)[number]['key']

export const STARTER_TEMPLATE_KEYS = STARTER_TEMPLATES.map(item => item.key) as StarterTemplateKey[]
