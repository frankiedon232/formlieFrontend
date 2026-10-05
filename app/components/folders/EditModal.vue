<!--
  New folder / edit folder (F11 M4): its name and its colour (the icon in the sidebar and on its
  page), picked from a small palette shown as swatches (arrow keys move between them). Saving
  refreshes the sidebar counts; a new folder can open its page straight away.
-->
<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { FormFolder } from '#shared/types/forms'
import { FOLDER_COLORS, FOLDER_COLOR_KEYS, type FolderColor } from '#shared/utils/forms/folders'

const props = defineProps<{ folder?: Pick<FormFolder, 'id' | 'name' | 'color'> | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [folder: FormFolder] }>()
const { t } = useI18n()
const api = useApi()
const counts = useNavCounts()
const { busy, run } = useBusy()

const schema = z.object({ name: z.string().trim().min(1, t('library.nameRequired')).max(60) })
const state = reactive({ name: '' })
const color = ref<FolderColor>('ink')
watch(open, value => {
  if (!value) return
  state.name = props.folder?.name ?? ''
  color.value = (props.folder?.color as FolderColor | undefined) ?? 'ink'
})

async function submit(event: FormSubmitEvent<z.output<typeof schema>>) {
  const body = { name: event.data.name, color: color.value }
  const result = await run(() => (props.folder ? api.patch<FormFolder>(`/folders/${props.folder.id}`, body) : api.post<FormFolder>('/folders', body)), {
    success: props.folder ? t('folders.toast.saved') : t('folders.toast.created', { name: event.data.name }),
  })
  if (!result) return
  void counts.refresh(true)
  emit('saved', result.data)
  open.value = false
}

/** Arrow keys move the colour choice (radio group). */
function step(by: number) {
  const index = FOLDER_COLOR_KEYS.indexOf(color.value)
  color.value = FOLDER_COLOR_KEYS[(index + by + FOLDER_COLOR_KEYS.length) % FOLDER_COLOR_KEYS.length]!
}
</script>

<template>
  <AppModal v-model:open="open" :title="folder ? t('folders.editTitle') : t('forms.folders.new')" :description="t('folders.editDesc')" :dismissible="!busy">
    <template #body>
      <UForm id="folder-form" :schema="schema" :state="state" class="flex flex-col gap-5" @submit="submit">
        <UFormField name="name" :label="t('forms.folders.newName')" required>
          <UInput v-model="state.name" maxlength="60" :placeholder="t('folders.namePlaceholder')" class="w-full" autofocus>
            <template #leading><UIcon name="i-lucide-folder" class="size-4" :class="FOLDER_COLORS[color].text" /></template>
          </UInput>
        </UFormField>
        <UFormField :label="t('folders.color')">
          <div
            class="flex flex-wrap gap-2"
            role="radiogroup"
            :aria-label="t('folders.color')"
            @keydown.right.prevent="step(1)"
            @keydown.down.prevent="step(1)"
            @keydown.left.prevent="step(-1)"
            @keydown.up.prevent="step(-1)"
          >
            <button
              v-for="key in FOLDER_COLOR_KEYS"
              :key="key"
              type="button"
              role="radio"
              :aria-checked="color === key"
              :aria-label="t(`folders.colors.${key}`)"
              :tabindex="color === key ? 0 : -1"
              class="flex size-9 items-center justify-center rounded-full ring-offset-2 ring-offset-(--ui-bg) transition focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="[FOLDER_COLORS[key].bg, color === key ? 'ring-2 ring-(--ui-border-inverted)' : 'hover:scale-105']"
              @click="color = key"
            >
              <UIcon v-if="color === key" name="i-lucide-check" class="size-4 text-white mix-blend-difference" />
            </button>
          </div>
        </UFormField>
      </UForm>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="folder-form" :label="folder ? t('common.save') : t('forms.folders.create')" icon="i-lucide-check" color="neutral" :loading="busy" />
      </div>
    </template>
  </AppModal>
</template>
