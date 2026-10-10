<!--
  Save the current design as a theme for the workspace. If this design came from a saved theme,
  the choice is "Update <theme>" (changes it for future use, forms keep their copy) or "Save as new".
-->
<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { SavedTheme } from '#shared/types/forms'

const props = defineProps<{ current: SavedTheme | null; canCreate?: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const d = useDesigner()
const builder = useBuilder()
const library = useThemes()

const schema = z.object({ name: z.string().trim().min(1, t('library.nameRequired')).max(80) })
const state = reactive({ name: '' })
const mode = ref<'new' | 'update'>('new')
watch(open, value => {
  if (!value) return
  mode.value = props.current ? 'update' : 'new'
  state.name = props.current?.name ?? ''
})
const modes = computed(() => [
  { value: 'update', label: t('themes.updateExisting', { name: props.current?.name ?? '' }) },
  ...(props.canCreate ? [{ value: 'new', label: t('themes.saveNew') }] : []),
])

const { busy, run } = useBusy()
async function submit(event: FormSubmitEvent<z.output<typeof schema>>) {
  const tokens = structuredClone(toRaw(d.theme.value))
  const saved = await run(() =>
    mode.value === 'update' && props.current
      ? library.update(props.current.id, { name: event.data.name, tokens })
      : library.create(event.data.name, tokens),
  )
  if (!saved) return
  // The form now "comes from" this theme (shown as selected in Your themes).
  d.write(tokens)
  if (builder.schema.value) builder.schema.value.theme_id = saved.id
  open.value = false
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('themes.saveTitle')" :description="t('themes.saveDesc')" :dismissible="!busy">
    <template #body>
      <UForm id="save-theme-form" :schema="schema" :state="state" class="flex flex-col gap-4" @submit="submit">
        <URadioGroup v-if="current && canCreate" v-model="mode" :items="modes" value-key="value" color="neutral" :aria-label="t('themes.saveTitle')" />
        <UFormField name="name" :label="t('themes.name')" required>
          <UInput v-model="state.name" maxlength="80" class="w-full" :placeholder="t('themes.namePlaceholder')" autofocus />
        </UFormField>
      </UForm>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="save-theme-form" :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="busy" />
      </div>
    </template>
  </AppModal>
</template>
