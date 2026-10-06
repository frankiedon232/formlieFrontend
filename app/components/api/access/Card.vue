<!--
  An access rule (locked card format, rule 21): a "last decided" pill, Allow / Block and ⋯ on top;
  what it matches as the title (kind and first values) and where it applies; kind, values, calls and
  state in two columns; a divider, then its note; who made it and its 30-day hits at the bottom.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiAccessRule } from '#shared/types/apiService'

const props = defineProps<{ item: ApiAccessRule; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { relative, number } = useFormat()
const format = useRuleFormat()
const facts = computed(() => [
  { key: 'kind', label: t('apiService.access.col.kind'), value: format.kindLabel(props.item.kind) },
  { key: 'values', label: t('apiService.access.col.values'), value: t('apiService.access.valuesCount', { n: props.item.values.length }, props.item.values.length) },
  { key: 'hits', label: t('apiService.access.col.hits'), value: number(props.item.hits_30d) },
  { key: 'state', label: t('apiService.access.col.state'), value: props.item.enabled ? t('apiService.access.on') : t('apiService.access.off') },
])
</script>

<template>
  <article class="group relative flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md" :class="[busy ? 'pointer-events-none opacity-60' : '', item.enabled ? '' : 'opacity-75']" :aria-busy="busy || undefined">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon :name="busy ? 'i-lucide-loader-circle' : 'i-lucide-clock'" class="size-3.5 shrink-0 text-muted" :class="busy ? 'animate-spin' : ''" />
        <span class="truncate">{{ item.last_hit_at ? t('apiService.access.lastHit', { when: relative(item.last_hit_at) }) : t('apiService.access.neverHit') }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <UBadge :label="t(`apiService.access.action.${item.action}`)" :icon="item.action === 'block' ? 'i-lucide-ban' : 'i-lucide-check'" :color="item.action === 'block' ? 'error' : 'success'" variant="subtle" size="sm" class="rounded-md" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <div class="mt-3 flex min-w-0 flex-col">
      <span class="flex min-w-0 items-center gap-1.5">
        <UIcon :name="format.kindIcon(item.kind)" class="size-4 shrink-0 text-muted" />
        <span class="truncate text-base font-semibold text-highlighted" :class="item.kind === 'ip' || item.kind === 'domain' ? 'font-mono text-sm' : ''" dir="ltr">{{ format.valuesText(item) }}</span>
      </span>
      <p class="truncate text-sm text-muted">{{ format.scopeText(item.scope) }}</p>
    </div>

    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm text-default tabular-nums">{{ fact.value }}</dd>
      </div>
    </dl>

    <div class="mt-auto pt-4">
      <p class="line-clamp-2 min-h-8 border-t border-default pt-3 text-xs text-muted">{{ item.note || t('apiService.access.noNote') }}</p>
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="item.created_by.name" size="2xs" />
          <span class="truncate text-xs text-muted">{{ item.created_by.name }}</span>
        </div>
        <ChartsSparkline :values="item.daily.map(day => day.count)" :width="72" :height="20" />
      </div>
    </div>
  </article>
</template>
