<!--
  Manage folders: create, rename inline, delete. A folder that still holds forms can't be deleted
  (owner, 2026-10-03), its forms are one click away to move them first.
-->
<script setup lang="ts">
import type { FormFolder } from '#shared/types/forms'

defineProps<{ folders: FormFolder[]; loading?: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ changed: [] }>()

const { t } = useI18n()
const api = useApi()
const toast = useToast()
const confirm = useConfirm()
const { handle } = useErrorHandler()

const busyId = ref<string | null>(null)
const editingId = ref<string | null>(null)
const editName = ref('')
const newName = ref('')

async function act(id: string, work: () => Promise<unknown>, success: string) {
  if (busyId.value) return
  busyId.value = id
  try {
    await work()
    toast.add({ title: success, color: 'success', icon: 'i-lucide-circle-check' })
    emit('changed')
  } catch (error) {
    handle(error)
  } finally {
    busyId.value = null
  }
}

function startRename(folder: FormFolder) {
  editingId.value = folder.id
  editName.value = folder.name
}
async function saveRename(folder: FormFolder) {
  const name = editName.value.trim()
  editingId.value = null
  if (!name || name === folder.name) return
  await act(folder.id, () => api.patch(`/folders/${folder.id}`, { name }), t('forms.folders.renamed'))
}
async function remove(folder: FormFolder) {
  const ok = await confirm({
    title: t('forms.folders.deleteTitle', { name: folder.name }),
    description: t('forms.folders.deleteEmpty'),
    confirmLabel: t('forms.actions.delete'),
    danger: true,
  })
  if (ok) await act(folder.id, () => api.del(`/folders/${folder.id}`), t('forms.folders.deleted'))
}
async function create() {
  const name = newName.value.trim()
  if (!name) return
  await act('__new__', () => api.post('/folders', { name }), t('forms.folders.created'))
  newName.value = ''
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('forms.folders.title')" :description="t('forms.folders.desc')">
    <template #body>
      <div class="flex flex-col gap-4">
        <div v-if="loading" class="space-y-2" :aria-label="t('common.loading')">
          <USkeleton v-for="n in 3" :key="n" class="h-10 w-full" />
        </div>
        <ul v-else-if="folders.length" class="divide-y divide-default rounded-lg border border-default">
          <li
            v-for="folder in folders"
            :key="folder.id"
            class="flex items-center gap-2 px-3 py-2"
            :class="busyId === folder.id ? 'pointer-events-none opacity-50 motion-safe:animate-pulse' : ''"
            :aria-busy="busyId === folder.id || undefined"
          >
            <UIcon name="i-lucide-folder" class="size-4 shrink-0 text-muted" />
            <UInput
              v-if="editingId === folder.id"
              v-model="editName"
              size="sm"
              maxlength="60"
              autofocus
              class="min-w-0 flex-1"
              :aria-label="t('forms.folders.rename')"
              @keydown.enter.prevent="saveRename(folder)"
              @keydown.esc.prevent.stop="editingId = null"
              @blur="saveRename(folder)"
            />
            <template v-else>
              <span class="min-w-0 flex-1 truncate text-sm text-highlighted">{{ folder.name }}</span>
              <span class="text-xs text-muted tabular-nums">{{
                t('forms.folders.count', { count: folder.forms_count ?? 0 }, folder.forms_count ?? 0)
              }}</span>
              <UButton
                v-if="folder.can?.edit"
                icon="i-lucide-pencil"
                color="neutral"
                variant="ghost"
                size="xs"
                :aria-label="t('forms.folders.renameNamed', { name: folder.name })"
                @click="startRename(folder)"
              />
              <UButton
                v-if="folder.forms_count"
                icon="i-lucide-arrow-up-right"
                color="neutral"
                variant="ghost"
                size="xs"
                :to="`/forms?folder_id=${folder.id}`"
                :aria-label="t('forms.folders.viewForms', { name: folder.name })"
                @click="open = false"
              />
              <UTooltip v-if="folder.can?.delete" :text="folder.forms_count ? t('forms.folders.notEmpty') : t('forms.folders.deleteNamed', { name: folder.name })">
                <UButton
                  icon="i-lucide-trash-2"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  :disabled="!!folder.forms_count"
                  :loading="busyId === folder.id"
                  :aria-label="t('forms.folders.deleteNamed', { name: folder.name })"
                  @click="remove(folder)"
                />
              </UTooltip>
            </template>
          </li>
        </ul>
        <p v-else class="rounded-lg border border-dashed border-default p-4 text-center text-sm text-muted">
          {{ t('forms.folders.empty') }}
        </p>

        <form v-if="useCan().can('folders.create')" class="flex items-end gap-2" @submit.prevent="create">
          <UFormField :label="t('forms.folders.newName')" class="flex-1">
            <UInput v-model="newName" maxlength="60" icon="i-lucide-folder-plus" class="w-full" />
          </UFormField>
          <UButton
            type="submit"
            :label="t('forms.folders.create')"
            color="neutral"
            :loading="busyId === '__new__'"
            :disabled="!newName.trim()"
          />
        </form>
      </div>
    </template>
  </AppModal>
</template>
