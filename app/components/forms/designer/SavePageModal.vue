<!--
  Save the page around this form (its page style, tone, website link, quick facts and background)
  as a page design for the workspace (Resources → Landing pages). If the page came from one of the
  workspace's designs, the choice is "Update <design>" (forms keep their copy) or "Save as new".
-->
<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { PageDesign } from '#shared/types/forms'
import { pageTokensOf } from '#shared/utils/forms/page-design'

const props = defineProps<{ current: PageDesign | null; canCreate?: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const d = useDesigner()
const builder = useBuilder()
const library = usePageDesigns()

const schema = z.object({ name: z.string().trim().min(1, t('library.nameRequired')).max(80) })
const state = reactive({ name: '' })
const own = computed(() => (props.current && props.current.source !== 'system' ? props.current : null))
const mode = ref<'new' | 'update'>('new')
watch(open, value => {
  if (!value) return
  mode.value = own.value ? 'update' : 'new'
  state.name = own.value?.name ?? ''
})
const modes = computed(() => [
  { value: 'update', label: t('themes.updateExisting', { name: own.value?.name ?? '' }) },
  ...(props.canCreate ? [{ value: 'new', label: t('themes.saveNew') }] : []),
])

const { busy, run } = useBusy()
async function submit(event: FormSubmitEvent<z.output<typeof schema>>) {
  const tokens = pageTokensOf(d.theme.value)
  const saved = await run(() =>
    mode.value === 'update' && own.value ? library.update(own.value.id, { name: event.data.name, tokens }) : library.create(event.data.name, tokens, 'saved'),
  )
  if (!saved) return
  // The form's page now "comes from" this design (selected in Page designs).
  if (builder.schema.value) builder.schema.value.page_design_id = saved.id
  open.value = false
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('pages.saveTitle')" :description="t('pages.saveDesc')" :dismissible="!busy">
    <template #body>
      <UForm id="save-page-form" :schema="schema" :state="state" class="flex flex-col gap-4" @submit="submit">
        <URadioGroup v-if="own && canCreate" v-model="mode" :items="modes" value-key="value" color="neutral" :aria-label="t('pages.saveTitle')" />
        <UFormField name="name" :label="t('pages.editor.name')" required>
          <UInput v-model="state.name" maxlength="80" class="w-full" :placeholder="t('pages.editor.namePlaceholder')" autofocus />
        </UFormField>
      </UForm>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="save-page-form" :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="busy" />
      </div>
    </template>
  </AppModal>
</template>
