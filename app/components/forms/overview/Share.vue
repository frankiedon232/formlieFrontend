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
const fill = computed(() => formLink(hosts.value, props.form.public_key, 'fill', sub.value))
const embed = computed(() => formLink(hosts.value, props.form.public_key, 'embed', sub.value))
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
      <UBadge :label="live ? t('forms.overview.live') : t(`status.${form.status}`)" :color="live ? 'success' : 'neutral'" variant="subtle" :icon="live ? 'i-lucide-radio' : 'i-lucide-circle-dashed'" />
    </div>
    <div class="flex flex-col gap-3" :class="live ? '' : 'opacity-60'">
      <AppCopyField :label="t('forms.overview.link')" :value="fill" monospace />
    </div>
    <div class="mt-3 flex flex-wrap gap-2">
      <UButton :label="t('forms.overview.openLink')" icon="i-lucide-external-link" color="neutral" variant="outline" size="sm" :to="fill" target="_blank" :disabled="!live" />
      <UButton :label="t('forms.overview.embedCode')" icon="i-lucide-code-xml" color="neutral" variant="outline" size="sm" @click="embedOpen = true" />
      <UButton :label="t('forms.overview.qr')" icon="i-lucide-qr-code" color="neutral" variant="outline" size="sm" @click="qrOpen = true" />
    </div>
    <FormsShareEmbedModal v-model:open="embedOpen" :url="embed" :form-name="form.name" :live="live" />
    <FormsShareQrModal v-model:open="qrOpen" :url="fill" :form-name="form.name" :accent="accent" :live="live" />
  </UCard>
</template>
