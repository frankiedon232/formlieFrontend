<!--
  Dashboard (F21, design reference 2: docs/design/Screenshot 2026-10-02 092034.png): the workspace home. Header:
  the period (last 30 days by default, kept in the address) and Daily / Weekly / Monthly / Yearly, with New form.
  Below, a view switch: Workspace (every area at a glance, M1) · Forms (running the forms, M2) · Data sources (M3) ·
  API service (M4), each shown to people whose role reaches it; the choice is remembered. Workspace and Forms take
  a folder / owner filter (M5, kept in the address). Everything follows the person's role and folder access.
-->
<script setup lang="ts">
import { DASHBOARD_GROUPS, type DashboardGroup, type DashboardView } from '#shared/types/dashboard'

definePageMeta({ breadcrumb: 'nav.dashboard' })
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { can } = useCan()
useHead({ title: () => t('nav.dashboard') })

// The period and grouping (kept in the address so a link shows the same)
const iso = (time: number) => new Date(time).toISOString().slice(0, 10)
const from = computed(() => (typeof route.query.from === 'string' && route.query.from ? route.query.from : iso(Date.now() - 29 * 86_400_000)))
const to = computed(() => (typeof route.query.to === 'string' && route.query.to ? route.query.to : iso(Date.now())))
const group = computed<DashboardGroup | undefined>(() => (DASHBOARD_GROUPS.includes(route.query.group as DashboardGroup) ? (route.query.group as DashboardGroup) : undefined))
const setPeriod = (start: string, end: string) => void router.replace({ query: { ...route.query, from: start || undefined, to: end || undefined } })
const groups = computed(() => DASHBOARD_GROUPS.map(value => ({ value, label: t(`dashboard.group.${value}`) })))
/** The group the server chose when none was asked for. */
const shownGroup = ref<DashboardGroup>('day')
const chosenGroup = computed({
  get: () => group.value ?? shownGroup.value,
  set: value => void router.replace({ query: { ...route.query, group: value } }),
})
const loaded = (value: DashboardGroup) => {
  shownGroup.value = value
  syncedAt.value = Date.now()
}
const syncedAt = ref<number | null>(null)

// The forms filter (Workspace and Forms views)
const text = (value: unknown) => (typeof value === 'string' && value ? value : undefined)
const folder = computed(() => text(route.query.folder))
const owner = computed(() => text(route.query.owner))
const setFilter = (value: { folder?: string; owner?: string }) => void router.replace({ query: { ...route.query, folder: value.folder, owner: value.owner } })

// Views: Workspace for everyone, the others for people whose role reaches the area
const VIEW_KEY = 'formalie:dashboard-view'
const views = computed(() => [{ value: 'workspace' as const, label: t('dashboard.views.workspace'), icon: 'i-lucide-layout-dashboard' }, ...(can('forms.view') ? [{ value: 'forms' as const, label: t('dashboard.views.forms'), icon: 'i-lucide-file-text' }] : []), ...(can('data.view') ? [{ value: 'data' as const, label: t('dashboard.views.data'), icon: 'i-lucide-database' }] : []), ...(can('api.view') ? [{ value: 'api' as const, label: t('dashboard.views.api'), icon: 'i-lucide-code-xml' }] : [])])
const stored = (() => {
  try {
    return localStorage.getItem(VIEW_KEY) as DashboardView | null
  } catch {
    return null
  }
})()
const view = computed<DashboardView>({
  get: () => {
    const wanted = (typeof route.query.view === 'string' ? route.query.view : stored) as DashboardView | null
    return views.value.some(item => item.value === wanted) ? wanted! : 'workspace'
  },
  set: value => {
    try {
      localStorage.setItem(VIEW_KEY, value)
    } catch {
      // Remembering is a convenience
    }
    void router.replace({ query: { ...route.query, view: value === 'workspace' ? undefined : value } })
  },
})
const current = useTemplateRef<{ refresh: () => Promise<unknown> }>('current')
</script>

<template>
  <AppPanel id="dashboard" :title="t('nav.dashboard')" :subtitle="syncedAt ? t('dashboard.synced') : t('dashboard.subtitle')" subtitle-icon="i-lucide-refresh-cw">
    <template #actions>
      <UButton icon="i-lucide-refresh-cw" color="neutral" variant="ghost" square :aria-label="t('dashboard.refresh')" class="max-xl:hidden" @click="current?.refresh()" />
      <!-- The picker has no single root for a tour marker: it sits on this wrapper -->
      <div class="inline-flex" data-help="dashboard-period"><DataDateRangePicker :from="from" :to="to" @change="setPeriod" /></div>
      <UTabs v-model="chosenGroup" :items="groups" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" class="max-2xl:hidden" :aria-label="t('dashboard.groupLabel')" />
      <UButton v-if="can('forms.create')" :label="t('dashboard.newForm')" icon="i-lucide-plus" color="neutral" to="/forms/new" />
    </template>

    <div class="flex flex-col gap-4">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <UTabs v-if="views.length > 1" v-model="view" :items="views" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" :aria-label="t('dashboard.views.label')" data-help="dashboard-views" />
        <DashboardFilter v-if="view === 'workspace' || view === 'forms'" :folder="folder" :owner="owner" data-help="dashboard-filter" @change="setFilter" />
        <UTabs v-model="chosenGroup" :items="groups" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" class="ms-auto 2xl:hidden" :aria-label="t('dashboard.groupLabel')" />
      </div>
      <DashboardApi v-if="view === 'api'" ref="current" :from="from" :to="to" :group="group" @loaded="loaded" />
      <DashboardData v-else-if="view === 'data'" ref="current" :from="from" :to="to" :group="group" @loaded="loaded" />
      <DashboardForms v-else-if="view === 'forms'" ref="current" :from="from" :to="to" :group="group" :folder="folder" :owner="owner" @loaded="loaded" />
      <DashboardWorkspace v-else ref="current" :from="from" :to="to" :group="group" :folder="folder" :owner="owner" @loaded="loaded" />
    </div>
  </AppPanel>
</template>
