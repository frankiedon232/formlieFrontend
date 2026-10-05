<!--
  The side card of the Responses pages (F11): review status as a slim stacked bar (each status
  filters the list), the busiest forms (inbox), where responses came from (link · embedded · API)
  and in which languages. `only` shows one of them as its own card (the all-forms Insights grid,
  owner 2026-10-05: balanced rows instead of one long side column).
-->
<script setup lang="ts">
import { RESPONSE_STATUSES, type ResponseInsights, type ResponseStatus } from '#shared/types/responses'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

const props = defineProps<{ insights: ResponseInsights; status?: string | null; only?: 'status' | 'busiest' | 'channels' | 'languages' }>()
const shows = (part: 'status' | 'busiest' | 'channels' | 'languages') => !props.only || props.only === part
const emit = defineEmits<{ status: [status: ResponseStatus] }>()
const { t } = useI18n()

const parts = computed(() =>
  RESPONSE_STATUSES.map(key => ({ key, label: t(`status.${key}`), count: props.insights.status[key], color: RESPONSE_STATUS_META[key].fill })),
)
const channelTotal = computed(() => props.insights.channels.link + props.insights.channels.embed + props.insights.channels.api)
const channels = computed(() =>
  ([
    { key: 'link', icon: 'i-lucide-link' },
    { key: 'embed', icon: 'i-lucide-code-xml' },
    { key: 'api', icon: 'i-lucide-plug' },
  ] as const)
    .map(item => ({ ...item, label: t(`responses.channel.${item.key}`), count: props.insights.channels[item.key] }))
    .filter(item => item.count || item.key !== 'api'),
)
const topTotal = computed(() => props.insights.top_forms.reduce((sum, item) => sum + item.count, 0))
const languageTotal = computed(() => props.insights.languages.reduce((sum, item) => sum + item.count, 0))
const languageName = (code: string) => APP_LOCALES.find(item => item.code === code)?.name ?? code
const flag = (code: string) => APP_LOCALES.find(item => item.code === code)?.flag
</script>

<template>
  <UCard variant="outline" :ui="{ root: only ? 'h-full' : '', body: 'flex flex-col gap-5 p-4 sm:p-5' }">
    <section v-if="shows('status')" class="flex flex-col gap-3">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('responses.breakdown.status') }}</h2>
      <ChartsStack :parts="parts" :selected="status" clickable @pick="key => emit('status', key as ResponseStatus)" />
    </section>
    <template v-if="shows('busiest') && insights.top_forms.length">
      <USeparator v-if="!only" />
      <section class="flex flex-col gap-3">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('responses.breakdown.busiest') }}</h2>
        <NuxtLink
          v-for="(item, index) in insights.top_forms"
          :key="item.id"
          :to="`/forms/${item.id}/responses`"
          class="-mx-1.5 rounded-md px-1.5 py-1 hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        >
          <ChartsMeter :label="item.name" :count="item.count" :total="topTotal" :strong="index === 0" />
        </NuxtLink>
      </section>
    </template>
    <USeparator v-if="!only" />
    <section v-if="shows('channels')" class="flex flex-col gap-3">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('responses.breakdown.channels') }}</h2>
      <ChartsMeter v-for="(item, index) in channels" :key="item.key" :label="item.label" :icon="item.icon" :count="item.count" :total="channelTotal" :strong="index === 0" />
    </section>
    <template v-if="shows('languages') && (only === 'languages' ? insights.languages.length : insights.languages.length > 1)">
      <USeparator v-if="!only" />
      <section class="flex flex-col gap-3">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('responses.breakdown.languages') }}</h2>
        <ChartsMeter
          v-for="(item, index) in insights.languages"
          :key="item.code"
          :label="languageName(item.code)"
          :icon="flag(item.code)"
          :count="item.count"
          :total="languageTotal"
          :strong="index === 0"
        />
      </section>
    </template>
  </UCard>
</template>
