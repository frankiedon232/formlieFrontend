<!--
  A connection on Data sources → Connections (locked card format, rule 21): a "checked" pill,
  status and ⋯ on top; the engine and name (red flag when it needs a look) with engine and version;
  address, database, access and response time in two columns; a divider, then Uptime (30 days)
  with a black bar; who added it, forms sending to it, missing permissions and the 30-day trend.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { DataSourceRow } from '#shared/types/datasources'

const props = defineProps<{ source: DataSourceRow; actions: DropdownMenuItem[][] }>()
const { t } = useI18n()
const { relative, number } = useFormat()
const flagged = computed(() => props.source.status === 'failing' || props.source.status === 'attention')
const facts = computed(() => [
  { key: 'address', label: t('dataSources.summary.address'), value: props.source.address, ltr: true },
  { key: 'database', label: t('dataSources.summary.database'), value: props.source.database, ltr: true },
  { key: 'access', label: t('dataSources.summary.access'), value: t(`dataSources.access.${props.source.access.mode}`) },
  { key: 'latency', label: t('dataSources.kpi.latency'), value: props.source.latency_ms === null ? '–' : t('dataSources.ms', { n: props.source.latency_ms }) },
])
</script>

<template>
  <article class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon name="i-lucide-activity" class="size-3.5 shrink-0 text-muted" />
        <span class="truncate">{{ source.last_checked_at ? t('dataSources.checked', { when: relative(source.last_checked_at) }) : t('dataSources.neverChecked') }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <DataStatusBadge :status="source.status" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <div class="mt-3 flex min-w-0 items-center gap-2.5">
      <DatasourcesEngineLogo :engine="source.engine" size="sm" />
      <div class="flex min-w-0 flex-col">
        <div class="flex min-w-0 items-center gap-1.5">
          <UIcon v-if="flagged" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('dataSources.needsLook')" />
          <NuxtLink :to="{ query: { connection: source.id } }" class="truncate text-base font-semibold text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">{{ source.name }}</NuxtLink>
        </div>
        <p class="truncate text-sm text-muted">{{ engineName(source.engine) }}{{ source.server_version ? ` ${source.server_version}` : '' }}</p>
      </div>
    </div>

    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm text-default" :class="fact.ltr ? 'text-start font-mono text-xs leading-5' : 'tabular-nums'" :dir="fact.ltr ? 'ltr' : undefined">{{ fact.value || '–' }}</dd>
      </div>
    </dl>

    <div class="mt-auto pt-4">
      <div class="border-t border-default pt-3">
        <div class="mb-1.5 flex items-center justify-between text-xs">
          <span class="text-muted">{{ t('dataSources.uptime') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ source.uptime_30d === null ? '–' : `${source.uptime_30d}%` }}</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-elevated" role="presentation">
          <div class="h-full rounded-full bg-inverted" :style="{ width: `${source.uptime_30d ?? 0}%` }" />
        </div>
      </div>

      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="source.created_by.name" size="xs" />
          <span class="flex items-center gap-1 text-xs text-muted tabular-nums" :title="t('dataSources.formsUsing')">
            <UIcon name="i-lucide-file-text" class="size-3.5" />{{ number(source.forms_count) }}
          </span>
          <span v-if="source.missing_permissions" class="flex items-center gap-1 text-xs text-warning tabular-nums" :title="t('dataSources.kpi.missing')">
            <UIcon name="i-lucide-key-round" class="size-3.5" />{{ number(source.missing_permissions) }}
          </span>
        </div>
        <ChartsSparkline :values="source.daily.map(day => day.count)" :width="72" :height="20" />
      </div>
    </div>
  </article>
</template>
