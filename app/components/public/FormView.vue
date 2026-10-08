<!--
  A public form (F10), `/{formKey}/fill` (full page) and `/{formKey}/embed` (no page chrome, for
  iframes). Server-rendered: the first response holds the whole form, its SEO tags and the right
  status code. States: not found · not published yet · closed · open. The respondent's language:
  `?lang=xx`, else the browser's language, when the form offers it, otherwise its main language,
  with a switcher when it has several (decisions 73 and 99, usePublicLanguage). Answers are
  sent once per fill-in session (usePublicSubmit).
-->
<script setup lang="ts">
import { THEME_FRAMES, type ThemeFrame } from '#shared/utils/forms/theme'
import { translateSchema } from '#shared/utils/forms/translations'
import { formLink, publicHosts } from '#shared/utils/urls/public'

const props = defineProps<{ formKey: string; embed?: boolean }>()
const { t } = useI18n()
const route = useRoute()
const config = useRuntimeConfig()
const url = useRequestURL()

const { form, errorCode, refresh } = await usePublicForm(props.formKey, props.embed ? 'embed' : 'link')
const resumeOn = computed(() => !!form.value?.schema?.settings?.save_resume)
const resume = usePublicResume(props.formKey, resumeOn)
const { submit, alreadySent, another, confirmDifferent, sendCode, confirmCode, prepareProof } = usePublicSubmit(props.formKey, props.embed ? 'embed' : 'link', resume)
const { upload } = usePublicUploads(props.formKey)
const respondent = computed(() => ({
  org: form.value ? { name: form.value.workspace.name, website: form.value.workspace.website } : undefined,
  embedded: !!props.embed,
  alreadySent: alreadySent.value,
  upload,
  // Long lists: their options come from the server as people type (F15 M3)
  lookup: async (field: { key: string }, { q, values, parents }: { q: string; values?: string[]; parents?: string[] }) =>
    (await api.get<{ items: { value: string; label: string }[]; total: number }>(`/public/forms/${encodeURIComponent(props.formKey)}/options`, { field: field.key, q, ...(values?.length ? { values: values.join(',') } : {}), ...(parents ? { parents: parents.join(',') } : {}), language: language.value, channel: props.embed ? 'embed' : 'link' }, { background: true })).data,
  another,
  confirmDifferent,
  sendCode,
  confirmCode,
  resume: resumeOn.value
    ? { initial: resume.initial.value, state: resume.state.value, savedAt: resume.savedAt.value, save: resume.save, later: resume.later }
    : undefined,
}))

// ── Language (decisions 73 and 99): link, browser, else the main one; the switcher changes it.
const { language, offered: languages, choose: chooseLanguage, dir } = await usePublicLanguage(props.formKey, form)

// Development only: `?frame=spotlight` previews another page style without changing the form.
const devFrame = import.meta.dev && THEME_FRAMES.includes(route.query.frame as ThemeFrame) ? (route.query.frame as ThemeFrame) : null
const schema = computed(() => {
  const base = form.value?.schema
  // The questions in the respondent's language (missing translations show the main language).
  const value = base ? translateSchema(base, language.value) : null
  if (!value || !devFrame) return value ?? null
  const theme = (value.theme ?? {}) as { frame?: Record<string, unknown> }
  return { ...value, theme: { ...theme, frame: { ...theme.frame, style: devFrame } } }
})

