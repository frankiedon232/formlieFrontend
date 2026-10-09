<!--
  People (F16 Users & profiles, M1; locked list format, rule 21): everyone in the workspace, profiled with
  departments, job titles and a role. Two chart cards (people and sign-ins; by status, legend filters),
  then table / cards with search, filters (status, role, department, job title) and sort. A row or card
  opens the person (`?person=`). Admins and owners only until F22.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { Directory } from '#shared/types/directory'
import type { PeopleInsights, PersonRow } from '#shared/types/people'
import { PERSON_STATUSES, WORKSPACE_ROLES } from '#shared/types/people'

definePageMeta({ breadcrumb: 'nav.people' })
const { t } = useI18n()
useHead({ title: () => t('nav.people') })
const api = useApi()
const route = useRoute()
const router = useRouter()
const { relative, dateTime, date } = useFormat()

const list = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: Ref<PersonRow[]> } }>('list')
const insights = ref<PeopleInsights | null>(null)
const directory = ref<Directory | null>(null)
async function loadInsights() {
  try {
    insights.value = (await api.get<PeopleInsights>('/people/insights', undefined, { background: !!insights.value })).data
  } catch {
    insights.value ??= null
  }
}
onMounted(async () => {
  void loadInsights()
  try {
    directory.value = (await api.get<Directory>('/directory', undefined, { background: true })).data
  } catch {
    directory.value = null
  }
})
const refreshAll = () => Promise.all([list.value?.refresh(), loadInsights()])
const actions = usePeopleActions(refreshAll)

// Invite people (I, or ?invite=1)
const inviteOpen = ref(!!route.query.invite)
defineShortcuts({ i: { usingInput: false, handler: () => (inviteOpen.value = true) } })

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('people.col.name'), sortable: true, fixed: true },
  { key: 'role', label: t('people.col.role'), sortable: true },
  { key: 'departments', label: t('people.col.department'), hideBelow: 'md' },
  { key: 'job_titles', label: t('people.col.jobTitle'), hideBelow: 'lg' },
  { key: 'status', label: t('people.col.status') },
  { key: 'two_step', label: t('people.col.twoStepShort'), hideBelow: 'lg' },
  { key: 'last_active_at', label: t('people.col.lastActive'), sortable: true, hideBelow: 'sm' },
  { key: 'joined_at', label: t('people.col.joined'), sortable: true, hidden: true },
])
const STATUS_DOT: Record<string, string> = { active: 'bg-green-500', invited: 'bg-amber-500', disabled: 'bg-(--ui-border-accented)' }
const filters = computed<DataFilter[]>(() => [
  { key: 'status', label: t('people.col.status'), icon: 'i-lucide-circle-dot', options: PERSON_STATUSES.map(value => ({ value, label: t(`people.status.${value}`), dot: STATUS_DOT[value] })) },
  { key: 'role', label: t('people.col.role'), icon: 'i-lucide-shield', options: WORKSPACE_ROLES.map(value => ({ value, label: t(`people.role.${value}`) })) },
  ...(directory.value?.departments.length ? [{ key: 'department', label: t('people.col.department'), icon: 'i-lucide-building-2', options: directory.value.departments.filter(item => !item.archived).map(item => ({ value: item.id, label: item.name })) }] : []),
  ...(directory.value?.job_titles.length ? [{ key: 'job_title', label: t('people.col.jobTitle'), icon: 'i-lucide-briefcase', options: directory.value.job_titles.filter(item => !item.archived).map(item => ({ value: item.id, label: item.name })) }] : []),
])
const sortOptions = computed(() => [
  { label: t('forms.sortName'), value: 'name' },
  { label: t('people.sort.active'), value: '-last_active_at' },
  { label: t('people.sort.joined'), value: '-joined_at' },
  { label: t('people.sort.role'), value: 'role' },
])
const fetcher: DataFetcher<PersonRow> = (params, signal) => api.list<PersonRow>('/people', params, { signal })
const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
const pickStatus = (status: string) => void router.replace({ query: { ...route.query, status: statusFilter.value === status ? undefined : status, page: undefined } })

// The panel (`?person=`)
const openId = computed(() => (typeof route.query.person === 'string' ? route.query.person : null))
const panelOpen = computed({ get: () => !!openId.value, set: value => !value && router.replace({ query: { ...route.query, person: undefined } }) })
const ids = computed(() => (list.value?.state.rows.value ?? []).map(row => row.id))
const openRow = (row: PersonRow) => void router.replace({ query: { ...route.query, person: row.id } })
const go = (id: string) => void router.replace({ query: { ...route.query, person: id } })

