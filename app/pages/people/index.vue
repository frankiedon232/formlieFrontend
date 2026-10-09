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
import { PERSON_STATUSES } from '#shared/types/people'

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
const { roles, refresh: loadRoles } = useRoles()
onMounted(() => void loadRoles())
// The menu counts (Awaiting approval, Not activated…) follow every change
const counts = useNavCounts()
const refreshAll = () => Promise.all([list.value?.refresh(), loadInsights(), counts.refresh(true)])
const actions = usePeopleActions(refreshAll)

// Invite people (I, or ?invite=1)
const inviteOpen = ref(!!route.query.invite)
// `?invite=1` from the menu or the header opens it here too; the address is tidied after
watch(() => route.query.invite, value => value && (inviteOpen.value = true))
watch(() => route.query.add, value => value && ((addOpen.value = true), router.replace({ query: { ...route.query, add: undefined } })), { immediate: true })
watch(inviteOpen, value => !value && route.query.invite && router.replace({ query: { ...route.query, invite: undefined } }))
// Add a user profile (N); sign-up links (shared and personal); approve someone who signed up with a link
const addOpen = ref(false)
const linksOpen = ref(false)
const approving = ref<PersonRow | null>(null)
const approveOpen = ref(false)
const approve = (person: PersonRow) => ((approving.value = person), (approveOpen.value = true))
const canManage = computed(() => useCan().can('people.manage'))
defineShortcuts({ n: { usingInput: false, handler: () => canManage.value && (addOpen.value = true) }, i: { usingInput: false, handler: () => canManage.value && (inviteOpen.value = true) } })

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
const STATUS_DOT: Record<string, string> = { active: 'bg-green-500', not_activated: 'bg-sky-500', invited: 'bg-amber-500', pending: 'bg-violet-500', disabled: 'bg-(--ui-border-accented)' }
const filters = computed<DataFilter[]>(() => [
  { key: 'status', label: t('people.col.status'), icon: 'i-lucide-circle-dot', options: PERSON_STATUSES.map(value => ({ value, label: t(`people.status.${value}`), dot: STATUS_DOT[value] })) },
  { key: 'role', label: t('people.col.role'), icon: 'i-lucide-shield', options: roles.value.map(role => ({ value: role.id, label: role.name })) },
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

// Edit (role, departments, job titles, manager)
const editOpen = ref(false)
const editing = ref<PersonRow | null>(null)
const edit = (person: PersonRow) => ((editing.value = person), (editOpen.value = true))
const panel = useTemplateRef<{ reload: () => void }>('panel')
const saved = () => Promise.all([refreshAll(), panel.value?.reload()])

const rowActions = (row: PersonRow): DropdownMenuItem[][] => [
  [
    { label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
    { label: t('people.email'), icon: 'i-lucide-mail', to: `mailto:${row.email}`, external: true },
    ...(['invited', 'not_activated', 'pending'].includes(row.status) ? [] : [{ label: t('people.activity'), icon: 'i-lucide-scroll-text', to: { path: '/audit', query: { actor_id: row.id } } }]),
  ],
  ...actions.menu(row, edit, approve),
]
// Several at once: role, add to a department or job title, disable / enable
const pickItems = (list: { id: string; name: string; archived?: boolean }[] | undefined, pick: (id: string) => void): DropdownMenuItem[] => (list ?? []).filter(item => !item.archived).map(item => ({ label: item.name, onSelect: () => pick(item.id) }))
const names = (items: { name: string }[]) => items.map(item => item.name).join(', ')
</script>

<template>
  <AppPanel id="people" :title="t('nav.people')" :subtitle="t('people.subtitle')">
    <template #actions>
      <UButton v-if="canManage" :label="t('people.links.button')" icon="i-lucide-link" color="neutral" variant="outline" @click="linksOpen = true" />
      <UButton v-if="canManage" :label="t('people.add.button')" icon="i-lucide-user-plus" color="neutral" @click="addOpen = true">
        <template #trailing><UKbd value="N" size="sm" class="hidden sm:inline-flex" /></template>
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
      selectable
      :row-actions="rowActions"
      :busy="row => actions.busy.value === row.id"
      :open-row="openRow"
      :search-placeholder="t('people.search')"
      empty-icon="i-lucide-users"
      :empty-title="t('people.empty')"
      :empty-description="t('people.emptyDesc')"
    >
      <template #name-cell="{ row }"><PeopleWho :person="row.original" @open="openRow(row.original)" /></template>
      <template #role-cell="{ row }"><span class="text-default">{{ row.original.role_name }}</span></template>
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
      <template v-if="canManage" #empty-actions><UButton :label="t('people.add.button')" icon="i-lucide-user-plus" color="neutral" @click="addOpen = true" /><UButton :label="t('people.links.button')" icon="i-lucide-link" color="neutral" variant="outline" @click="linksOpen = true" /></template>
      <template #bulk-actions="{ selected, clear }">
        <UDropdownMenu :items="actions.roleItems(role => void actions.bulk(selected.map(row => row.id), 'role', role).then(clear))">
          <UButton :label="t('people.bulk.role')" icon="i-lucide-shield" trailing-icon="i-lucide-chevron-down" color="neutral" variant="outline" size="sm" :loading="actions.busy.value === 'bulk'" />
        </UDropdownMenu>
        <UDropdownMenu v-if="directory?.departments.length" :items="pickItems(directory?.departments, id => void actions.bulk(selected.map(row => row.id), 'department', id).then(clear))">
          <UButton :label="t('people.bulk.department')" icon="i-lucide-building-2" trailing-icon="i-lucide-chevron-down" color="neutral" variant="outline" size="sm" />
        </UDropdownMenu>
        <UDropdownMenu v-if="directory?.job_titles.length" :items="pickItems(directory?.job_titles, id => void actions.bulk(selected.map(row => row.id), 'job_title', id).then(clear))">
          <UButton :label="t('people.bulk.jobTitle')" icon="i-lucide-briefcase" trailing-icon="i-lucide-chevron-down" color="neutral" variant="outline" size="sm" />
        </UDropdownMenu>
        <UButton :label="t('people.manage.enable')" icon="i-lucide-user-check" color="neutral" variant="outline" size="sm" @click="actions.bulk(selected.map(row => row.id), 'enable').then(clear)" />
        <UButton :label="t('people.manage.disable')" icon="i-lucide-user-x" color="error" variant="outline" size="sm" @click="actions.bulk(selected.map(row => row.id), 'disable').then(clear)" />
      </template>
      <template #grid-card="{ row }"><PeopleCard :person="row" :actions="rowActions(row)" :busy="actions.busy.value === row.id" /></template>
    </DataView>

    <PeopleDetail :id="openId" ref="panel" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" :busy="!!actions.busy.value" :menu="person => actions.menu(person, edit, approve)" @go="go" @resend="actions.resend" @copy-link="actions.copyLink" @revoke="person => actions.revoke(person).then(() => (panelOpen = false))" @edit="edit" @approve="approve" @reject="person => actions.reject(person).then(() => (panelOpen = false))" />
    <PeopleEditModal v-model:open="editOpen" :person="editing" :directory="directory" @saved="saved" />
    <PeopleInviteModal v-model:open="inviteOpen" :directory="directory" @invited="refreshAll" />
    <PeopleAddModal v-model:open="addOpen" :directory="directory" @saved="refreshAll" />
    <PeopleAddModal v-model:open="approveOpen" :directory="directory" :approve="approving" @saved="saved" />
    <PeopleSignupLinks v-model:open="linksOpen" @personal="() => ((linksOpen = false), (inviteOpen = true))" />
  </AppPanel>
</template>
