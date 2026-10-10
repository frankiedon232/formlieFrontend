<!--
  Dashboard → Forms view (F21 M2): running the forms (Analytics analyses them). KPI cards (published, new forms,
  responses per active form, published without responses, unpublished changes); responses by form beside the
  forms by status (thin lines, a status opens the filtered list) and where responses come from; new forms over
  time, folders and owners; and the forms that need work, each with the step that fixes it.
-->
<script setup lang="ts">
import type { DashboardGroup, FormsDashboard } from '#shared/types/dashboard'

const props = defineProps<{ from: string; to: string; group?: DashboardGroup; folder?: string; owner?: string }>()
const emit = defineEmits<{ loaded: [group: DashboardGroup] }>()
const { t, d } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { number, date } = useFormat()

const data = ref<FormsDashboard | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    data.value = (await api.get<FormsDashboard>('/dashboard/forms', { from: props.from, to: props.to, group: props.group, folder: props.folder, owner: props.owner })).data
    emit('loaded', data.value.group)
  } catch (error) {
    failed.value = true
    handle(error)
  }
}
watch(() => [props.from, props.to, props.group, props.folder, props.owner], load, { immediate: true })
defineExpose({ refresh: load })

const change = (kpi: { value: number; previous: number | null } | undefined) => (kpi && kpi.previous ? Math.round(((kpi.value - kpi.previous) / kpi.previous) * 100) : null)
const kpis = computed(() => {
  const k = data.value?.kpis
  return [
    { key: 'published', icon: 'i-lucide-globe', label: t('dashboard.formsView.published'), value: k ? number(k.published.value) : null, change: null, to: '/forms?status=published', hint: t('dashboard.formsView.publishedHint') },
    { key: 'created', icon: 'i-lucide-file-plus-2', label: t('dashboard.formsView.created'), value: k ? number(k.created.value) : null, change: change(k?.created), to: '/forms?sort=-created_at' },
    { key: 'perForm', icon: 'i-lucide-inbox', label: t('dashboard.formsView.perForm'), value: k ? number(k.per_form.value) : null, change: change(k?.per_form), to: '/analytics' },
    { key: 'silent', icon: 'i-lucide-bell-off', label: t('dashboard.formsView.silent'), value: k ? number(k.silent.value) : null, change: null, to: '#forms-work', hint: t('dashboard.formsView.silentHint'), lower: true },
    { key: 'unpublished', icon: 'i-lucide-pencil-line', label: t('dashboard.formsView.unpublished'), value: k ? number(k.unpublished.value) : null, change: null, to: '#forms-work', hint: t('dashboard.formsView.unpublishedHint'), lower: true },
  ]
})

const DOTS = { draft: 'bg-amber-500', published: 'bg-green-500', closed: 'bg-violet-600', archived: 'bg-(--ui-text-dimmed)' } as const
const statusParts = computed(() => (Object.keys(DOTS) as (keyof typeof DOTS)[]).map(key => ({ key, label: t(`status.${key}`), count: data.value?.by_status[key] ?? 0, color: DOTS[key] })))
const pickStatus = (key: string) => navigateTo({ path: '/forms', query: { status: key } })
const topTotal = computed(() => data.value?.top.reduce((sum, item) => sum + item.responses, 0) ?? 0)
const channelTotal = computed(() => (data.value ? data.value.channels.link + data.value.channels.embed + data.value.channels.api : 0))
const CHANNEL_ICON = { link: 'i-lucide-link', embed: 'i-lucide-code', api: 'i-lucide-code-xml' } as const
const formChange = (item: FormsDashboard['top'][number]) => (item.previous ? Math.round(((item.responses - item.previous) / item.previous) * 100) : null)

const bucketLabel = (start: string) => {
  const day = new Date(`${start}T00:00:00Z`)
  const group = data.value?.group ?? 'day'
  return group === 'year' ? String(day.getUTCFullYear()) : group === 'month' ? d(day, { month: 'short', year: '2-digit', timeZone: 'UTC' }) : d(day, { day: 'numeric', month: 'short', timeZone: 'UTC' })
}
const createdPoints = computed(() => data.value?.created.map(item => ({ label: bucketLabel(item.start), value: item.count })) ?? [])
const anyCreated = computed(() => createdPoints.value.some(point => point.value))
const folderTotal = computed(() => data.value?.folders.reduce((sum, item) => sum + item.responses, 0) ?? 0)
const ownerTotal = computed(() => data.value?.owners.reduce((sum, item) => sum + item.responses, 0) ?? 0)

