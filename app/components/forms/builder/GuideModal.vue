<!--
  Write the form's help guide (F10, owner 2026-10-03): a title and rich text (headings, lists,
  links, alignment) explaining how to fill in this form. Respondents open it from the "?" button.
  Changes go into the draft like every other setting (published with the form).
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const builder = useBuilder()
const schema = builder.schema

const title = ref('')
const html = ref<unknown>('')
watch(
  open,
  value => {
    if (!value) return
    const guide = schema.value?.settings?.guide
    title.value = guide?.title ?? ''
    html.value = guide?.html ?? ''
  },
  { immediate: true },
)

/** The rich text editor respondents use, with the full toolbar. */
const editorField = { id: 'guide', key: 'guide', type: 'rich_text', label: '', width: 12, required: false, props: { toolbar: 'full' } } as FormField

function save() {
  if (!schema.value) return
  builder.history.record()
  const current = schema.value.settings?.guide
  schema.value.settings = {
    ...schema.value.settings,
    guide: { enabled: current?.enabled ?? true, title: title.value.trim().slice(0, 120), html: String(html.value ?? '') },
  }
  open.value = false
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('builder.guide.editTitle')" :description="t('builder.guide.editDesc')" :ui="{ content: 'sm:max-w-3xl' }">
    <template #body>
      <div class="flex flex-col gap-4">
        <UFormField :label="t('builder.guide.titleLabel')">
          <UInput v-model="title" maxlength="120" :placeholder="t('builder.guide.titlePlaceholder')" class="w-full" />
        </UFormField>
        <UFormField :label="t('builder.guide.content')" :description="t('builder.guide.contentHint')">
          <div class="min-h-64 rounded-md border border-default">
            <FormsRendererRichText id="guide-editor" v-model="html" :field="editorField" mode="live" />
          </div>
        </UFormField>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" class="justify-center" @click="open = false" />
        <UButton :label="t('builder.guide.save')" icon="i-lucide-check" color="neutral" class="justify-center" @click="save" />
      </div>
    </template>
  </AppModal>
</template>
