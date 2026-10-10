<!--
  Tokens & headers → Headers (F13 M2; owner 2026-10-06): the only headers a call sends (Formalie-Key
  required on POST, optional on the rest; no custom headers), the organisation's address key with Rotate (the old
  key keeps working for a grace period), and the expiry tracker every answer carries.
-->
<script setup lang="ts">
import type { ApiServiceSettings } from '#shared/types/apiService'

const props = defineProps<{ settings: ApiServiceSettings | null }>()
const emit = defineEmits<{ rotateKey: [] }>()
const { t } = useI18n()
const { dateTime, relative } = useFormat()
const { can } = useCan()

const STANDARD = [
  { name: 'Authorization', value: 'Bearer <token>', when: 'always' },
  { name: 'Content-Type', value: 'application/json', when: 'always' },
  { name: 'Formalie-Key', value: '<new unique id>', when: 'post' },
] as const
// The expiry tracker: where each part comes back in an answer (owner, 2026-10-06)
const EXPIRY = [
  { name: 'Formalie-Token-Expires', key: 'header', where: 'header' },
  { name: 'meta.token_expires_at', key: 'at', where: 'body' },
  { name: 'meta.token_expires_in_days', key: 'days', where: 'body' },
] as const
const base = computed(() => (props.settings ? `${props.settings.base_url}/${props.settings.api_key}` : ''))
</script>

<template>
  <div class="grid shrink-0 gap-4 lg:grid-cols-3">
    <UCard variant="outline" class="min-w-0 lg:col-span-2" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.headers.standardTitle') }}</h2>
        <p class="text-xs text-muted">{{ t('apiService.headers.standardDesc') }}</p>
      </div>
      <ul class="divide-y divide-default overflow-hidden rounded-lg border border-default">
        <li v-for="header in STANDARD" :key="header.name" class="flex flex-col gap-1 px-3 py-2.5 sm:flex-row sm:items-center sm:gap-4">
          <code class="w-48 shrink-0 font-mono text-sm font-medium text-highlighted" dir="ltr">{{ header.name }}</code>
          <code class="min-w-0 flex-1 truncate font-mono text-xs text-muted" dir="ltr">{{ header.value }}</code>
          <UBadge :label="t(`apiService.headers.when.${header.when}`)" color="neutral" variant="outline" size="sm" class="w-fit shrink-0 rounded-md" />
        </li>
      </ul>
    </UCard>

    <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.key.title') }}</h2>
        <p class="text-xs text-muted">{{ t('apiService.key.desc') }}</p>
      </div>
      <USkeleton v-if="!settings" class="h-9 w-full" />
      <template v-else>
        <AppCopyField :value="settings.api_key" :label="t('apiService.key.current')" monospace />
        <p class="truncate font-mono text-[11px] text-muted" dir="ltr">{{ base }}/…</p>
        <UAlert v-if="settings.previous_key && settings.previous_until" icon="i-lucide-refresh-cw" color="warning" variant="subtle" :title="t('apiService.key.previous', { key: settings.previous_key, until: dateTime(settings.previous_until) })" />
        <p v-else-if="settings.rotated_at" class="text-xs text-muted">
          {{ t('apiService.key.rotatedAt', { when: relative(settings.rotated_at) }) }}
        </p>
        <UButton v-if="can('api.key')" :label="t('apiService.key.rotate')" icon="i-lucide-refresh-cw" color="neutral" variant="outline" class="mt-auto w-fit" @click="emit('rotateKey')" />
      </template>
    </UCard>

    <UCard variant="outline" class="min-w-0 overflow-hidden lg:col-span-3" :ui="{ body: 'grid p-0 sm:p-0 lg:grid-cols-2' }">
      <div class="flex min-w-0 flex-col gap-3 p-4 sm:p-5">
        <div class="flex items-center gap-2.5">
          <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon name="i-lucide-calendar-clock" class="size-4 text-highlighted" /></span>
          <div class="min-w-0">
            <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.headers.expiryTitle') }}</h2>
            <p class="text-xs text-muted">{{ t('apiService.headers.expiryDesc') }}</p>
          </div>
        </div>
        <ul class="divide-y divide-default overflow-hidden rounded-lg border border-default">
          <li v-for="field in EXPIRY" :key="field.name" class="flex flex-col gap-1 px-3 py-2.5 sm:flex-row sm:items-center sm:gap-3">
            <code class="shrink-0 font-mono text-xs font-medium text-highlighted sm:w-52" dir="ltr">{{ field.name }}</code>
            <span class="min-w-0 flex-1 text-xs text-muted">{{ t(`apiService.headers.expiryField.${field.key}`) }}</span>
            <UBadge :label="t(`apiService.headers.expiryWhere.${field.where}`)" color="neutral" :variant="field.where === 'header' ? 'outline' : 'soft'" size="sm" class="w-fit shrink-0 rounded-md" />
          </li>
        </ul>
      </div>
      <div class="flex min-w-0 flex-col justify-center gap-2 border-t border-default bg-neutral-950 p-4 sm:p-5 lg:border-s lg:border-t-0">
        <span class="text-[11px] font-semibold tracking-wide text-neutral-400 uppercase">{{ t('apiService.headers.expirySample') }}</span>
        <pre class="overflow-auto rounded-lg bg-neutral-900 p-3 font-mono text-xs leading-relaxed text-neutral-300" dir="ltr"><span class="text-neutral-500">HTTP/1.1 200 OK</span>
<span class="text-white">Formalie-Token-Expires</span>: 2027-01-01T00:00:00Z

{
  "data": { … },
  "meta": {
    <span class="text-white">"token_expires_at"</span>: "2027-01-01T00:00:00Z",
    <span class="text-white">"token_expires_in_days"</span>: 87
  }
}</pre>
      </div>
    </UCard>
  </div>
</template>
