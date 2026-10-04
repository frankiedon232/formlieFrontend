<!--
  Import tab of New form: drop or pick a form export (.json, up to 1 MB). The file is validated
  against FormSchema v1 and summarised before anything is created.
-->
<script setup lang="ts">
import { countFields, formImportFile, MAX_IMPORT_BYTES, type FormSchemaV1 } from '#shared/utils/forms/schema'

const imported = defineModel<{ name?: string; schema: FormSchemaV1 } | null>({ required: true })
const { t } = useI18n()

const file = ref<File | null>(null)
const reading = ref(false)
const importError = ref<string | null>(null)

watch(file, async picked => {
  imported.value = null
  importError.value = null
  if (!picked) return
  if (picked.size > MAX_IMPORT_BYTES) return (importError.value = t('forms.new.tooBig'))
  reading.value = true
  try {
    const raw: unknown = JSON.parse(await picked.text())
    const parsed = formImportFile.safeParse(raw)
    if (!parsed.success) {
      // A union reports one wrapper issue; use the branch that matches the file's shape
      // (`{ name, schema }` export vs a bare schema) so the path points at the real problem.
      const issue = parsed.error.issues[0]
      const wrapped = !!raw && typeof raw === 'object' && 'schema' in raw
      const inner = issue?.code === 'invalid_union' ? issue.errors[wrapped ? 0 : 1]?.[0] : issue
      importError.value = t('forms.new.invalid', { detail: inner?.path.join('.') || '-' })
      return
    }
    imported.value = parsed.data
  } catch {
    importError.value = t('forms.new.notJson')
  } finally {
    reading.value = false
  }
})

</script>

<template>
  <div class="flex flex-col gap-3">
    <UFileUpload
      v-model="file"
      accept="application/json,.json"
      :label="t('forms.new.drop')"
      :description="t('forms.new.dropHint')"
      icon="i-lucide-file-json"
      color="neutral"
      layout="list"
      class="min-h-36 w-full"
    />
    <p v-if="reading" class="flex items-center gap-2 text-sm text-muted" aria-live="polite">
      <UIcon name="i-lucide-loader-circle" class="size-4 animate-spin" /> {{ t('forms.new.reading') }}
    </p>
    <UAlert
      v-if="importError"
      icon="i-lucide-file-x"
      color="error"
      variant="subtle"
      :title="importError"
    />
    <UAlert
      v-if="imported"
      icon="i-lucide-file-check"
      color="success"
      variant="subtle"
      :title="t('forms.new.ready')"
      :description="
        t('forms.new.summary', {
          pages: imported.schema.pages.length,
          fields: countFields(imported.schema),
        })
      "
    />
  </div>
</template>
