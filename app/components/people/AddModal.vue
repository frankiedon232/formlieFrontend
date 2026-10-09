<!--
  Add a user profile (F16 rework): the organisation profiles a staff member in full (name, email, phone,
  role, departments, job titles, manager). The profile starts as Not activated and the person gets an
  activation email to set their own password; then they sign in. Also used to approve someone who
  signed up with a link (`approve`): their details are shown, the admin completes the profile.
-->
<script setup lang="ts">
import type { Directory } from '#shared/types/directory'
import type { PersonRow } from '#shared/types/people'

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ directory: Directory | null; approve?: PersonRow | null }>()
const emit = defineEmits<{ saved: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { roles: workspaceRoles, refresh: loadRoles } = useRoles()

const blank = () => ({ first_name: '', last_name: '', email: '', phone: '', role: 'member', department_ids: [] as string[], job_title_ids: [] as string[], manager_id: 'none' })
const state = reactive(blank())
const people = ref<PersonRow[]>([])
watch(open, async value => {
  if (!value) return
  void loadRoles()
  const p = props.approve
  Object.assign(state, blank(), p ? { first_name: p.first_name, last_name: p.last_name, email: p.email, phone: p.phone ?? '', role: p.role, department_ids: p.departments.map(item => item.id), job_title_ids: p.job_titles.map(item => item.id) } : {})
  try {
    people.value = (await api.list<PersonRow>('/people', { page_size: 100, 'filter[status]': 'active', sort: 'name' }, { background: true })).data
  } catch {
    people.value = []
  }
})
const roles = computed(() => workspaceRoles.value.filter(role => role.id !== 'owner').map(role => ({ value: role.id, label: role.name, description: role.description ?? undefined })))
const departments = computed(() => (props.directory?.departments ?? []).filter(item => !item.archived).map(item => ({ value: item.id, label: item.name })))
const jobTitles = computed(() => (props.directory?.job_titles ?? []).filter(item => !item.archived).map(item => ({ value: item.id, label: item.name })))
const managers = computed(() => [{ value: 'none', label: t('people.none') }, ...people.value.map(item => ({ value: item.id, label: item.name, description: item.email }))])
const emailOk = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(state.email.trim()))
const phoneOk = computed(() => !state.phone.trim() || /^\+[1-9][\d\s-]{6,18}$/.test(state.phone.trim()))
const valid = computed(() => !!state.first_name.trim() && !!state.last_name.trim() && emailOk.value && phoneOk.value && !!state.role)

const saving = ref(false)
async function save() {
  if (!valid.value || saving.value) return
  saving.value = true
  const shared = { role: state.role, department_ids: state.department_ids, job_title_ids: state.job_title_ids, manager_id: state.manager_id === 'none' ? null : state.manager_id }
  try {
    if (props.approve) {
      await api.post(`/people/${props.approve.id}/approve`, shared)
      toast.add({ title: t('people.approve.done', { name: props.approve.name }), description: t('people.approve.doneDesc'), color: 'success', icon: 'i-lucide-user-check' })
    } else {
      await api.post('/people', { ...shared, first_name: state.first_name.trim(), last_name: state.last_name.trim(), email: state.email.trim(), phone: state.phone.trim() || null })
      toast.add({ title: t('people.add.done', { name: `${state.first_name} ${state.last_name}`.trim() }), description: t('people.add.doneDesc', { email: state.email.trim() }), color: 'success', icon: 'i-lucide-mail-check' })
    }
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
  <AppModal v-model:open="open" keep-open :title="approve ? t('people.approve.title', { name: approve.name }) : t('people.add.title')" :description="approve ? t('people.approve.desc') : t('people.add.desc')" :ui="{ content: 'sm:max-w-2xl' }">
    <template #body>
      <form class="flex flex-col gap-4" @submit.prevent="save">
        <div class="grid gap-4 sm:grid-cols-2">
          <UFormField :label="t('auth.fields.firstName')" required><UInput v-model="state.first_name" maxlength="60" :disabled="!!approve" class="w-full" autofocus /></UFormField>
          <UFormField :label="t('auth.fields.lastName')" required><UInput v-model="state.last_name" maxlength="60" :disabled="!!approve" class="w-full" /></UFormField>
          <UFormField :label="t('auth.fields.email')" required :error="state.email && !emailOk ? t('auth.validation.email') : undefined">
            <UInput v-model="state.email" type="email" icon="i-lucide-mail" :disabled="!!approve" dir="ltr" class="w-full" />
          </UFormField>
          <UFormField :label="t('people.col.phone')" :hint="t('people.invite.optional')" :error="!phoneOk ? t('people.join.phoneFormat') : undefined">
            <UInput v-model="state.phone" type="tel" placeholder="+44 7700 900123" icon="i-lucide-phone" :disabled="!!approve" dir="ltr" class="w-full" />
          </UFormField>
        </div>
        <USeparator />
        <div class="grid gap-4 sm:grid-cols-2">
          <UFormField :label="t('people.col.role')" required>
            <USelectMenu v-model="state.role" :items="roles" value-key="value" icon="i-lucide-shield" class="w-full" />
            <template #hint><NuxtLink to="/people/roles" class="underline">{{ t('access.manageRoles') }}</NuxtLink></template>
          </UFormField>
          <UFormField :label="t('people.col.manager')">
            <USelectMenu v-model="state.manager_id" :items="managers" value-key="value" icon="i-lucide-user-round" class="w-full" />
          </UFormField>
          <UFormField :label="t('people.col.departments')">
            <USelectMenu v-model="state.department_ids" :items="departments" value-key="value" multiple :placeholder="t('people.invite.pick')" icon="i-lucide-building-2" class="w-full" />
          </UFormField>
          <UFormField :label="t('people.col.jobTitles')">
            <USelectMenu v-model="state.job_title_ids" :items="jobTitles" value-key="value" multiple :placeholder="t('people.invite.pick')" icon="i-lucide-briefcase" class="w-full" />
          </UFormField>
        </div>
      </form>
    </template>
    <template #footer>
      <div class="flex w-full items-center justify-between gap-2">
        <span class="text-xs text-muted">{{ approve ? t('people.approve.note') : t('people.add.note') }}</span>
        <div class="flex gap-2">
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
          <UButton :label="approve ? t('people.approve.button') : t('people.add.button')" :icon="approve ? 'i-lucide-user-check' : 'i-lucide-user-plus'" color="neutral" :loading="saving" :disabled="!valid" @click="save" />
        </div>
      </div>
    </template>
  </AppModal>
</template>
