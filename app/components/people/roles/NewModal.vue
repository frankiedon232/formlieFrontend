<!-- New role (F22): a name, a line about it, and where to start (nothing ticked, or a copy of a role). -->
<script setup lang="ts">
import type { RoleRow } from '#shared/types/people'

const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ created: [role: RoleRow] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const state = reactive({ name: '', description: '', copy_of: 'none' })
const roles = ref<RoleRow[]>([])
watch(open, async value => {
  if (!value) return
  Object.assign(state, { name: '', description: '', copy_of: 'none' })
  try {
    roles.value = (await api.get<RoleRow[]>('/roles', undefined, { background: true })).data
  } catch {
    roles.value = []
  }
})
const starts = computed(() => [{ value: 'none', label: t('access.startEmpty') }, ...roles.value.map(role => ({ value: role.id, label: t('access.startCopy', { name: role.name }) }))])
const saving = ref(false)
async function create() {
  if (!state.name.trim() || saving.value) return
  saving.value = true
  try {
    const { data } = await api.post<RoleRow>('/roles', { name: state.name.trim(), description: state.description.trim() || null, ...(state.copy_of !== 'none' ? { copy_of: state.copy_of } : { permissions: [] }) })
    open.value = false
    emit('created', data)
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="t('access.new')" :description="t('access.newDesc')">
    <template #body>
      <form class="flex flex-col gap-4" @submit.prevent="create">
        <UFormField :label="t('access.name')" required><UInput v-model="state.name" maxlength="60" :placeholder="t('access.namePlaceholder')" class="w-full" autofocus /></UFormField>
        <UFormField :label="t('optionSets.description')"><UInput v-model="state.description" maxlength="300" class="w-full" /></UFormField>
        <UFormField :label="t('access.start')"><USelect v-model="state.copy_of" :items="starts" value-key="value" class="w-full" /></UFormField>
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton :label="t('access.create')" icon="i-lucide-check" color="neutral" :loading="saving" :disabled="!state.name.trim()" @click="create" />
      </div>
    </template>
  </AppModal>
</template>