const WORK = {
  nearly_full: { icon: 'i-lucide-gauge', color: 'text-warning', to: (id: string) => `/forms/${id}/share` },
  closing: { icon: 'i-lucide-calendar-clock', color: 'text-warning', to: (id: string) => `/forms/${id}/share` },
  no_responses: { icon: 'i-lucide-bell-off', color: 'text-muted', to: (id: string) => `/forms/${id}/share` },
  unpublished_changes: { icon: 'i-lucide-pencil-line', color: 'text-muted', to: (id: string) => `/forms/${id}/build` },
  stale_draft: { icon: 'i-lucide-file-clock', color: 'text-muted', to: (id: string) => `/forms/${id}/build` },
} as const
</script>

<template>
  <AppEmpty v-if="failed && !data" icon="i-lucide-cloud-off" :title="t('dashboard.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
  <DashboardStart v-else-if="data?.new_workspace" />
  <div v-else class="flex flex-col gap-4" :class="data && failed ? 'opacity-60' : ''">
    <div class="flex shrink-0 snap-x gap-3 overflow-x-auto [scrollbar-width:none] sm:grid sm:grid-cols-3 sm:overflow-visible xl:grid-cols-5">
      <ChartsKpi v-for="kpi in kpis" :key="kpi.key" class="min-w-[13.5rem] snap-start sm:min-w-0" :label="kpi.label" :icon="kpi.icon" :value="kpi.value" :change="kpi.change" :hint="kpi.hint" :to="kpi.to" :lower-is-better="!!kpi.lower" />
    </div>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <UCard variant="outline" class="min-w-0 lg:col-span-2" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
        <div class="flex items-center gap-2">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.formsView.byForm') }}</h2>
          <UButton icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" square class="ms-auto" to="/analytics" :aria-label="t('nav.analytics')" />
        </div>
        <div v-if="!data" class="flex flex-col gap-3"><USkeleton v-for="n in 5" :key="n" class="h-8 w-full" /></div>
        <AppEmpty v-else-if="!data.top.length" size="sm" icon="i-lucide-inbox" :title="t('dashboard.activity.none')" :description="t('dashboard.activity.noneDesc')" />
        <ul v-else class="flex flex-col gap-3">
          <li v-for="(item, i) in data.top" :key="item.id" class="flex items-end gap-3">
            <NuxtLink :to="`/forms/${item.id}`" class="min-w-0 flex-1 rounded-sm focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
              <ChartsMeter :label="item.name" :count="item.responses" :total="topTotal" :strong="i === 0" />
            </NuxtLink>
            <UBadge v-if="formChange(item) !== null" :label="`${formChange(item)! >= 0 ? '+' : ''}${formChange(item)}%`" :color="formChange(item)! >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="mb-0.5 w-14 justify-center tabular-nums" />
            <span v-else class="w-14" />
          </li>
        </ul>
      </UCard>

      <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
        <div class="flex flex-col gap-3">
          <div class="flex items-center justify-between gap-2">
            <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.formsView.byStatus') }}</h2>
            <span v-if="data" class="text-xs text-muted">{{ t('dashboard.formsView.live', { n: number(data.by_status.published) }) }}</span>
          </div>
          <USkeleton v-if="!data" class="h-20 w-full" />
          <template v-else>
            <ChartsLines :parts="statusParts" @pick="pickStatus" />
            <ul class="grid grid-cols-2 gap-x-4 gap-y-1">
              <li v-for="part in statusParts" :key="part.key">
                <NuxtLink :to="{ path: '/forms', query: { status: part.key } }" class="flex items-center gap-2 text-xs hover:text-highlighted">
                  <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" /><span class="flex-1 text-muted">{{ part.label }}</span><span class="text-highlighted tabular-nums">{{ number(part.count) }}</span>
                </NuxtLink>
              </li>
            </ul>
          </template>
        </div>
        <div class="flex flex-col gap-3 border-t border-default pt-4">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.formsView.channels') }}</h2>
          <USkeleton v-if="!data" class="h-24 w-full" />
          <p v-else-if="!channelTotal" class="text-xs text-muted">{{ t('dashboard.activity.none') }}</p>
          <template v-else>
            <ChartsMeter v-for="key in (['link', 'embed', 'api'] as const)" :key="key" :label="t(`dashboard.formsView.channel.${key}`)" :icon="CHANNEL_ICON[key]" :count="data.channels[key]" :total="channelTotal" />
          </template>
        </div>
      </UCard>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.formsView.newForms') }}</h2>
          <span v-if="data" class="text-xs text-muted tabular-nums">{{ number(data.kpis.created.value) }}</span>
        </div>
        <USkeleton v-if="!data" class="h-32 w-full" />
        <p v-else-if="!anyCreated" class="text-xs text-muted">{{ t('dashboard.formsView.noneCreated') }}</p>
        <ChartsBars v-else :points="createdPoints" :unit="n => t('dashboard.formsView.formsCount', { n: number(n) }, n)" height="h-32" />
      </UCard>
      <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.formsView.folders') }}</h2>
        <div v-if="!data" class="flex flex-col gap-3"><USkeleton v-for="n in 4" :key="n" class="h-7 w-full" /></div>
        <template v-else>
          <NuxtLink v-for="(item, i) in data.folders" :key="item.id ?? 'none'" :to="item.id ? `/folders/${item.id}` : '/forms'" class="rounded-sm focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
            <ChartsMeter :label="`${item.name ?? t('dashboard.formsView.noFolder')} · ${t('dashboard.formsView.formsCount', { n: number(item.forms) }, item.forms)}`" :count="item.responses" :total="folderTotal" :strong="i === 0" icon="i-lucide-folder" />
          </NuxtLink>
        </template>
      </UCard>
      <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.formsView.owners') }}</h2>
        <div v-if="!data" class="flex flex-col gap-3"><USkeleton v-for="n in 4" :key="n" class="h-7 w-full" /></div>
        <template v-else>
          <ChartsMeter v-for="(item, i) in data.owners" :key="item.id" :label="`${item.name} · ${t('dashboard.formsView.formsCount', { n: number(item.forms) }, item.forms)}`" :count="item.responses" :total="ownerTotal" :strong="i === 0" icon="i-lucide-user-round" />
        </template>
      </UCard>
    </div>

    <UCard id="forms-work" variant="outline" class="min-w-0" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
      <div class="flex items-center gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.formsView.work') }}</h2>
        <UBadge v-if="data?.work.length" :label="String(data.work.length)" color="neutral" variant="outline" size="sm" />
      </div>
      <div v-if="!data" class="flex flex-col gap-2"><USkeleton v-for="n in 3" :key="n" class="h-9 w-full" /></div>
      <p v-else-if="!data.work.length" class="flex items-center gap-2 text-sm text-muted"><UIcon name="i-lucide-circle-check" class="size-4 text-success" />{{ t('dashboard.formsView.allGood') }}</p>
      <ul v-else class="grid grid-cols-1 gap-x-6 divide-y divide-default md:grid-cols-2 md:divide-y-0">
        <li v-for="(item, i) in data.work" :key="`${item.kind}-${item.form.id}-${i}`" class="flex items-center gap-3 py-2 md:border-b md:border-default">
          <UIcon :name="WORK[item.kind].icon" class="size-4 shrink-0" :class="WORK[item.kind].color" />
          <span class="flex min-w-0 flex-1 flex-col">
            <NuxtLink :to="`/forms/${item.form.id}`" class="truncate text-sm text-highlighted hover:underline">{{ item.form.name }}</NuxtLink>
            <span class="truncate text-xs text-muted">{{ t(`dashboard.formsView.workKind.${item.kind}`, { date: item.at ? date(item.at) : '', n: number(item.count ?? 0) }) }}</span>
          </span>
          <UButton :label="t(`dashboard.formsView.workAction.${item.kind}`)" color="neutral" variant="outline" size="xs" :to="WORK[item.kind].to(item.form.id)" />
        </li>
      </ul>
    </UCard>
  </div>
</template>
