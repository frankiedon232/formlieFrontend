<!--
  Dashboard → Needs attention (F21): what to look at now, most urgent first (a payment due, a failing connection or
  webhook, a form nearly full or closing, the plan's form limit, the card expiring, responses to review), each
  opening where it is fixed; below, each area at a glance (forms, data sources, API service, plan), only the areas
  the person's role reaches.
-->
<script setup lang="ts">
import type { AttentionItem, WorkspaceDashboard } from '#shared/types/dashboard'

const props = defineProps<{ data: WorkspaceDashboard | null }>()
const { t } = useI18n()
const { number, date } = useFormat()

const LOOK: Record<AttentionItem['kind'], { icon: string; color: string }> = {
  payment_due: { icon: 'i-lucide-credit-card', color: 'text-error' },
  connection_failing: { icon: 'i-lucide-database-zap', color: 'text-error' },
  webhook_failing: { icon: 'i-lucide-webhook', color: 'text-error' },
  form_full: { icon: 'i-lucide-gauge', color: 'text-warning' },
  plan_forms: { icon: 'i-lucide-gem', color: 'text-warning' },
  form_closing: { icon: 'i-lucide-calendar-clock', color: 'text-warning' },
  card_expiring: { icon: 'i-lucide-credit-card', color: 'text-warning' },
  connection_attention: { icon: 'i-lucide-database', color: 'text-warning' },
  to_review: { icon: 'i-lucide-inbox', color: 'text-highlighted' },
}
const text = (item: AttentionItem) => t(`dashboard.attention.${item.kind}`, { name: item.name ?? '', n: number(item.count ?? 0), date: item.at ? date(item.at) : '' }, item.count ?? 1)
const areas = computed(() => {
  const a = props.data?.areas
  if (!a) return []
  return [
    { key: 'forms', icon: 'i-lucide-file-text', to: '/forms', value: number(a.forms.total), hint: t('dashboard.areas.formsHint', { published: number(a.forms.published), drafts: number(a.forms.drafts) }) },
    ...(a.data ? [{ key: 'data', icon: 'i-lucide-database', to: '/data-sources', value: number(a.data.connections), hint: a.data.failing ? t('dashboard.areas.dataFailing', { n: a.data.failing }, a.data.failing) : t('dashboard.areas.dataOk', { n: a.data.connected }, a.data.connected) }] : []),
    ...(a.api ? [{ key: 'api', icon: 'i-lucide-code-xml', to: '/api-service', value: number(a.api.calls), hint: t('dashboard.areas.apiHint', { services: number(a.api.services), errors: number(a.api.errors) }) }] : []),
    ...(a.plan ? [{ key: 'plan', icon: 'i-lucide-gem', to: '/settings/subscription', value: t(`billing.plan.${a.plan.plan}.name`), hint: a.plan.forms_limit === null ? t('dashboard.areas.planUnlimited', { n: number(a.plan.forms) }) : t('dashboard.areas.planForms', { n: number(a.plan.forms), limit: number(a.plan.forms_limit) }) }] : []),
  ]
})
</script>

<template>
  <UCard id="attention" variant="outline" class="flex h-full min-w-0 flex-col" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex items-center gap-2">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.attention.title') }}</h2>
      <UBadge v-if="data?.kpis.attention.value" :label="String(data.kpis.attention.value)" color="warning" variant="subtle" size="sm" />
    </div>
    <div v-if="!data" class="flex flex-col gap-2"><USkeleton v-for="n in 3" :key="n" class="h-9 w-full" /></div>
    <p v-else-if="!data.attention.length" class="flex items-center gap-2 text-sm text-muted"><UIcon name="i-lucide-circle-check" class="size-4 text-success" />{{ t('dashboard.attention.none') }}</p>
    <ul v-else class="flex flex-col divide-y divide-default">
      <li v-for="(item, i) in data.attention" :key="`${item.kind}-${i}`">
        <NuxtLink :to="item.link" class="group flex items-center gap-3 py-2 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
          <UIcon :name="LOOK[item.kind].icon" class="size-4 shrink-0" :class="LOOK[item.kind].color" />
          <span class="min-w-0 flex-1 text-sm text-default group-hover:text-highlighted">{{ text(item) }}</span>
          <UIcon name="i-lucide-chevron-right" class="size-4 shrink-0 text-dimmed rtl:rotate-180" />
        </NuxtLink>
      </li>
    </ul>

    <div class="mt-auto grid grid-cols-2 gap-2 border-t border-default pt-4">
      <template v-if="!data"><USkeleton v-for="n in 4" :key="n" class="h-16" /></template>
      <NuxtLink v-for="area in areas" v-else :key="area.key" :to="area.to" class="flex min-w-0 flex-col gap-0.5 rounded-lg border border-default p-2.5 transition hover:border-accented focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
        <span class="flex items-center gap-1.5 text-xs text-muted"><UIcon :name="area.icon" class="size-3.5" />{{ t(`dashboard.areas.${area.key}`) }}</span>
        <span class="truncate text-base font-semibold text-highlighted tabular-nums">{{ area.value }}</span>
        <span class="truncate text-[11px] text-muted">{{ area.hint }}</span>
      </NuxtLink>
    </div>
  </UCard>
</template>
