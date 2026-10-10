<!--
  One role (F22): name and description, what it may do (the permission grid), and who holds it (they
  open on People). Changes are a draft until Save (Ctrl / ⌘ + S); leaving with unsaved changes asks
  first. Owner is shown read-only (everything, can't be changed). ⋯ duplicate, delete (own roles nobody
  holds).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { RoleRow } from '#shared/types/people'
import type { Grants } from '#shared/utils/auth/permissions'
import { withNeeds } from '#shared/utils/auth/permissions'

definePageMeta({ breadcrumb: 'nav.peopleRoles' })
const { t } = useI18n()
const route = useRoute()
const api = useApi()
const toast = useToast()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const { relative, number } = useFormat()
const { can } = useCan()
const breadcrumbs = useBreadcrumbs()
const id = String(route.params.id)

const role = ref<RoleRow | null>(null)
const failed = ref(false)
const draft = ref<{ name: string; description: string; grants: Grants } | null>(null)
const draftOf = (row: RoleRow) => ({ name: row.name, description: row.description ?? '', grants: withNeeds(row.grants) })
/** The same grants in a fixed order, to see whether anything changed. */
const keyOf = (grants: Grants) => JSON.stringify(withNeeds(grants))
async function load() {
  failed.value = false
  try {
    role.value = (await api.get<RoleRow>(`/roles/${id}`)).data
    draft.value = draftOf(role.value)
    breadcrumbs.setLabel(route.path, role.value.name)
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
onMounted(load)
useHead({ title: () => role.value?.name ?? t('nav.peopleRoles') })

const locked = computed(() => role.value?.id === 'owner' || !can('roles.manage'))
const dirty = computed(() => !!draft.value && !!role.value && (draft.value.name !== role.value.name || draft.value.description !== (role.value.description ?? '') || keyOf(draft.value.grants) !== keyOf(role.value.grants)))
const saving = ref(false)
async function save() {
  if (!draft.value || !dirty.value || saving.value || locked.value) return
  if (!draft.value.name.trim()) return toast.add({ title: t('access.nameRequired'), color: 'warning', icon: 'i-lucide-triangle-alert' })
  saving.value = true
  try {
    role.value = (await api.patch<RoleRow>(`/roles/${id}`, { name: draft.value.name.trim(), description: draft.value.description.trim() || null, grants: draft.value.grants })).data
    draft.value = draftOf(role.value)
    toast.add({ title: t('access.saved', { name: role.value.name }), description: role.value.people_count ? t('access.savedPeople', { n: role.value.people_count }, role.value.people_count) : undefined, color: 'success', icon: 'i-lucide-circle-check' })
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
const discard = () => role.value && (draft.value = draftOf(role.value))
defineShortcuts({ meta_s: { usingInput: true, handler: () => void save() } })
onBeforeRouteLeave(async () => (!dirty.value ? true : await confirm({ title: t('settings.leave.title'), description: t('settings.leave.desc'), confirmLabel: t('settings.leave.confirm'), danger: true })))

const more = computed<DropdownMenuItem[][]>(() =>
  can('roles.manage') && role.value
    ? [
        [{ label: t('access.duplicate'), icon: 'i-lucide-copy', onSelect: duplicate }],
        ...(!role.value.built_in ? [[{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, disabled: role.value.people_count > 0, onSelect: remove }]] : []),
      ]
    : [],
)
async function duplicate() {
  try {
    const { data } = await api.post<RoleRow>(`/roles/${id}/duplicate`)
    toast.add({ title: t('access.duplicated', { name: role.value?.name ?? '' }), color: 'success', icon: 'i-lucide-copy' })
    await navigateTo(`/people/roles/${data.id}`)
  } catch (error) {
    handle(error)
  }
}
async function remove() {
  if (!role.value || !(await confirm({ title: t('access.deleteTitle', { name: role.value.name }), description: t('access.deleteDesc'), confirmLabel: t('apiService.delete.confirm'), danger: true }))) return
  try {
    await api.del(`/roles/${id}`)
    toast.add({ title: t('access.deleted', { name: role.value.name }), color: 'success', icon: 'i-lucide-trash-2' })
    await navigateTo('/people/roles')
  } catch (error) {
    handle(error)
  }
}
</script>

<template>
  <AppPanel id="role" :title="role?.name ?? t('nav.peopleRoles')" :subtitle="role ? t('access.updated', { when: relative(role.updated_at) }) : undefined">
    <template #actions>
      <template v-if="!locked">
        <UButton :label="t('settings.discard')" color="neutral" variant="outline" :disabled="!dirty || saving" class="hidden sm:inline-flex" @click="discard" />
        <UButton :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="saving" :disabled="!dirty" @click="save">
          <template #trailing><UKbd value="meta" size="sm" class="hidden sm:inline-flex" /><UKbd value="S" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
      </template>
      <UDropdownMenu v-if="more.length" :items="more" :content="{ align: 'end' }">
        <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" square :aria-label="t('dataView.actions')" />
      </UDropdownMenu>
    </template>

    <AppEmpty v-if="failed" icon="i-lucide-shield-x" :title="t('access.notFound')" :actions="[{ label: t('nav.peopleRoles'), icon: 'i-lucide-arrow-left', color: 'neutral', variant: 'outline', to: '/people/roles' }]" />
    <div v-else-if="!draft || !role" class="flex flex-col gap-4"><USkeleton class="h-16 rounded-lg" /><USkeleton v-for="n in 6" :key="n" class="h-14" /></div>
    <div v-else class="flex max-w-5xl flex-col gap-6">
      <UAlert v-if="role.id === 'owner'" icon="i-lucide-crown" color="neutral" variant="subtle" :title="t('access.ownerLocked')" :description="t('access.ownerLockedDesc')" />
      <div class="grid gap-4 sm:grid-cols-[minmax(0,18rem)_minmax(0,1fr)]">
        <UFormField :label="t('access.name')" required><UInput v-model="draft.name" maxlength="60" :disabled="locked" class="w-full" /></UFormField>
        <UFormField :label="t('optionSets.description')"><UInput v-model="draft.description" maxlength="300" :disabled="locked" class="w-full" /></UFormField>
      </div>
      <section class="flex flex-col gap-3">
        <div class="flex flex-col">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('access.what') }}</h2>
          <p class="text-xs text-muted">{{ t('access.whatHint') }}</p>
        </div>
        <PeopleRolesEditor v-model="draft.grants" :readonly="locked" />
      </section>
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('access.holders', { n: number(role.people_count) }, role.people_count) }}</h2>
          <UButton v-if="role.people_count" :label="t('access.seeAll')" color="neutral" variant="link" size="xs" trailing-icon="i-lucide-arrow-right" :to="{ path: '/people', query: { role: role.id } }" class="rtl:[&_svg]:rotate-180" />
        </div>
        <AppEmpty v-if="!role.people_count" size="xs" icon="i-lucide-users" :title="t('access.nobody')" :description="t('access.nobodyHint')" />
        <ul v-else class="flex flex-wrap gap-2">
          <li v-for="person in role.people" :key="person.id">
            <NuxtLink :to="{ path: '/people', query: { person: person.id } }" class="flex items-center gap-2 rounded-full border border-default py-1 ps-1 pe-3 text-sm text-highlighted hover:border-accented">
              <UAvatar :src="person.photo ?? undefined" :alt="person.name" size="2xs" />{{ person.name }}
            </NuxtLink>
          </li>
        </ul>
      </section>
    </div>
  </AppPanel>
</template>
