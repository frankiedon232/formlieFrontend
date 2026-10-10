<!--
  AI assistant overview (F19 M1, own rail area): this month's use of the allowance and requests by kind
  (two chart cards; the legend opens History filtered), what the assistant can do (cards that follow the
  role; parts still being built say so), the latest requests and the promise that people stay in control.
  Switched off: what that means and, for people who manage it, the way to switch it on.
-->
<script setup lang="ts">
import type { AiKind, AiRequestRow, AiUsage } from '#shared/types/ai'
import type { Permission } from '#shared/utils/auth/permissions'
import { AI_KIND_META } from '#shared/utils/ai/kinds'

definePageMeta({ breadcrumb: 'nav.ai' })
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { relative, number } = useFormat()
const { can } = useCan()
const ai = useAi()
const { titleOf } = useAiText()
useHead({ title: () => t('nav.ai') })

const usage = ref<AiUsage | null>(null)
const recent = ref<AiRequestRow[] | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    const [settings, u] = await Promise.all([ai.load(true), api.get<AiUsage>('/ai/usage')])
    usage.value = u.data
    if (settings && can('ai.history')) recent.value = (await api.list<AiRequestRow>('/ai/requests', { page_size: 5, sort: '-created_at' })).data
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
onMounted(load)
const byKindCount = computed(() => usage.value?.by_kind ?? null)
const openKind = (kind: AiKind) => void navigateTo({ path: '/ai/history', query: { kind } })

// What it can do; parts land milestone by milestone (PROGRESS.md → F19)
const sections: { key: string; nav: string; icon: string; to: string; permission: Permission; ready: boolean }[] = [
  { key: 'createForm', nav: 'aiCreateForm', icon: 'i-lucide-file-plus-2', to: '/ai/create-form', permission: 'ai.create', ready: true },
  { key: 'templates', nav: 'aiTemplates', icon: 'i-lucide-layout-template', to: '/ai/templates', permission: 'ai.create', ready: true },
  { key: 'analysis', nav: 'aiAnalysis', icon: 'i-lucide-chart-scatter', to: '/ai/analysis', permission: 'ai.analyse', ready: true },
  { key: 'insights', nav: 'aiInsights', icon: 'i-lucide-lightbulb', to: '/ai/insights', permission: 'ai.analyse', ready: true },
  { key: 'translate', nav: 'aiTranslate', icon: 'i-lucide-languages', to: '/ai/translate', permission: 'ai.translate', ready: true },
  { key: 'history', nav: 'aiHistory', icon: 'i-lucide-history', to: '/ai/history', permission: 'ai.history', ready: true },
  { key: 'settings', nav: 'aiSettings', icon: 'i-lucide-sliders-horizontal', to: '/ai/settings', permission: 'ai.use', ready: true },
]
const shown = computed(() => sections.filter(section => can(section.permission)))
const promises = ['review', 'private', 'audit'] as const
</script>

<template>
  <AppPanel id="ai" :title="t('nav.ai')" :subtitle="t('ai.subtitle')" subtitle-icon="i-lucide-sparkles">
    <template #actions>
      <UButton v-if="can('ai.history')" :label="t('nav.aiHistory')" icon="i-lucide-history" color="neutral" variant="outline" to="/ai/history" class="max-sm:hidden" />
      <UButton v-if="can('ai.settings')" :label="t('nav.aiSettings')" icon="i-lucide-sliders-horizontal" color="neutral" to="/ai/settings" />
    </template>

    <AppEmpty v-if="failed && !usage" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
    <AiOff v-else-if="!ai.enabled.value" />
    <template v-else>
      <AiOverviewCards :usage="usage" :by-kind="byKindCount" :kinds-title="t('ai.overview.byKind')" :kinds-note="t('ai.usage.thisMonth')" @kind="openKind" />

      <section class="flex flex-col gap-3">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('ai.overview.what') }}</h2>
        <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <UPageCard
            v-for="section in shown"
            :key="section.key"
            :to="section.to"
            :icon="section.icon"
            :title="t(`nav.${section.nav}`)"
            :description="t(`ai.section.${section.key}`)"
            variant="outline"
            class="h-full transition-all hover:-translate-y-0.5 hover:shadow-md"
            :ui="{ leadingIcon: 'size-5 text-default' }"
          >
            <template v-if="!section.ready" #footer>
              <UBadge :label="t('ai.overview.soon')" color="neutral" variant="soft" size="sm" class="rounded-md" />
            </template>
          </UPageCard>
        </div>
      </section>

      <div class="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <UCard v-if="can('ai.history')" variant="outline" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
          <div class="flex items-center justify-between gap-2">
            <h2 class="text-sm font-semibold text-highlighted">{{ t('ai.overview.latest') }}</h2>
            <UButton :label="t('ai.overview.all')" trailing-icon="i-lucide-arrow-right" color="neutral" variant="ghost" size="xs" to="/ai/history" />
          </div>
          <div v-if="!recent" class="flex flex-col gap-2"><USkeleton v-for="n in 4" :key="n" class="h-10 w-full rounded-md" /></div>
          <AppEmpty v-else-if="!recent.length" size="sm" icon="i-lucide-sparkles" :title="t('ai.history.emptyTitle')" :description="t('ai.history.emptyDesc')" />
          <ul v-else class="flex flex-col divide-y divide-default">
            <li v-for="item in recent" :key="item.id">
              <NuxtLink :to="{ path: '/ai/history', query: { q: item.title } }" class="flex items-center gap-3 rounded-md py-2.5 hover:bg-elevated/50 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
                <span class="flex size-8 shrink-0 items-center justify-center rounded-lg border border-default"><UIcon :name="AI_KIND_META[item.kind].icon" class="size-4 text-muted" /></span>
                <span class="flex min-w-0 flex-1 flex-col">
                  <span class="truncate text-sm font-medium text-highlighted">{{ titleOf(item) }}</span>
                  <span class="truncate text-xs text-muted">{{ item.mine ? t('ai.history.you') : item.by.name }} · {{ relative(item.created_at) }}</span>
                </span>
                <span class="hidden text-xs text-muted tabular-nums sm:inline">{{ t('ai.overview.credits', { n: number(item.credits) }, item.credits) }}</span>
                <DataStatusBadge :status="item.status" />
              </NuxtLink>
            </li>
          </ul>
        </UCard>

        <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('ai.promise.title') }}</h2>
          <ul class="flex flex-col gap-2.5">
            <li v-for="item in promises" :key="item" class="flex items-start gap-2 text-sm text-muted">
              <UIcon name="i-lucide-check" class="mt-0.5 size-4 shrink-0 text-default" />
              {{ t(`ai.promise.${item}`) }}
            </li>
          </ul>
        </UCard>
      </div>
    </template>
  </AppPanel>
</template>
