<!--
  Roles & access (F22, brought forward into F16; locked list format, rule 21): the workspace's roles and
  what each opens. Two cards (people per role; built-in and own roles, the legend filters), then table /
  cards. A role opens its editor; New role (N) starts from scratch or a copy; ⋯ duplicate, delete (own
  roles nobody holds). Owner is built in and can't be changed.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { RoleRow, RolesInsights } from '#shared/types/people'
import { reachOf } from '#shared/utils/auth/permissions'

definePageMeta({ breadcrumb: 'nav.peopleRoles' })
const { t } = useI18n()
const { roleName, roleDescription } = useBuiltInNames()
useHead({ title: () => t('nav.peopleRoles') })
const api = useApi()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const { relative, number, percent } = useFormat()
const { can } = useCan()
const manage = computed(() => can('roles.manage'))

const view = useTemplateRef<{ refresh: () => Promise<void> }>('view')
const insights = ref<RolesInsights | null>(null)
async function loadInsights() {
  try {
    insights.value = (await api.get<RolesInsights>('/roles/insights', undefined, { background: !!insights.value })).data
  } catch {
    insights.value ??= null
  }
}
onMounted(loadInsights)
const refreshAll = () => Promise.all([view.value?.refresh(), loadInsights()])

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('access.col.role'), sortable: true, fixed: true },
  { key: 'people_count', label: t('access.col.people'), sortable: true },
  { key: 'permissions', label: t('access.col.reach'), hideBelow: 'sm' },
  { key: 'built_in', label: t('access.col.kind'), hideBelow: 'md' },
  { key: 'updated_at', label: t('access.col.updated'), sortable: true, hideBelow: 'lg' },
])
const sortOptions = computed(() => [
  { label: t('forms.sortName'), value: 'name' },
  { label: t('access.sort.people'), value: '-people_count' },
  { label: t('access.sort.updated'), value: '-updated_at' },
])
const filters = computed<DataFilter[]>(() => [{ key: 'kind', label: t('access.col.kind'), icon: 'i-lucide-shield', options: [{ value: 'builtin', label: t('access.builtIn'), dot: 'bg-(--ui-text-dimmed)' }, { value: 'own', label: t('access.own'), dot: 'bg-violet-500' }] }])
const fetcher: DataFetcher<RoleRow> = (params, signal) => api.list<RoleRow>('/roles', params, { signal })
const kind = computed(() => (typeof route.query.kind === 'string' && !route.query.kind.includes(',') ? route.query.kind : null))
const pickKind = (key: string) => void router.replace({ query: { ...route.query, kind: kind.value === key ? undefined : key, page: undefined } })
/** How much of the platform a role opens (share of all permissions). */
const reach = (row: RoleRow) => (row.id === 'owner' ? 1 : reachOf(row.grants))

const open = (row: RoleRow) => navigateTo(`/people/roles/${row.id}`)
const newOpen = ref(false)
defineShortcuts({ n: { usingInput: false, handler: () => manage.value && (newOpen.value = true) } })

const busy = ref<string | null>(null)
async function act(row: RoleRow, work: () => Promise<unknown>, message: string) {
  if (busy.value) return
  busy.value = row.id
  try {
    await work()
    toast.add({ title: message, color: 'success', icon: 'i-lucide-circle-check' })
    await refreshAll()
  } catch (error) {
    handle(error)
  } finally {
    busy.value = null
  }
}
async function remove(row: RoleRow) {
  if (await confirm({ title: t('access.deleteTitle', { name: row.name }), description: t('access.deleteDesc'), confirmLabel: t('apiService.delete.confirm'), danger: true }))
    await act(row, () => api.del(`/roles/${row.id}`), t('access.deleted', { name: row.name }))
}
const rowActions = (row: RoleRow): DropdownMenuItem[][] => [
  [{ label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => void open(row) }],
  ...(manage.value
    ? [
        [{ label: t('access.duplicate'), icon: 'i-lucide-copy', onSelect: () => void act(row, () => api.post(`/roles/${row.id}/duplicate`), t('access.duplicated', { name: row.name })) }],
        ...(!row.built_in ? [[{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, disabled: row.people_count > 0, onSelect: () => void remove(row) }]] : []),
      ]
    : []),
]
</script>

<template>
  <AppPanel id="roles" :title="t('nav.peopleRoles')" :subtitle="t('access.subtitle')">
    <template #actions>
      <UButton v-if="manage" :label="t('access.new')" icon="i-lucide-plus" color="neutral" @click="newOpen = true">
        <template #trailing><UKbd value="N" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
    </template>

    <PeopleRolesOverview :insights="insights" :selected="kind" @pick="pickKind" />

    <DataView
      id="roles"
      ref="view"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="name"
      default-view="table"
      :row-actions="rowActions"
      :busy="row => busy === row.id"
      :open-row="open"
      :search-placeholder="t('access.search')"
      empty-icon="i-lucide-shield"
      :empty-title="t('access.empty')"
    >
      <template #name-cell="{ row }">
        <div class="flex min-w-0 flex-col">
          <span class="flex items-center gap-1.5 font-medium text-highlighted"><UIcon :name="row.original.id === 'owner' ? 'i-lucide-crown' : 'i-lucide-shield'" class="size-3.5 shrink-0 text-muted" />{{ roleName(row.original.id, row.original.name) }}</span>
          <span v-if="row.original.description" class="max-w-80 truncate text-xs text-muted">{{ roleDescription(row.original.id, row.original.description) }}</span>
        </div>
      </template>
      <template #people_count-cell="{ row }">
        <div class="flex items-center gap-2">
          <UAvatarGroup v-if="row.original.people.length" size="2xs" :max="3"><UAvatar v-for="person in row.original.people" :key="person.id" :src="person.photo ?? undefined" :alt="person.name" /></UAvatarGroup>
          <span class="text-muted tabular-nums">{{ t('access.peopleCount', { n: number(row.original.people_count) }, row.original.people_count) }}</span>
        </div>
      </template>
      <template #permissions-cell="{ row }">
        <div class="flex w-36 items-center gap-2"><UProgress :model-value="reach(row.original) * 100" color="neutral" size="xs" class="flex-1" /><span class="w-9 text-end text-xs text-muted tabular-nums">{{ percent(reach(row.original)) }}</span></div>
      </template>
      <template #built_in-cell="{ row }"><UBadge :label="row.original.built_in ? t('access.builtIn') : t('access.own')" color="neutral" :variant="row.original.built_in ? 'soft' : 'outline'" size="sm" /></template>
      <template #updated_at-cell="{ row }"><span class="whitespace-nowrap text-muted">{{ relative(row.original.updated_at) }}</span></template>
      <template #grid-card="{ row }"><PeopleRolesCard :role="row" :reach="reach(row)" :actions="rowActions(row)" :busy="busy === row.id" /></template>
    </DataView>

    <PeopleRolesNewModal v-model:open="newOpen" @created="role => navigateTo(`/people/roles/${role.id}`)" />
  </AppPanel>
</template>
