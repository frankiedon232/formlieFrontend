<!--
  Form overview → Share card (also beside the Share tab): status, the public link (custom link
  when set — shared/utils/urls/public.ts) with copy, three equal actions (open · embed code ·
  QR code), and a summary of how the form is shared (access · limit · availability) that opens
  the Share settings. Live once the form is published.
-->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'
import { formLink, publicHosts } from '#shared/utils/urls/public'

const props = defineProps<{ form: FormSummary; accent?: string }>()
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
const route = useRoute()
const onShareTab = computed(() => route.path.endsWith('/share'))
const live = computed(() => props.form.status === 'published')
const qrOpen = ref(false)
const embedOpen = ref(false)

/** How the form is shared, in a few words (each opens the Share settings). */
const facts = computed(() => [
  {
    icon: props.form.access === 'password' ? 'i-lucide-lock-keyhole' : 'i-lucide-globe',
    label: props.form.access === 'password' ? t('share.access.password') : t('share.access.public'),
  },
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
          <UBadge v-if="form.access === 'password'" :label="t('share.access.badge')" color="neutral" variant="outline" icon="i-lucide-lock-keyhole" size="sm" />
          <UBadge :label="live ? t('forms.overview.live') : t(`status.${form.status}`)" :color="live ? 'success' : 'neutral'" variant="subtle" :icon="live ? 'i-lucide-radio' : 'i-lucide-circle-dashed'" size="sm" />
        </div>
      </div>
      <p class="text-xs text-muted">{{ live ? t('forms.overview.shareLive') : t('forms.overview.shareNotLive') }}</p>
    </div>

    <!-- The link. -->
    <div :class="live ? '' : 'opacity-60'">
      <AppCopyField :label="form.custom_link ? t('share.summary.customLink') : t('forms.overview.link')" :value="fill" monospace />
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
      <component
        :is="onShareTab ? 'div' : resolveComponent('NuxtLink')"
        :to="onShareTab ? undefined : `/forms/${form.id}/share`"
        class="flex items-center gap-3 px-4 py-3 sm:px-5"
        :class="onShareTab ? '' : 'rounded-b-lg transition-colors hover:bg-elevated/60 focus-visible:outline-2 focus-visible:outline-inverted'"
      >
        <div class="flex min-w-0 flex-1 flex-wrap gap-x-3 gap-y-1">
          <span v-for="fact in facts" :key="fact.label" class="flex items-center gap-1.5 text-xs text-toned">
            <UIcon :name="fact.icon" class="size-3.5 shrink-0 text-muted" />{{ fact.label }}
          </span>
        </div>
        <span v-if="!onShareTab" class="flex shrink-0 items-center gap-1 text-xs font-medium text-highlighted">
          {{ t('share.open') }}<UIcon name="i-lucide-chevron-right" class="size-3.5 rtl:rotate-180" />
        </span>
      </component>
    </div>

    <FormsShareEmbedModal v-model:open="embedOpen" :url="embed" :form-name="form.name" :live="live" />
    <FormsShareQrModal v-model:open="qrOpen" :url="fill" :form-name="form.name" :accent="accent" :live="live" />
  </UCard>
</template>
