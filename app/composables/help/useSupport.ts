/**
 * Contact support from anywhere (F25, owner 2026-10-10): Formalie's own "Contact support" form opens in the app's
 * browser window (we collect our own data with our own forms), with what the app knows filled in: the person's
 * name and email, the workspace and its plan, the page it was opened from, and what it is about when known.
 */
import type { HelpCategory, SupportTopic } from '#shared/types/help'

export function useSupport() {
  const { t } = useI18n()
  const route = useRoute()
  const session = useSession()
  const tenant = useTenant()
  const browser = useAppBrowser()
  const billing = useBilling()

  function contact(options: { topic?: SupportTopic; area?: HelpCategory | null; subject?: string; article?: string | null } = {}) {
    const user = session.user.value
    browser.openForm('support', t('help.contact.title'), {
      topic: options.topic,
      area: options.area ?? undefined,
      subject: options.subject,
      article: options.article ?? undefined,
      name: user ? `${user.first_name} ${user.last_name}`.trim() : undefined,
      email: user?.email,
      workspace: tenant.profile.value?.subdomain,
      plan: billing.overview.value?.subscription.plan,
      page: route.fullPath,
    })
  }

  /** The Enterprise enquiry (Settings → Plans, "Contact us"; Privacy: a region, with what is needed filled in). */
  function enquire(extra: { needs?: string; residency?: string } = {}) {
    const user = session.user.value
    browser.openForm('enterprise', t('billing.enquiry.title'), {
      company: tenant.profile.value?.name,
      name: user ? `${user.first_name} ${user.last_name}`.trim() : undefined,
      email: user?.email,
      workspace: tenant.profile.value?.subdomain,
      plan: billing.overview.value?.subscription.plan,
      ...extra,
    })
  }
  return { contact, enquire }
}
