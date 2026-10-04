<!--
  Form overview → sharing: the public link (built by shared/utils/urls/public.ts) with copy and
  open buttons, the embed code (iframe with auto height) and a QR code (PNG / SVG). Live once the
  form is published; access rules arrive with the Share settings (F10 M3).
-->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'
import { formLink, publicHosts } from '#shared/utils/urls/public'

const props = defineProps<{ form: FormSummary; accent?: string }>()
const { t } = useI18n()
const config = useRuntimeConfig().public
const tenant = useTenant()
const request = useRequestURL()

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
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <div class="mb-3 flex items-start justify-between gap-2">
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('forms.overview.shareTitle') }}</h2>
        <p class="text-xs text-muted">{{ live ? t('forms.overview.shareLive') : t('forms.overview.shareNotLive') }}</p>
      </div>
      <div class="flex shrink-0 flex-col items-end gap-1">
        <UBadge :label="live ? t('forms.overview.live') : t(`status.${form.status}`)" :color="live ? 'success' : 'neutral'" variant="subtle" :icon="live ? 'i-lucide-radio' : 'i-lucide-circle-dashed'" />
        <UBadge v-if="form.access === 'password'" :label="t('share.access.badge')" color="neutral" variant="outline" icon="i-lucide-lock-keyhole" size="sm" />
      </div>
    </div>
    <div class="flex flex-col gap-3" :class="live ? '' : 'opacity-60'">
      <AppCopyField :label="t('forms.overview.link')" :value="fill" monospace />
    </div>
    <div class="mt-3 flex flex-wrap gap-2">
      <UButton :label="t('forms.overview.openLink')" icon="i-lucide-external-link" color="neutral" variant="outline" size="sm" :to="fill" target="_blank" :disabled="!live" />
      <UButton :label="t('forms.overview.embedCode')" icon="i-lucide-code-xml" color="neutral" variant="outline" size="sm" @click="embedOpen = true" />
      <UButton :label="t('forms.overview.qr')" icon="i-lucide-qr-code" color="neutral" variant="outline" size="sm" @click="qrOpen = true" />
    </div>
    <UButton v-if="!onShareTab" :label="t('share.open')" icon="i-lucide-settings-2" color="neutral" variant="link" size="sm" class="mt-2 px-0" :to="`/forms/${form.id}/share`" />
    <FormsShareEmbedModal v-model:open="embedOpen" :url="embed" :form-name="form.name" :live="live" />
    <FormsShareQrModal v-model:open="qrOpen" :url="fill" :form-name="form.name" :accent="accent" :live="live" />
  </UCard>
</template>
