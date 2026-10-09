<!--
  Edit a person (F16 M3): role (Owner only offered to owners), departments, job titles and manager
  (searchable; not themselves or someone who reports to them, the server checks loops). Their own
  profile details (name, phone, photo) are theirs to change in My profile.
-->
<script setup lang="ts">
import type { WorkspaceRole } from '#shared/types/auth'
import type { Directory } from '#shared/types/directory'
import type { PersonRow } from '#shared/types/people'

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ person: PersonRow | null; directory: Directory | null }>()
const emit = defineEmits<{ saved: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const session = useSession()
const { handle } = useErrorHandler()

const state = reactive({ role: 'member' as WorkspaceRole, department_ids: [] as string[], job_title_ids: [] as string[], manager_id: null as string | null })
const people = ref<PersonRow[]>([])
watch(open, async value => {
  if (!value || !props.person) return
  Object.assign(state, { role: props.person.role, department_ids: props.person.departments.map(item => item.id), job_title_ids: props.person.job_titles.map(item => item.id), manager_id: props.person.manager?.id ?? null })
  try {
    people.value = (await api.list<PersonRow>('/people', { page_size: 100, 'filter[status]': 'active', sort: 'name' }, { background: true })).data
  } catch {
    people.value = []
  }
})

const iAmOwner = computed(() => session.user.value?.role === 'owner')
// The workspace's roles (Roles & access); Owner only for owners
const { roles: workspaceRoles, refresh: loadRoles } = useRoles()
onMounted(() => void loadRoles())
const roles = computed(() =>
  workspaceRoles.value
    .filter(role => role.id !== 'owner' || iAmOwner.value || props.person?.role === 'owner')
    .map(role => ({ value: role.id, label: role.name, description: role.description ?? undefined, disabled: role.id === 'owner' && !iAmOwner.value })),
)
const departments = computed(() => (props.directory?.departments ?? []).filter(item => !item.archived).map(item => ({ value: item.id, label: item.name })))
const jobTitles = computed(() => (props.directory?.job_titles ?? []).filter(item => !item.archived).map(item => ({ value: item.id, label: item.name })))
const NONE = 'none'
const managers = computed(() => [{ value: NONE, label: t('people.none') }, ...people.value.filter(item => item.id !== props.person?.id).map(item => ({ value: item.id, label: item.name, description: item.email }))])

const saving = ref(false)
async function save() {
  if (!props.person || saving.value) return
  saving.value = true
  try {
    await api.patch(`/people/${props.person.id}`, { ...state, ...(props.person.status === 'invited' ? { manager_id: undefined } : {}) })
    toast.add({ title: t('people.manage.saved', { name: props.person.name }), color: 'success', icon: 'i-lucide-circle-check' })
    open.value = false
    emit('saved')
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="t('people.manage.editTitle', { name: person?.name ?? '' })" :description="t('people.manage.editDesc')" :ui="{ content: 'sm:max-w-xl' }">
    <template #body>
      <form class="flex flex-col gap-4" @submit.prevent="save">
        <UFormField :label="t('people.col.role')">
          <USelectMenu v-model="state.role" :items="roles" value-key="value" icon="i-lucide-shield" class="w-full" />
          <template #hint><NuxtLink to="/people/roles" class="underline">{{ t('access.manageRoles') }}</NuxtLink></template>
        </UFormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <UFormField :label="t('people.col.departments')">
            <USelectMenu v-model="state.department_ids" :items="departments" value-key="value" multiple :placeholder="t('people.invite.pick')" icon="i-lucide-building-2" class="w-full" />
          </UFormField>
          <UFormField :label="t('people.col.jobTitles')">
            <USelectMenu v-model="state.job_title_ids" :items="jobTitles" value-key="value" multiple :placeholder="t('people.invite.pick')" icon="i-lucide-briefcase" class="w-full" />
          </UFormField>
        </div>
        <UFormField v-if="person?.status !== 'invited'" :label="t('people.col.manager')" :description="t('people.manage.managerHint')">
          <USelectMenu :model-value="state.manager_id ?? NONE" :items="managers" value-key="value" icon="i-lucide-user-round" class="w-full" @update:model-value="(value: unknown) => (state.manager_id = value === NONE ? null : String(value))" />
        </UFormField>
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="saving" @click="save" />
      </div>
    </template>
  </AppModal>
</template>
