<!--
  Endpoint wizard, Methods step (F13 M2): headers every call to this endpoint must send, with the
  value they must have (up to 5; e.g. a partner id). Saved values show masked; leaving one empty
  keeps it. Names Formalie or HTTP set themselves (Authorization, Content-Type, X-Formalie-…) are refused.
-->
<script setup lang="ts">
import type { ApiHeaderDraft } from '#shared/types/apiService'
import { checkHeaderName, checkHeaderValue, MAX_REQUIRED_HEADERS } from '#shared/utils/apiService/tokens'

const rows = defineModel<ApiHeaderDraft[]>({ required: true })
defineProps<{ showErrors?: boolean }>()
const { t } = useI18n()
const errorsOf = (row: ApiHeaderDraft, index: number) => {
  const name = checkHeaderName(row.name.trim())
  const duplicate = rows.value.findIndex(item => item.name.trim().toLowerCase() === row.name.trim().toLowerCase()) !== index
  const value = row.value === null && row.preview ? null : checkHeaderValue(row.value ?? '')
  return { name: name ? t(`apiService.headers.invalid.${name}`) : duplicate ? t('apiService.headers.invalid.duplicate') : undefined, value: value ? t(`apiService.headers.invalid.${value}`) : undefined }
}
const add = () => rows.value.length < MAX_REQUIRED_HEADERS && (rows.value = [...rows.value, { name: '', value: '', preview: null }])
const remove = (index: number) => (rows.value = rows.value.filter((_, i) => i !== index))
const setName = (index: number, name: string) => (rows.value = rows.value.map((row, i) => (i === index ? { ...row, name: name.replace(/[^A-Za-z0-9-]/g, '').slice(0, 64) } : row)))
const setValue = (index: number, value: string) => (rows.value = rows.value.map((row, i) => (i === index ? { ...row, value: value === '' && row.preview ? null : value } : row)))
</script>

<template>
  <div class="flex flex-col gap-3 rounded-lg border border-default p-3 sm:p-4">
    <div>
      <h3 class="text-sm font-semibold text-highlighted">{{ t('apiService.headers.requiredTitle') }}</h3>
      <p class="text-xs text-muted">{{ t('apiService.headers.requiredDesc') }}</p>
    </div>
    <div v-for="(row, index) in rows" :key="index" class="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-start">
      <UFormField :error="showErrors ? errorsOf(row, index).name : undefined" :label="index === 0 ? t('apiService.headers.name') : undefined">
        <UInput :model-value="row.name" placeholder="X-Partner-Id" class="w-full" :ui="{ base: 'font-mono' }" dir="ltr" :aria-label="t('apiService.headers.name')" @update:model-value="value => setName(index, String(value))" />
      </UFormField>
      <UFormField :error="showErrors ? errorsOf(row, index).value : undefined" :label="index === 0 ? t('apiService.headers.value') : undefined">
        <UInput :model-value="row.value ?? ''" :placeholder="row.preview ? t('apiService.headers.keep', { preview: row.preview }) : 'acme-42'" class="w-full" :ui="{ base: 'font-mono' }" dir="ltr" :aria-label="t('apiService.headers.value')" @update:model-value="value => setValue(index, String(value))" />
      </UFormField>
      <UButton icon="i-lucide-x" color="neutral" variant="ghost" square :class="index === 0 ? 'sm:mt-6' : ''" :aria-label="t('apiService.headers.remove')" @click="remove(index)" />
    </div>
    <UButton v-if="rows.length < MAX_REQUIRED_HEADERS" :label="t('apiService.headers.add')" icon="i-lucide-plus" color="neutral" variant="outline" size="sm" class="w-fit" @click="add" />
  </div>
</template>
