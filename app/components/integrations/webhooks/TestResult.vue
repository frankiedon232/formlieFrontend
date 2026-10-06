<!-- The answer to "Send a test" (F13 M6): delivered or not, the receiver's status and time, what went wrong, its answer. -->
<script setup lang="ts">
import type { WebhookDeliveryDetail } from '#shared/types/integrations'

const props = defineProps<{ result: WebhookDeliveryDetail }>()
const emit = defineEmits<{ open: [] }>()
const { t } = useI18n()
const ok = computed(() => props.result.status === 'delivered')
const last = computed(() => props.result.history[props.result.history.length - 1] ?? null)
const reason = computed(() => (last.value?.error && !last.value.error.startsWith('HTTP') ? t(`integrations.webhooks.error.${last.value.error}`) : null))
</script>

<template>
  <div class="flex flex-col gap-2 rounded-lg border p-3" :class="ok ? 'border-default' : 'border-error/40 bg-error/5'" role="status">
    <div class="flex flex-wrap items-center gap-2">
      <UIcon :name="ok ? 'i-lucide-circle-check' : 'i-lucide-circle-x'" class="size-4" :class="ok ? 'text-success' : 'text-error'" />
      <span class="text-sm font-medium text-highlighted">{{ ok ? t('integrations.webhooks.testOk') : t('integrations.webhooks.testFailed') }}</span>
      <UBadge v-if="result.status_code" :label="String(result.status_code)" color="neutral" variant="outline" size="sm" class="rounded-md font-mono" />
      <span v-if="result.duration_ms != null" class="text-xs text-muted tabular-nums">{{ t('dataSources.ms', { n: result.duration_ms }) }}</span>
      <UButton :label="t('integrations.webhooks.details')" color="neutral" variant="link" size="xs" class="ms-auto" @click="emit('open')" />
    </div>
    <p v-if="reason" class="text-xs text-muted">{{ reason }}</p>
    <pre v-if="result.response?.body" class="max-h-32 overflow-auto rounded-md bg-elevated/50 p-2 font-mono text-[11px] text-default" dir="ltr">{{ result.response.body }}</pre>
  </div>
</template>