// ── State, status code, SEO ──────────────────────────────────────────────────────────
/** Arriving with a personal invitation link or a sign-in pass: "Opening…" until it is checked, never a locked page first. */
const arriving = ref(!!(route.query.invite || route.query.pass))
type View = 'open' | 'opening' | 'locked' | 'closed' | 'not_published' | 'expired' | 'scheduled' | 'limit_reached' | 'not_found' | 'error'
const view = computed<View>(() => {
  if (errorCode.value === 'FRM-FORM-1001') return 'not_found'
  if (errorCode.value || !form.value) return 'error'
  if (form.value.state === 'open' && form.value.locked) return arriving.value ? 'opening' : 'locked'
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

// ── Embed: which websites may show it in a frame (Share settings → Embed, decision 94; the
// portal and /fill pages may never be framed). Development has no full policy, so only this rule.
if (import.meta.server && props.embed) {
  const event = useRequestEvent()
  const response = event?.node.res
  if (response) {
    const ancestors = `frame-ancestors ${form.value?.embed_ancestors ?? '*'}`
    response.removeHeader('x-frame-options')
    const policy = response.getHeader('content-security-policy')
    response.setHeader('content-security-policy', typeof policy === 'string' ? policy.replace("frame-ancestors 'self'", ancestors) : ancestors)
  }
}

// ── Embed: tell the parent page how tall the form is (auto-resize). ──────────────────
const root = useTemplateRef<HTMLElement>('root')
if (import.meta.client && props.embed) {
  useResizeObserver(root, entries => {
    const height = Math.ceil(entries[0]?.contentRect.height ?? 0)
    if (height && window.parent !== window) window.parent.postMessage({ type: 'formalie:resize', key: props.formKey, height }, '*')
  })
}

// Password forms: after the right password, load the questions and start the spam check.
async function onUnlocked() {
  // "Opening your form…" until the questions are here (never a still, locked card).
  arriving.value = true
  try {
    await refresh()
    prepareProof()
  } finally {
    arriving.value = false
  }
}

// Invitation links (?invite=) and member sign-in passes (?pass=) open the form by themselves; the
// token leaves the address bar at once (history, screenshots, shared tabs).
const accessFailed = ref<'invite' | 'pass' | null>(null)
const api = useApi()
onMounted(async () => {
  const address = new URL(location.href)
  const invite = address.searchParams.get('invite')
  const pass = address.searchParams.get('pass')
  if (!invite && !pass) return void (arriving.value = false)
  address.searchParams.delete('invite')
  address.searchParams.delete('pass')
  history.replaceState(history.state, '', address.pathname + address.search + address.hash)
  try {
    await api.post(`/public/forms/${encodeURIComponent(props.formKey)}/unlock`, invite ? { invite } : { pass })
    await onUnlocked()
  } catch {
    accessFailed.value = invite ? 'invite' : 'pass'
  } finally {
    arriving.value = false
  }
})

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
    case 'opening':
      return { icon: 'i-lucide-loader-circle', title: t('public.opening'), description: '' }
    case 'locked':
      return form.value?.lock === 'invite'
        ? { icon: 'i-lucide-mail-check', title: t('public.invite.title'), description: t('public.invite.desc') }
        : form.value?.lock === 'organisation'
          ? { icon: 'i-lucide-building-2', title: t('public.member.title', { org: form.value.workspace.name }), description: t('public.member.desc') }
          : { icon: 'i-lucide-lock-keyhole', title: t('public.locked.title'), description: t('public.locked.desc') }
    case 'limit_reached':
      return { icon: 'i-lucide-users-round', title: t('public.full.title'), description: t('public.full.desc') }
    case 'error':
      return { icon: 'i-lucide-cloud-off', title: t('public.error.title'), description: t('public.error.desc') }
    default:
      return null
  }
})
</script>

<template>
  <div ref="root" :class="embed ? '' : 'flex min-h-dvh flex-col'">
    <!-- Invitation or signed-in member: who is filling in (kept with the response). -->
    <div v-if="view === 'open' && form?.visitor" class="border-b border-default bg-elevated/60 px-4 py-2 text-center text-xs text-toned">
      <UIcon name="i-lucide-user-round-check" class="me-1 inline size-3.5 align-[-2px]" />{{ t('public.visitor', { who: form.visitor.name ? `${form.visitor.name} (${form.visitor.email})` : form.visitor.email }) }}
    </div>
    <FormsRendererPage v-if="view === 'open' && schema" :schema="schema" :title="form?.name ?? ''" :submit="submit" :respondent="respondent" :framed="!embed" :languages="languages" :language="language" :class="embed ? '' : 'flex-1'" @language="chooseLanguage" />

    <!-- Closed / not open yet: still the organisation's page (bar + footer); unknown links stay neutral. -->
    <header v-if="view !== 'open' && form && !embed" class="border-b border-default bg-default">
      <div class="mx-auto flex h-16 max-w-5xl items-center justify-between gap-3 px-4 sm:px-6">
        <FormsRendererFrameOrg :org="{ name: form.workspace.name, logo: form.workspace.logo_url }" :initials="orgInitials" accent="var(--ui-bg-inverted)" on-accent="var(--ui-bg)" />
        <FormsRendererLanguageSwitch :model-value="language" :languages="languages" class="ms-auto" @update:model-value="chooseLanguage" />
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
            <UIcon :name="message?.icon ?? 'i-lucide-info'" class="size-6 text-muted" :class="view === 'opening' ? 'animate-spin' : ''" />
          </span>
          <h1 class="text-lg font-semibold text-highlighted">{{ message?.title }}</h1>
          <p v-if="message?.description" class="text-sm text-muted">{{ message?.description }}</p>
          <p v-if="form && view !== 'not_found'" class="text-xs text-dimmed">{{ form.name }} · {{ form.workspace.name }}</p>
          <PublicAccess v-if="view === 'locked' && form" :form="form" :form-key="formKey" :failed="accessFailed" :embed="embed" class="w-full" @unlocked="onUnlocked" />
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
