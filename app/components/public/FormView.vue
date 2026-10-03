<!--
  A public form (F10) — `/{formKey}/fill` (full page) and `/{formKey}/embed` (no page chrome, for
  iframes). Server-rendered: the first response holds the whole form, its SEO tags and the right
  status code. States: not found · not published yet · closed · open. The respondent's language:
  `?lang=xx` when the form offers it, otherwise the form's main language (decision 73). Answers are
  sent once per fill-in session (usePublicSubmit).
-->
<script setup lang="ts">
import { THEME_FRAMES, type ThemeFrame } from '#shared/utils/forms/theme'
import { formLink, publicHosts } from '#shared/utils/urls/public'

const props = defineProps<{ formKey: string; embed?: boolean }>()
const { t } = useI18n()
const route = useRoute()
const config = useRuntimeConfig()
const url = useRequestURL()

const { form, errorCode } = await usePublicForm(props.formKey)
const { submit, alreadySent, another } = usePublicSubmit(props.formKey, props.embed ? 'embed' : 'link')
const respondent = computed(() => ({ alreadySent: alreadySent.value, another }))

// Development only: `?frame=spotlight` previews another page style without changing the form.
const devFrame = import.meta.dev && THEME_FRAMES.includes(route.query.frame as ThemeFrame) ? (route.query.frame as ThemeFrame) : null
const schema = computed(() => {
  const value = form.value?.schema
  if (!value || !devFrame) return value ?? null
  const theme = (value.theme ?? {}) as { frame?: Record<string, unknown> }
  return { ...value, theme: { ...theme, frame: { ...theme.frame, style: devFrame } } }
})

// ── Language ─────────────────────────────────────────────────────────────────────────
const nuxtApp = useNuxtApp()
const language = computed(() => {
  const wanted = typeof route.query.lang === 'string' ? route.query.lang : null
  const offered = form.value?.languages ?? []
  return wanted && offered.includes(wanted) ? wanted : (form.value?.language ?? 'en')
})
/** Switch the interface language for this page only (no cookie: a signed-in person's portal language stays). */
async function useLanguage(code: string) {
  const i18n = nuxtApp.$i18n
  if (i18n.locale.value === code) return
  await i18n.loadLocaleMessages(code as Parameters<typeof i18n.loadLocaleMessages>[0])
  ;(i18n.locale as unknown as { value: string }).value = code
}
await useLanguage(language.value)
watch(language, code => void useLanguage(code))
const dir = computed(() => APP_LOCALES.find(locale => locale.code === language.value)?.dir ?? 'ltr')

// ── State, status code, SEO ──────────────────────────────────────────────────────────
type View = 'open' | 'closed' | 'not_published' | 'expired' | 'scheduled' | 'not_found' | 'error'
const view = computed<View>(() => {
  if (errorCode.value === 'FRM-FORM-1001') return 'not_found'
  if (errorCode.value || !form.value) return 'error'
  return form.value.state
})
if (import.meta.server && ['not_found', 'error', 'expired'].includes(view.value)) {
  const event = useRequestEvent()
  if (event) setResponseStatus(event, view.value === 'not_found' ? 404 : view.value === 'expired' ? 410 : 503)
}
const { locale } = useI18n()
const longDate = (iso: string | null | undefined) =>
  iso ? new Intl.DateTimeFormat(locale.value, { dateStyle: 'long', timeStyle: 'short' }).format(new Date(iso)) : ''

const canonical = computed(() =>
  form.value ? formLink(publicHosts(config.public, url.port), form.value.key, 'fill', form.value.workspace.subdomain) : undefined,
)
const title = computed(() => (form.value ? `${form.value.seo.title} · ${form.value.workspace.name}` : t('public.notFound.title')))
useHead({
  htmlAttrs: { lang: language, dir },
  link: computed(() => (canonical.value && !props.embed ? [{ rel: 'canonical', href: canonical.value }] : [])),
})
useSeoMeta({
  title,
  description: () => form.value?.seo.description || undefined,
  ogTitle: () => form.value?.seo.title,
  ogDescription: () => form.value?.seo.description || undefined,
  ogImage: () => form.value?.seo.image ?? undefined,
  ogUrl: () => canonical.value,
  ogType: 'website',
  ogSiteName: () => form.value?.workspace.name,
  twitterCard: () => (form.value?.seo.image ? 'summary_large_image' : 'summary'),
  // Embeds, closed and unpublished forms are never listed; open forms follow their SEO setting.
  robots: () => (props.embed || view.value !== 'open' || form.value?.seo.noindex ? 'noindex, nofollow' : 'index, follow'),
})

