<!--
  The latest Formalie support sessions in this workspace (B16): who, read only or with changes, when it
  started and ended, and why it ended. A live one is marked. What they did is in the audit trail.
-->
<script setup lang="ts">
import type { SupportSessionRow } from '#shared/types/support'

defineProps<{ sessions: SupportSessionRow[] }>()
const { t } = useI18n()
const { moment, dateTime } = useFormat()
</script>

<template>
  <div class="flex flex-col rounded-lg border border-default">
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-default px-3 py-2">
      <span class="text-xs font-medium text-highlighted">{{ t('support.access.sessions') }}</span>
      <UButton :label="t('support.access.inAudit')" icon="i-lucide-scroll-text" color="neutral" variant="link" size="xs" to="/audit" />
    </div>
    <AppEmpty v-if="!sessions.length" size="xs" icon="i-lucide-life-buoy" :title="t('support.access.noSessions')" :description="t('support.access.noSessionsDesc')" />
    <ul v-else class="flex max-h-72 flex-col divide-y divide-default overflow-y-auto">
      <li v-for="item in sessions" :key="item.id" class="flex items-center gap-3 px-3 py-2.5">
        <span class="flex size-8 shrink-0 items-center justify-center rounded-lg border border-default"><UIcon :name="item.mode === 'write' ? 'i-lucide-pencil' : 'i-lucide-eye'" class="size-4 text-muted" /></span>
        <span class="flex min-w-0 flex-1 flex-col">
          <span class="flex min-w-0 items-center gap-2">
            <span class="truncate text-sm font-medium text-highlighted">{{ item.staff_name }}</span>
            <UBadge v-if="item.active" :label="t('support.access.live')" color="success" variant="subtle" size="xs" class="shrink-0" />
          </span>
          <span class="truncate text-xs text-muted">{{ t(`support.access.mode.${item.mode}`) }}<template v-if="item.ended_reason"> · {{ t(`support.access.endedReason.${item.ended_reason}`) }}</template></span>
        </span>
        <UTooltip :text="[dateTime(item.started_at), item.ended_at ? dateTime(item.ended_at) : ''].filter(Boolean).join(' · ')">
          <span class="shrink-0 text-end text-xs whitespace-nowrap text-muted">{{ moment(item.started_at) }}<template v-if="item.ended_at"><br class="sm:hidden"><span class="hidden sm:inline"> · </span>{{ t('support.access.endedAt', { when: moment(item.ended_at) }) }}</template></span>
        </UTooltip>
      </li>
    </ul>
  </div>
</template>
