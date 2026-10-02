<!-- Rename a saved theme (themes library). -->
<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { SavedTheme } from '#shared/types/forms'

const props = defineProps<{ theme: SavedTheme | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [] }>()
const { t } = useI18n()
const library = useThemes()

const schema = z.object({ name: z.string().trim().min(1, t('library.nameRequired')).max(80) })
const state = reactive({ name: '' })
watch(open, value => {
  if (value) state.name = props.theme?.name ?? ''
})
const { busy, run } = useBusy()
async function submit(event: FormSubmitEvent<z.output<typeof schema>>) {
  if (!props.theme) return
  if (await run(() => library.update(props.theme!.id, { name: event.data.name }))) {
    emit('saved')
    open.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('themes.renameTitle')" :dismissible="!busy">
    <template #body>
      <UForm id="rename-theme-form" :schema="schema" :state="state" @submit="submit">
        <UFormField name="name" :label="t('themes.name')" required>
          <UInput v-model="state.name" maxlength="80" class="w-full" autofocus />
        </UFormField>
      </UForm>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="rename-theme-form" :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="busy" />
      </div>
    </template>
  </AppModal>
</template>
