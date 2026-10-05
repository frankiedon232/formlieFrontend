<!--
  A saved query (locked card format, rule 21): "last run" pill, shared or personal and ⋯; the name
  and its connection; what it does, who saved it, runs and when it changed in two columns; a
  divider, then the statement's first lines; the engine and the 30-day runs.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { SavedQuery } from '#shared/types/query'

const props = defineProps<{ item: SavedQuery; actions: DropdownMenuItem[][] }>()
const { t } = useI18n()
const { relative, number } = useFormat()
const facts = computed(() => [
  { key: 'kind', label: t('query.saved.col.kind'), value: t(`query.kind.${props.item.kind}`) },
  { key: 'owner', label: t('query.saved.col.owner'), value: props.item.mine ? t('query.saved.you') : props.item.owner.name },
  { key: 'runs', label: t('query.saved.col.runs'), value: number(props.item.run_count) },
  { key: 'updated', label: t('query.saved.col.updated'), value: relative(props.item.updated_at) },
])
</script>

<template>
  <article class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon name="i-lucide-play" class="size-3.5 shrink-0 text-muted" />
        <span class="truncate">{{ item.last_run_at ? t('query.saved.lastRun', { when: relative(item.last_run_at) }) : t('query.saved.neverRun') }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <UBadge :label="item.shared ? t('query.saved.sharedShort') : t('query.saved.personal')" :icon="item.shared ? 'i-lucide-users' : 'i-lucide-lock'" color="neutral" variant="outline" size="sm" class="rounded-md" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <div class="mt-3 flex min-w-0 flex-col">
      <div class="flex min-w-0 items-center gap-1.5">
        <UIcon v-if="item.kind !== 'read'" name="i-lucide-flag" class="size-3.5 shrink-0 text-warning" :aria-label="t('query.saved.kindChange')" />
        <span class="truncate text-base font-semibold text-highlighted">{{ item.name }}</span>
      </div>
      <p class="truncate text-sm text-muted">{{ item.description || item.datasource.name }}</p>
    </div>

    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm text-default tabular-nums">{{ fact.value }}</dd>
      </div>
    </dl>

    <div class="mt-auto pt-4">
      <pre class="line-clamp-3 border-t border-default pt-3 font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-muted" dir="ltr">{{ item.sql }}</pre>
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <DatasourcesEngineLogo :engine="item.datasource.engine" size="sm" />
          <span class="truncate text-xs text-muted">{{ item.datasource.name }}</span>
        </div>
        <ChartsSparkline :values="item.daily.map(day => day.count)" :width="72" :height="20" />
      </div>
    </div>
  </article>
</template>
