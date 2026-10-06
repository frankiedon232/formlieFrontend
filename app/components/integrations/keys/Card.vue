<!--
  An API key (locked card format, rule 21): a "last used" pill, status and ⋯ on top; its name (red
  flag when it expires soon) and preview; scopes, calls, expiry and created in two columns; a
  divider, then its scopes as badges; who made it and 30 days of calls.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ManagementKey } from '#shared/types/integrations'

const props = defineProps<{ item: ManagementKey; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { relative, number, date } = useFormat()
const facts = computed(() => [
  { key: 'scopes', label: t('integrations.keys.col.scopes'), value: t('integrations.keys.scopesCount', { n: props.item.scopes.length }, props.item.scopes.length) },
  { key: 'calls', label: t('integrations.keys.col.calls'), value: number(props.item.calls_30d) },
  { key: 'expires', label: t('apiService.tokens.col.expires'), value: props.item.expires_at ? date(props.item.expires_at) : t('apiService.tokens.never') },
  { key: 'created', label: t('apiService.col.created'), value: relative(props.item.created_at) },
])
</script>

<template>
  <article class="group relative flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md" :class="[busy ? 'pointer-events-none opacity-60' : '', item.status === 'revoked' || item.status === 'expired' ? 'opacity-75' : '']" :aria-busy="busy || undefined">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon :name="busy ? 'i-lucide-loader-circle' : 'i-lucide-clock'" class="size-3.5 shrink-0 text-muted" :class="busy ? 'animate-spin' : ''" />
        <span class="truncate">{{ item.last_used_at ? t('integrations.keys.lastUsed', { when: relative(item.last_used_at) }) : t('integrations.keys.neverUsed') }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <DataStatusBadge :status="item.status" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <div class="mt-3 flex min-w-0 flex-col">
      <span class="flex min-w-0 items-center gap-1.5">
        <UIcon v-if="item.status === 'expiring'" name="i-lucide-flag" class="size-4 shrink-0 text-error" />
        <span class="truncate text-base font-semibold text-highlighted">{{ item.name }}</span>
      </span>
      <p class="truncate font-mono text-xs text-muted" dir="ltr">{{ item.preview }}</p>
    </div>

    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm text-default tabular-nums">{{ fact.value }}</dd>
      </div>
    </dl>

    <div class="mt-auto pt-4">
      <div class="flex h-6 gap-1 overflow-hidden border-t border-default pt-3">
        <code v-for="scope in item.scopes" :key="scope" class="shrink-0 rounded bg-elevated px-1.5 font-mono text-[11px] text-highlighted">{{ scope }}</code>
      </div>
      <div class="mt-5 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="item.created_by.name" size="2xs" />
          <span class="truncate text-xs text-muted">{{ item.created_by.name }}</span>
        </div>
        <ChartsSparkline :values="item.daily.map(day => day.count)" :width="72" :height="20" />
      </div>
    </div>
  </article>
</template>
