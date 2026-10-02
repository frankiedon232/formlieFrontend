<!-- Move one or more forms to a folder (or out of folders); a new folder can be created on the spot. -->
<script setup lang="ts">
import type { FormFolder } from '#shared/types/forms'

const props = defineProps<{ folders: FormFolder[]; count: number; current?: string | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ move: [folderId: string | null]; folderCreated: [] }>()

const { t } = useI18n()
const api = useApi()
const { busy, run } = useBusy()

const NONE = '__none__'
const selected = ref<string>(NONE)
const creating = ref(false)
const newName = ref('')

watch(open, value => {
  if (!value) return
  selected.value = props.current ?? NONE
  creating.value = false
  newName.value = ''
})

const items = computed(() => [
  { value: NONE, label: t('forms.noFolder'), icon: 'i-lucide-folder-minus' },
  ...props.folders.map(folder => ({ value: folder.id, label: folder.name, icon: 'i-lucide-folder' })),
])

async function createFolder() {
  const created = await run(() => api.post<FormFolder>('/folders', { name: newName.value.trim() }))
  if (!created) return
  emit('folderCreated')
  selected.value = created.data.id
  creating.value = false
  newName.value = ''
}

function submit() {
  emit('move', selected.value === NONE ? null : selected.value)
  open.value = false
}
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="t('forms.move.title', { count }, count)"
    :description="t('forms.move.desc')"
  >
    <template #body>
      <div class="flex flex-col gap-4">
        <UFormField :label="t('forms.move.folder')">
          <USelectMenu
            v-model="selected"
            :items="items"
            value-key="value"
            :search-input="{ placeholder: t('common.search') }"
            class="w-full"
          />
        </UFormField>
        <form v-if="creating" class="flex items-end gap-2" @submit.prevent="createFolder">
          <UFormField :label="t('forms.folders.newName')" class="flex-1">
            <UInput v-model="newName" maxlength="60" autofocus class="w-full" />
          </UFormField>
          <UButton
            type="submit"
            :label="t('forms.folders.create')"
            color="neutral"
            :loading="busy"
            :disabled="!newName.trim()"
          />
        </form>
        <UButton
          v-else
          :label="t('forms.folders.new')"
          icon="i-lucide-folder-plus"
          color="neutral"
          variant="link"
          class="self-start px-0"
          @click="creating = true"
        />
      </div>
    </template>
    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" class="justify-center" @click="open = false" />
        <UButton
          :label="t('forms.move.submit')"
          icon="i-lucide-folder-input"
          color="neutral"
          class="justify-center"
          :disabled="busy"
          @click="submit"
        />
      </div>
    </template>
  </AppModal>
</template>
