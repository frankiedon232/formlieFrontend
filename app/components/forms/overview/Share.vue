<!--
  Form overview → Share card (also beside the Share tab): status, the public link (custom link
  when set, shared/utils/urls/public.ts) with copy, three equal actions (open · embed code ·
  QR code), and a summary of how the form is shared (access · limit · availability) that opens
  the Share settings (editors only, decision 97). Live once the form is published.
-->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'
import { formLink, publicHosts, shortLink } from '#shared/utils/urls/public'

const props = defineProps<{ form: FormSummary; accent?: string; readOnly?: boolean }>()
const { t } = useI18n()
const config = useRuntimeConfig().public
const tenant = useTenant()
const request = useRequestURL()
const { date, number } = useFormat()

const hosts = computed(() => publicHosts(config, request.port))
const sub = computed(() => tenant.profile.value?.subdomain ?? null)
// The custom link when there is one (F10 M3); the key keeps working too.
const address = computed(() => props.form.custom_link || props.form.public_key)
const fill = computed(() => formLink(hosts.value, address.value, 'fill', sub.value))
const embed = computed(() => formLink(hosts.value, address.value, 'embed', sub.value))
// Short link (F10 M3): shown under the link and used for the QR code (a shorter code is easier to scan).
const short = computed(() => (props.form.short_code ? shortLink(hosts.value, props.form.short_code) : null))
const route = useRoute()
const onShareTab = computed(() => route.path.endsWith('/share'))
const live = computed(() => props.form.status === 'published')
const qrOpen = ref(false)
const embedOpen = ref(false)

/** Who can open it: all four modes (the badge shows every mode but "anyone with the link"). */
const ACCESS_ICON = { public: 'i-lucide-globe', password: 'i-lucide-lock-keyhole', invite: 'i-lucide-mail-check', organisation: 'i-lucide-building-2' } as const
const access = computed(() => ({ icon: ACCESS_ICON[props.form.access] ?? ACCESS_ICON.public, label: t(`share.access.${props.form.access ?? 'public'}`) }))
/** How the form is shared, in a few words (each opens the Share settings). */
const facts = computed(() => [
  access.value,
  {
    icon: 'i-lucide-gauge',
    label: props.form.response_limit != null ? t('share.summary.limit', { n: number(props.form.response_limit) }) : t('share.summary.noLimit'),
  },
  ...(props.form.closes_at ? [{ icon: 'i-lucide-calendar-x-2', label: t('share.summary.until', { date: date(props.form.closes_at) }) }] : []),
])
const actions = computed(() => [
  { key: 'open', label: t('forms.overview.openLink'), icon: 'i-lucide-external-link', to: fill.value, disabled: !live.value },
  { key: 'embed', label: t('forms.overview.embedCode'), icon: 'i-lucide-code-xml', onClick: () => (embedOpen.value = true) },
  { key: 'qr', label: t('forms.overview.qr'), icon: 'i-lucide-qr-code', onClick: () => (qrOpen.value = true) },
])
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
    <!-- Header: title + status on one line, one sentence under it. -->
    <div class="flex flex-col gap-1">
      <div class="flex items-center justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('forms.overview.shareTitle') }}</h2>
        <div class="flex shrink-0 items-center gap-1.5">
          <UBadge v-if="form.access && form.access !== 'public'" :label="form.access === 'password' ? t('share.access.badge') : access.label" color="neutral" variant="outline" :icon="access.icon" size="sm" class="max-sm:[&>span:last-child]:sr-only" />
          <UBadge :label="live ? t('forms.overview.live') : t(`status.${form.status}`)" :color="live ? 'success' : 'neutral'" variant="subtle" :icon="live ? 'i-lucide-radio' : 'i-lucide-circle-dashed'" size="sm" />
        </div>
      </div>
      <p class="text-xs text-muted">{{ live ? t('forms.overview.shareLive') : t('forms.overview.shareNotLive') }}</p>
    </div>

    <!-- The link. -->
    <div :class="live ? '' : 'opacity-60'">
      <AppCopyField :label="form.custom_link ? t('share.summary.customLink') : t('forms.overview.link')" :value="fill" monospace />
      <AppCopyField v-if="short" :label="t('share.short.label')" :value="short" monospace class="mt-3" />
    </div>

    <!-- Three equal actions. -->
    <div class="grid grid-cols-3 gap-2">
      <UButton
        v-for="action in actions"
        :key="action.key"
        :to="action.to"
        :target="action.to ? '_blank' : undefined"
        :disabled="action.disabled"
        color="neutral"
        variant="outline"
        class="flex h-auto flex-col items-center justify-center gap-1.5 px-1 py-2.5 text-center"
        @click="action.onClick?.()"
      >
        <UIcon :name="action.icon" class="size-4" />
        <span class="text-xs leading-tight">{{ action.label }}</span>
      </UButton>
    </div>

    <!-- How it's shared → Share settings. -->
    <div class="-mx-4 -mb-4 border-t border-default sm:-mx-5 sm:-mb-5">
      <div v-if="onShareTab || readOnly" class="flex flex-wrap gap-x-3 gap-y-1 px-4 py-3 sm:px-5">
        <span v-for="fact in facts" :key="fact.label" class="flex items-center gap-1.5 text-xs text-toned">
          <UIcon :name="fact.icon" class="size-3.5 shrink-0 text-muted" />{{ fact.label }}
        </span>
      </div>
      <NuxtLink
        v-else
        :to="`/forms/${form.id}/share`"
        class="flex items-center gap-3 rounded-b-lg px-4 py-3 transition-colors hover:bg-elevated/60 focus-visible:outline-2 focus-visible:outline-inverted sm:px-5"
      >
        <span class="flex min-w-0 flex-1 flex-wrap gap-x-3 gap-y-1">
          <span v-for="fact in facts" :key="fact.label" class="flex items-center gap-1.5 text-xs text-toned">
            <UIcon :name="fact.icon" class="size-3.5 shrink-0 text-muted" />{{ fact.label }}
          </span>
        </span>
        <span class="flex shrink-0 items-center gap-1 text-xs font-medium text-highlighted">
          {{ t('share.open') }}<UIcon name="i-lucide-chevron-right" class="size-3.5 rtl:rotate-180" />
        </span>
      </NuxtLink>
    </div>

    <FormsShareEmbedModal v-model:open="embedOpen" :url="embed" :form-name="form.name" :live="live" />
    <FormsShareQrModal v-model:open="qrOpen" :url="short ?? fill" :form-name="form.name" :accent="accent" :live="live" />
  </UCard>
</template>
