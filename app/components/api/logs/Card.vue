<!--
  A logged call (locked card format, rule 21): a "when" pill, status and ⋯ on top; the method and
  address as the title (red flag for our own failures) and its endpoint; token, caller, time taken and
  error code in two columns; a divider, then the request id; the caller's country at the bottom.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiLogEntry } from '#shared/types/apiService'

const props = defineProps<{ item: ApiLogEntry; actions: DropdownMenuItem[][] }>()
const { t } = useI18n()
const { relative } = useFormat()
const { current } = useAppLocale()
const facts = computed(() => [
  { key: 'token', label: t('apiService.logs.col.token'), value: props.item.token?.name ?? t('apiService.logs.noToken') },
  { key: 'caller', label: t('apiService.logs.col.caller'), value: props.item.ip },
  { key: 'time', label: t('apiService.logs.col.duration'), value: t('dataSources.ms', { n: props.item.duration_ms }) },
  { key: 'code', label: t('apiService.logs.col.code'), value: props.item.code ?? '–' },
])
const country = computed(() => (props.item.country ? (new Intl.DisplayNames([current.value.language], { type: 'region' }).of(props.item.country) ?? props.item.country) : t('apiService.logs.unknownCountry')))
</script>

<template>
  <article class="group relative flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon name="i-lucide-clock" class="size-3.5 shrink-0 text-muted" />
        <span class="truncate">{{ relative(item.at) }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <ApiLogsStatus :status="item.status" :code="item.code" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>
    <div class="mt-3 flex min-w-0 flex-col">
      <span class="flex min-w-0 items-center gap-1.5">
        <UIcon v-if="item.status >= 500" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('apiService.logs.class.5xx')" />
        <span class="truncate font-mono text-sm font-semibold text-highlighted" dir="ltr">{{ item.method }} {{ item.path }}</span>
      </span>
      <p class="truncate text-sm text-muted">{{ item.endpoint ? `/${item.endpoint.name}` : t('apiService.logs.noEndpoint') }}</p>
    </div>
    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm text-default tabular-nums" :class="fact.key === 'caller' || fact.key === 'code' ? 'font-mono text-xs' : ''" dir="ltr">{{ fact.value }}</dd>
      </div>
    </dl>
    <div class="mt-auto pt-4">
      <p class="truncate border-t border-default pt-3 font-mono text-[11px] text-muted" dir="ltr">{{ item.request_id }}</p>
      <div class="mt-4 flex items-center gap-2 text-xs text-muted">
        <UIcon :name="item.country ? `i-circle-flags-${item.country.toLowerCase()}` : 'i-lucide-globe'" class="size-4 shrink-0" />
        <span class="truncate">{{ country }}</span>
        <UBadge v-if="item.token" :label="t(`apiService.tokens.mode.${item.token.mode}`)" color="neutral" :variant="item.token.mode === 'test' ? 'soft' : 'outline'" size="xs" class="ms-auto rounded-md" />
      </div>
    </div>
  </article>
</template>
