<!--
  Where calls go and come from (F13 M4): the busiest endpoints, the busiest tokens (callers), the
  countries calls come from and the methods used, each as slim bars with counts and shares.
-->
<script setup lang="ts">
import type { ApiAnalytics } from '#shared/types/apiService'
import { API_METHODS } from '#shared/utils/urls/public'

const props = defineProps<{ analytics: ApiAnalytics | null }>()
const { t } = useI18n()
const { current } = useAppLocale()
const Link = resolveComponent('NuxtLink')
const total = computed(() => props.analytics?.totals.calls ?? 0)
const names = computed(() => new Intl.DisplayNames([current.value.language], { type: 'region' }))
const cards = computed(() => {
  const a = props.analytics
  if (!a) return []
  return [
    { key: 'endpoints', title: t('apiService.analytics.topEndpoints'), rows: a.endpoints.slice(0, 6).map(item => ({ key: item.id, label: `/${item.name}`, count: item.calls, icon: 'i-lucide-route', mono: true, to: { path: '/api-service/endpoints', query: { endpoint: item.id } } })) },
    { key: 'tokens', title: t('apiService.analytics.topCallers'), rows: a.tokens.slice(0, 6).map(item => ({ key: item.id, label: item.name, count: item.calls, icon: item.mode === 'test' ? 'i-lucide-flask-conical' : 'i-lucide-key-round', mono: false, to: { path: '/api-service/auth', query: { token: item.id } } })) },
    { key: 'countries', title: t('apiService.analytics.countries'), rows: a.countries.slice(0, 6).map(item => ({ key: item.code, label: names.value.of(item.code) ?? item.code, count: item.calls, icon: `i-circle-flags-${item.code.toLowerCase()}`, mono: false, to: undefined })) },
    { key: 'methods', title: t('apiService.col.methods'), rows: API_METHODS.map(method => ({ key: method, label: method, count: a.methods[method], icon: 'i-lucide-arrow-left-right', mono: true, to: undefined })).filter(item => item.count) },
  ]
})
</script>

<template>
  <div class="grid shrink-0 gap-4 md:grid-cols-2 xl:grid-cols-4">
    <template v-if="!analytics"><USkeleton v-for="n in 4" :key="n" class="h-64 rounded-lg" /></template>
    <UCard v-for="card in cards" v-else :key="card.key" variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
      <h2 class="text-sm font-semibold text-highlighted">{{ card.title }}</h2>
      <p v-if="!card.rows.length" class="text-sm text-muted">{{ t('apiService.noCalls') }}</p>
      <component :is="row.to ? Link : 'div'" v-for="(row, i) in card.rows" :key="row.key" :to="row.to" class="rounded-md focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" :class="row.to ? 'hover:bg-elevated/50' : ''">
        <ChartsMeter :label="row.label" :count="row.count" :total="total" :strong="i === 0" :icon="row.icon" :class="row.mono ? '[&_span.truncate]:font-mono' : ''" />
      </component>
    </UCard>
  </div>
</template>
