<!--
  New folder / edit folder (F11 M4): its name and its colour (the icon in the sidebar, on its card
  and on its page). Eighteen colours as swatches (arrow keys move between them) and "Custom" for any
  other (owner 2026-10-05: more colours and a picker): Nuxt UI's colour picker plus a hex box.
  Saving refreshes the sidebar counts; a new folder can open its page straight away.
-->
<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { FormFolder } from '#shared/types/forms'
import { FOLDER_COLORS, FOLDER_COLOR_KEYS, folderColor, isCustomColor } from '#shared/utils/forms/folders'

const props = defineProps<{ folder?: Pick<FormFolder, 'id' | 'name' | 'color'> | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [folder: FormFolder] }>()
const { t } = useI18n()
const api = useApi()
const counts = useNavCounts()
const { busy, run } = useBusy()

const schema = z.object({ name: z.string().trim().min(1, t('library.nameRequired')).max(60) })
const state = reactive({ name: '' })
/** A named colour (`teal`) or a custom one (`#3a7bd5`). */
const color = ref<string>('ink')
const custom = ref('#3a7bd5')
const customOpen = ref(false)
const hex = ref('')
watch(open, value => {
  if (!value) return
  state.name = props.folder?.name ?? ''
  color.value = props.folder?.color || 'ink'
  if (isCustomColor(color.value)) custom.value = color.value
})
watch(custom, value => {
  hex.value = value
  if (customOpen.value) color.value = value
})
function typedHex(value: string) {
  hex.value = value.startsWith('#') ? value : `#${value}`
  if (isCustomColor(hex.value)) custom.value = hex.value.toLowerCase()
}
watch(customOpen, value => value && ((color.value = custom.value), (hex.value = custom.value)))

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

/** Arrow keys move between the named colours (radio group); focus follows the choice. */
const swatches = useTemplateRef<HTMLElement>('swatches')
async function step(by: number) {
  const index = Math.max(0, FOLDER_COLOR_KEYS.indexOf(color.value as (typeof FOLDER_COLOR_KEYS)[number]))
  color.value = FOLDER_COLOR_KEYS[(index + by + FOLDER_COLOR_KEYS.length) % FOLDER_COLOR_KEYS.length]!
  await nextTick()
  swatches.value?.querySelector<HTMLElement>('[role="radio"][aria-checked="true"]')?.focus()
}
const preview = computed(() => folderColor(color.value))
</script>

<template>
  <AppModal v-model:open="open" :title="folder ? t('folders.editTitle') : t('forms.folders.new')" :description="t('folders.editDesc')" :dismissible="!busy">
    <template #body>
      <UForm id="folder-form" :schema="schema" :state="state" class="flex flex-col gap-5" @submit="submit">
        <UFormField name="name" :label="t('forms.folders.newName')" required>
          <UInput v-model="state.name" maxlength="60" :placeholder="t('folders.namePlaceholder')" class="w-full" autofocus>
            <template #leading><UIcon name="i-lucide-folder" class="size-4" :class="preview.text" :style="preview.textStyle" /></template>
          </UInput>
        </UFormField>
        <UFormField :label="t('folders.color')">
          <div
            ref="swatches"
            class="grid grid-cols-7 gap-2 sm:grid-cols-10"
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
              :title="t(`folders.colors.${key}`)"
              :tabindex="color === key || (key === 'ink' && !FOLDER_COLOR_KEYS.includes(color as never)) ? 0 : -1"
              class="flex aspect-square items-center justify-center rounded-full ring-offset-2 ring-offset-(--ui-bg) transition focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="[FOLDER_COLORS[key].bg, color === key ? 'ring-2 ring-(--ui-border-inverted)' : 'hover:scale-105']"
              @click="color = key"
            >
              <UIcon v-if="color === key" name="i-lucide-check" class="size-4 text-white mix-blend-difference" />
            </button>

            <!-- Custom: any colour, with Nuxt UI's colour picker and a hex box -->
            <UPopover v-model:open="customOpen" :content="{ align: 'end' }">
              <button
                type="button"
                role="radio"
                :aria-checked="isCustomColor(color)"
                :aria-label="t('folders.colors.custom')"
                :title="t('folders.colors.custom')"
                class="flex aspect-square items-center justify-center rounded-full ring-offset-2 ring-offset-(--ui-bg) transition focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
                :class="isCustomColor(color) ? 'ring-2 ring-(--ui-border-inverted)' : 'hover:scale-105'"
                :style="isCustomColor(color) ? { backgroundColor: color } : { background: 'conic-gradient(#ef4444, #f59e0b, #84cc16, #10b981, #06b6d4, #3b82f6, #8b5cf6, #ec4899, #ef4444)' }"
              >
                <UIcon :name="isCustomColor(color) ? 'i-lucide-check' : 'i-lucide-plus'" class="size-4 text-white mix-blend-difference" />
              </button>
              <template #content>
                <div class="flex w-60 flex-col gap-3 p-3">
                  <UColorPicker v-model="custom" class="w-full" />
                  <UInput :model-value="hex" maxlength="7" :aria-label="t('folders.hex')" class="font-mono" @update:model-value="value => typedHex(String(value))">
                    <template #leading><span class="size-4 rounded-sm border border-default" :style="{ backgroundColor: custom }" /></template>
                  </UInput>
                </div>
              </template>
            </UPopover>
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
