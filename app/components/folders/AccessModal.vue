<!--
  Who may see a folder (F22 R2, owner 2026-10-10: "some forms and their responses belong to folders
  others should not see"). Everyone (default) or only chosen roles, departments and people. A folder
  people may not see hides its forms and their responses everywhere (lists, counts, search, responses,
  exports). Owner and people who decide folder access always see it. Needs folders.access.
-->
<script setup lang="ts">
import type { Directory } from '#shared/types/directory'
import type { FolderAccess, FormFolder } from '#shared/types/forms'

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ folder: Pick<FormFolder, 'id' | 'name'> & { access?: FolderAccess | null } }>()
const emit = defineEmits<{ saved: [] }>()
const { t } = useI18n()
const api = useApi()
const { busy, run } = useBusy()

const directory = ref<Directory | null>(null)
const state = reactive<FolderAccess>({ restricted: false, roles: [], departments: [], people: [] })
watch(open, async value => {
  if (!value) return
  const access = props.folder.access
  Object.assign(state, { restricted: !!access?.restricted, roles: [...(access?.roles ?? [])], departments: [...(access?.departments ?? [])], people: [...(access?.people ?? [])] })
  try {
    directory.value = (await api.get<Directory>('/directory', undefined, { background: true })).data
  } catch {
    directory.value = { departments: [], job_titles: [], roles: [], users: [] }
  }
})
const items = (list: Directory['roles'] | undefined) => (list ?? []).filter(item => !item.archived).map(item => ({ value: item.id, label: item.name, description: item.detail }))
// Owner always sees every folder, so it isn't offered
const roles = computed(() => items(directory.value?.roles).filter(item => item.value !== 'owner'))
const chosen = computed(() => state.roles.length + state.departments.length + state.people.length)

async function save() {
  const done = await run(() => api.put(`/folders/${props.folder.id}/access`, state.restricted ? state : { restricted: false, roles: [], departments: [], people: [] }), { success: t('folders.access.saved') })
  if (done) {
    open.value = false
    emit('saved')
  }
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="t('folders.access.title', { name: folder.name })" :description="t('folders.access.desc')" :ui="{ content: 'sm:max-w-xl' }">
    <template #body>
      <div class="flex flex-col gap-4">
        <URadioGroup
          v-model="state.restricted"
          :items="[
            { value: false, label: t('folders.access.everyone'), description: t('folders.access.everyoneHint') },
            { value: true, label: t('folders.access.restricted'), description: t('folders.access.restrictedHint') },
          ]"
          variant="card"
          color="neutral"
          :aria-label="t('folders.access.title', { name: folder.name })"
        />
        <template v-if="state.restricted">
          <USkeleton v-if="!directory" class="h-32" />
          <div v-else class="flex flex-col gap-3">
            <UFormField :label="t('folders.access.roles')">
              <USelectMenu v-model="state.roles" :items="roles" value-key="value" multiple icon="i-lucide-shield" :placeholder="t('people.invite.pick')" class="w-full" />
            </UFormField>
            <UFormField :label="t('people.col.departments')">
              <USelectMenu v-model="state.departments" :items="items(directory.departments)" value-key="value" multiple icon="i-lucide-building-2" :placeholder="t('people.invite.pick')" class="w-full" />
            </UFormField>
            <UFormField :label="t('folders.access.people')">
              <USelectMenu v-model="state.people" :items="items(directory.users)" value-key="value" multiple icon="i-lucide-user-round" :placeholder="t('people.invite.pick')" class="w-full" />
            </UFormField>
            <UAlert icon="i-lucide-info" color="neutral" variant="subtle" :description="chosen ? t('folders.access.note') : t('folders.access.nobody')" :ui="{ description: 'text-xs' }" />
          </div>
        </template>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="busy" @click="save" />
      </div>
    </template>
  </AppModal>
</template>