const rowActions = (row: PersonRow): DropdownMenuItem[][] => [
  [
    { label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
    { label: t('people.email'), icon: 'i-lucide-mail', to: `mailto:${row.email}`, external: true },
    ...(row.status === 'invited' ? [] : [{ label: t('people.activity'), icon: 'i-lucide-scroll-text', to: { path: '/audit', query: { actor_id: row.id } } }]),
  ],
  ...(row.status === 'invited'
    ? [
        [
          { label: t('people.invite.resend'), icon: 'i-lucide-send', onSelect: () => void actions.resend(row) },
          { label: t('people.invite.copyLink'), icon: 'i-lucide-link', onSelect: () => void actions.copyLink(row) },
        ],
        [{ label: t('people.invite.revoke'), icon: 'i-lucide-user-minus', color: 'error' as const, onSelect: () => void actions.revoke(row) }],
      ]
    : []),
]
const names = (items: { name: string }[]) => items.map(item => item.name).join(', ')
</script>

<template>
  <AppPanel id="people" :title="t('nav.people')" :subtitle="t('people.subtitle')">
    <template #actions>
      <UButton :label="t('people.invite.button')" icon="i-lucide-user-plus" color="neutral" @click="inviteOpen = true">
        <template #trailing><UKbd value="I" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
    </template>
    <PeopleOverview :insights="insights" :selected="statusFilter" @pick="pickStatus" />

    <DataView
      id="people"
      ref="list"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="name"
      default-view="table"
      :row-actions="rowActions"
      :busy="row => actions.busy.value === row.id"
      :open-row="openRow"
      :search-placeholder="t('people.search')"
      empty-icon="i-lucide-users"
      :empty-title="t('people.empty')"
      :empty-description="t('people.emptyDesc')"
    >
      <template #name-cell="{ row }"><PeopleWho :person="row.original" @open="openRow(row.original)" /></template>
      <template #role-cell="{ row }"><span class="text-default">{{ t(`people.role.${row.original.role}`) }}</span></template>
      <template #departments-cell="{ row }"><span class="block max-w-48 truncate text-muted">{{ names(row.original.departments) || '–' }}</span></template>
      <template #job_titles-cell="{ row }"><span class="block max-w-48 truncate text-muted">{{ names(row.original.job_titles) || '–' }}</span></template>
      <template #status-cell="{ row }"><PeopleStatus :person="row.original" /></template>
      <template #two_step-cell="{ row }">
        <span class="flex items-center gap-1.5 text-muted"><UIcon :name="row.original.two_step ? 'i-lucide-shield-check' : 'i-lucide-shield-off'" class="size-4" :class="row.original.two_step ? 'text-highlighted' : ''" />{{ row.original.two_step ? t('people.twoStepOn') : t('people.twoStepOff') }}</span>
      </template>
      <template #last_active_at-cell="{ row }">
        <UTooltip v-if="row.original.invite" :text="t('people.invite.by', { name: row.original.invite.invited_by })"><span class="whitespace-nowrap text-muted">{{ t('people.invite.sentAgo', { when: relative(row.original.invite.sent_at) }) }}</span></UTooltip>
        <UTooltip v-else-if="row.original.last_active_at" :text="dateTime(row.original.last_active_at)"><span class="whitespace-nowrap text-muted">{{ relative(row.original.last_active_at) }}</span></UTooltip>
        <span v-else class="text-muted">{{ t('people.never') }}</span>
      </template>
      <template #joined_at-cell="{ row }"><span class="whitespace-nowrap text-muted">{{ date(row.original.joined_at) }}</span></template>
      <template #empty-actions><UButton :label="t('people.invite.button')" icon="i-lucide-user-plus" color="neutral" @click="inviteOpen = true" /></template>
      <template #grid-card="{ row }"><PeopleCard :person="row" :actions="rowActions(row)" :busy="actions.busy.value === row.id" /></template>
    </DataView>

    <PeopleDetail :id="openId" ref="panel" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" :busy="!!actions.busy.value" @go="go" @resend="actions.resend" @copy-link="actions.copyLink" @revoke="person => actions.revoke(person).then(() => (panelOpen = false))" />
    <PeopleInviteModal v-model:open="inviteOpen" :directory="directory" @invited="refreshAll" />
  </AppPanel>
</template>
