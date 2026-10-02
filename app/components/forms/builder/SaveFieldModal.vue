<!-- Save the selected field to the workspace library (palette → Saved) under a name. -->
<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const library = useFieldLibrary()

const schema = z.object({ name: z.string().trim().min(1, t('library.nameRequired')).max(80) })
const state = reactive({ name: '' })
watch(open, value => {
  if (value) state.name = props.field.label || t(`builder.field.${props.field.type}`)
})

const { busy, run } = useBusy()
async function submit(event: FormSubmitEvent<z.output<typeof schema>>) {
  if (await run(() => library.saveField(event.data.name, props.field))) open.value = false
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('library.saveFieldTitle')" :description="t('library.saveFieldDesc')" :dismissible="!busy">
    <template #body>
      <UForm id="save-field-form" :schema="schema" :state="state" @submit="submit">
        <UFormField name="name" :label="t('library.fieldName')" required>
          <UInput v-model="state.name" maxlength="80" class="w-full" autofocus />
        </UFormField>
      </UForm>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="save-field-form" :label="t('library.saveField')" icon="i-lucide-bookmark-plus" color="neutral" :loading="busy" />
      </div>
    </template>
  </AppModal>
</template>
