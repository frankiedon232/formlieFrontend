<!--
  A token (locked card format, rule 21): a "used" pill, status and ⋯ on top; the name (red flag when
  it expires soon or hasn't been used for 90 days) and its visible part; kind, mode, expiry and calls
  in two columns; a divider, then what it may call; who made it and its 30-day calls at the bottom.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiToken } from '#shared/types/apiService'

const props = defineProps<{ item: ApiToken; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { number } = useFormat()
const format = useTokenFormat()
const facts = computed(() => [
  { key: 'kind', label: t('apiService.tokens.col.kind'), value: format.kindLabel(props.item) },
  { key: 'mode', label: t('apiService.tokens.col.mode'), value: t(`apiService.tokens.mode.${props.item.mode}`) },
  { key: 'expires', label: t('apiService.tokens.col.expires'), value: format.expiresText(props.item) },
  { key: 'calls', label: t('apiService.col.calls'), value: number(props.item.calls_30d) },
])
</script>

<template>
  <article class="group relative flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md" :class="[busy ? 'pointer-events-none opacity-60' : '', item.status === 'revoked' ? 'opacity-75' : '']" :aria-busy="busy || undefined">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon :name="busy ? 'i-lucide-loader-circle' : 'i-lucide-clock'" class="size-3.5 shrink-0 text-muted" :class="busy ? 'animate-spin' : ''" />
        <span class="truncate">{{ format.usedText(item) }}</span>
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
        <UIcon v-if="format.flagged(item)" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('apiService.tokens.needsLook')" />
        <span class="truncate text-base font-semibold text-highlighted">{{ item.name }}</span>
      </div>
      <p class="truncate font-mono text-xs text-muted" dir="ltr">{{ item.preview }}</p>
    </div>

    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm text-default tabular-nums">{{ fact.value }}</dd>
      </div>
    </dl>

    <div class="mt-auto pt-4">
      <div class="flex min-w-0 flex-col gap-1 border-t border-default pt-3">
        <span class="text-xs text-muted">{{ t('apiService.tokens.col.scope') }}</span>
        <span class="truncate text-sm text-highlighted">{{ format.scopeText(item) }}</span>
      </div>
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