// ── Embed: tell the parent page how tall the form is (auto-resize). ──────────────────
const root = useTemplateRef<HTMLElement>('root')
if (import.meta.client && props.embed) {
  useResizeObserver(root, entries => {
    const height = Math.ceil(entries[0]?.contentRect.height ?? 0)
    if (height && window.parent !== window) window.parent.postMessage({ type: 'formalie:resize', key: props.formKey, height }, '*')
  })
}

const year = new Date().getFullYear()
const browser = useInAppBrowser()
function visit(event: MouseEvent) {
  const site = form.value?.workspace.website
  if (!site || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  browser.open(site, form.value?.workspace.name)
}
const orgInitials = computed(() =>
  (form.value?.workspace.name ?? '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(word => word[0]!.toUpperCase())
    .join(''),
)
const message = computed(() => {
  switch (view.value) {
    case 'not_found':
      return { icon: 'i-lucide-file-question', title: t('public.notFound.title'), description: t('public.notFound.desc') }
    case 'closed':
      return { icon: 'i-lucide-lock', title: t('public.closed.title'), description: t('public.closed.desc') }
    case 'not_published':
      return { icon: 'i-lucide-file-clock', title: t('public.notPublished.title'), description: t('public.notPublished.desc') }
    case 'expired':
      return { icon: 'i-lucide-calendar-x-2', title: t('public.expired.title'), description: t('public.expired.desc', { date: longDate(form.value?.closes_at) }) }
    case 'scheduled':
      return { icon: 'i-lucide-calendar-clock', title: t('public.scheduled.title'), description: t('public.scheduled.desc', { date: longDate(form.value?.opens_at) }) }
    case 'error':
      return { icon: 'i-lucide-cloud-off', title: t('public.error.title'), description: t('public.error.desc') }
    default:
      return null
  }
})
</script>

<template>
  <div ref="root" :class="embed ? '' : 'flex min-h-dvh flex-col'">
    <FormsRendererPage v-if="view === 'open' && schema" :schema="schema" :title="form?.name ?? ''" :submit="submit" :respondent="respondent" :framed="!embed" :class="embed ? '' : 'flex-1'" />

    <!-- Closed / not open yet: still the organisation's page (bar + footer); unknown links stay neutral. -->
    <header v-if="view !== 'open' && form && !embed" class="border-b border-default bg-default">
      <div class="mx-auto flex h-16 max-w-5xl items-center justify-between gap-3 px-4 sm:px-6">
        <FormsRendererFrameOrg :org="{ name: form.workspace.name, logo: form.workspace.logo_url }" :initials="orgInitials" accent="var(--ui-bg-inverted)" on-accent="var(--ui-bg)" />
        <UButton
          v-if="form.workspace.website"
          :to="form.workspace.website"
          target="_blank"
          external
          :label="t('public.frame.website')"
          trailing-icon="i-lucide-arrow-up-right"
          color="neutral"
          variant="outline"
          size="sm"
          class="rounded-full max-sm:[&>span:first-child]:sr-only"
          @click="visit"
        />
      </div>
    </header>
    <div v-if="view !== 'open' || !schema" class="flex flex-1 items-center justify-center bg-elevated/40 px-4 py-16">
      <UCard class="w-full max-w-md" :ui="{ body: 'p-6 sm:p-8' }">
        <div class="flex flex-col items-center gap-3 text-center">
          <span class="flex size-12 items-center justify-center rounded-full bg-elevated">
            <UIcon :name="message?.icon ?? 'i-lucide-info'" class="size-6 text-muted" />
          </span>
          <h1 class="text-lg font-semibold text-highlighted">{{ message?.title }}</h1>
          <p class="text-sm text-muted">{{ message?.description }}</p>
          <p v-if="form && view !== 'not_found'" class="text-xs text-dimmed">{{ form.name }} · {{ form.workspace.name }}</p>
          <UButton v-if="view === 'error'" :label="t('common.retry')" icon="i-lucide-rotate-cw" color="neutral" variant="outline" @click="reloadNuxtApp()" />
        </div>
      </UCard>
    </div>

    <FormsRendererFrameFooter
      v-if="!embed && view !== 'open'"
      class="bg-default"
      :org="{ name: form?.workspace.name ?? 'Formalie' }"
      :year="year"
      :slim="!form"
    />
    <!-- Website, terms and privacy open here, over the form (nothing typed in is lost). -->
    <ClientOnly><PublicBrowser /></ClientOnly>
  </div>
</template>
