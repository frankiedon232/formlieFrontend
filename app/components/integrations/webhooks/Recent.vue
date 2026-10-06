<!-- A webhook's latest deliveries in its panel (F13 M6): event, when, result, tries; each opens the delivery; "All deliveries" opens the log filtered to it. -->
<script setup lang="ts">
import type { WebhookDelivery } from '#shared/types/integrations'
import { eventLabelKey } from '#shared/utils/integrations/webhooks'

defineProps<{ deliveries: WebhookDelivery[] | null }>()
const emit = defineEmits<{ open: [id: string]; all: [] }>()
const { t } = useI18n()
const { relative } = useFormat()
</script>

<template>
  <div class="flex flex-col gap-2">
    <div v-if="!deliveries" class="flex flex-col gap-2"><USkeleton v-for="n in 4" :key="n" class="h-12 rounded-lg" /></div>
    <AppEmpty v-else-if="!deliveries.length" size="sm" icon="i-lucide-send" :title="t('integrations.webhooks.noDeliveries')" :description="t('integrations.webhooks.noDeliveriesDesc')" />
    <template v-else>
      <button
        v-for="item in deliveries"
        :key="item.id"
        type="button"
        class="flex min-w-0 items-center gap-3 rounded-lg border border-default px-3 py-2 text-start transition-colors hover:bg-elevated/50 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        @click="emit('open', item.id)"
      >
        <UIcon :name="item.status === 'delivered' ? 'i-lucide-circle-check' : item.status === 'retrying' ? 'i-lucide-refresh-cw' : 'i-lucide-circle-x'" class="size-4 shrink-0" :class="item.status === 'delivered' ? 'text-success' : item.status === 'retrying' ? 'text-warning' : 'text-error'" />
        <div class="flex min-w-0 flex-1 flex-col">
          <span class="truncate text-sm text-highlighted">{{ t(eventLabelKey(item.event)) }}<span v-if="item.form" class="text-muted"> · {{ item.form.name }}</span></span>
          <span class="text-xs text-muted">{{ relative(item.at) }} · {{ t('integrations.webhooks.triesCount', { n: item.attempts }, item.attempts) }}</span>
        </div>
        <UBadge v-if="item.test" :label="t('integrations.webhooks.test')" color="neutral" variant="soft" size="sm" class="rounded-md" />
        <span class="font-mono text-xs text-muted tabular-nums">{{ item.status_code ?? '–' }}</span>
      </button>
      <UButton :label="t('integrations.webhooks.allDeliveries')" trailing-icon="i-lucide-arrow-right" color="neutral" variant="ghost" size="sm" class="self-start" @click="emit('all')" />
    </template>
  </div>
</template>
