<!--
  An assistant request (locked card format, rule 21): "when" pill, status and ⋯; the title and what it
  was about; kind, who asked, credits and when it was applied in two columns; a divider, then the
  share of the month's allowance it used; avatar, the kind's icon and credits at the bottom.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { AiRequestRow } from '#shared/types/ai'
import { AI_KIND_META } from '#shared/utils/ai/kinds'

const props = defineProps<{ item: AiRequestRow; actions: DropdownMenuItem[][]; limit: number }>()
const { t } = useI18n()
const { relative, number } = useFormat()
const facts = computed(() => [
  { key: 'kind', label: t('ai.history.col.kind'), value: t(`ai.kind.${props.item.kind}`) },
  { key: 'by', label: t('ai.history.col.by'), value: props.item.mine ? t('ai.history.you') : props.item.by.name },
  { key: 'credits', label: t('ai.history.col.credits'), value: number(props.item.credits) },
  { key: 'applied', label: t('ai.history.col.applied'), value: props.item.applied_at ? relative(props.item.applied_at) : '–' },
])
const share = computed(() => (props.limit ? Math.min(100, Math.round((props.item.credits / props.limit) * 1000) / 10) : 0))
</script>

<template>
  <article class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon name="i-lucide-clock" class="size-3.5 shrink-0 text-muted" />
        <span class="truncate">{{ relative(item.created_at) }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <DataStatusBadge :status="item.status" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <div class="mt-3 flex min-w-0 flex-col">
      <div class="flex min-w-0 items-center gap-1.5">
        <UIcon v-if="item.status === 'failed'" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('status.failed')" />
        <span class="truncate text-base font-semibold text-highlighted">{{ item.title }}</span>
      </div>
      <p class="truncate text-sm text-muted">{{ item.target?.name || t(`ai.kindHint.${item.kind}`) }}</p>
    </div>

    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm text-default tabular-nums">{{ fact.value }}</dd>
      </div>
    </dl>

    <div class="mt-auto pt-4">
      <div class="flex flex-col gap-1.5 border-t border-default pt-3">
        <div class="flex items-center justify-between text-xs">
          <span class="text-muted">{{ t('ai.history.ofAllowance') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ share }}%</span>
        </div>
        <UProgress :model-value="share" size="xs" color="neutral" />
      </div>
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="item.by.name" size="2xs" />
          <span class="truncate text-xs text-muted">{{ item.by.name }}</span>
        </div>
        <span class="flex items-center gap-1 text-xs text-muted">
          <UIcon :name="AI_KIND_META[item.kind].icon" class="size-3.5" />
          {{ number(item.credits) }}
        </span>
      </div>
    </div>
  </article>
</template>
