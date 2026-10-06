<!--
  An endpoint's questions (F13 M1): what can be sent (and must be), what comes back and what a GET
  list can be narrowed by. Read-only (`editable` false) in the panel; ticks in the wizard. Questions
  the API can't take say why (files, calculated values, read-only questions); the form's required
  questions are always accepted and required. Phones: one card per question.
-->
<script setup lang="ts">
import type { ApiEndpointField } from '#shared/types/apiService'
import { notAcceptedReason } from '#shared/utils/apiService/endpoints'
import { FIELD_TYPES } from '#shared/utils/forms/fields'

const props = defineProps<{ fields: ApiEndpointField[]; editable?: boolean; writes: boolean; reads: boolean }>()
const emit = defineEmits<{ change: [key: string, patch: Partial<Pick<ApiEndpointField, 'accept' | 'required' | 'returned' | 'filter'>>] }>()
const { t } = useI18n()

const icon = (type: string) => (FIELD_TYPES as Record<string, { icon: string }>)[type]?.icon ?? 'i-lucide-circle-help'
const columns = computed(() => [
  ...(props.writes ? [{ key: 'accept' as const, label: t('apiService.fields.accept') }, { key: 'required' as const, label: t('apiService.fields.required') }] : []),
  ...(props.reads ? [{ key: 'returned' as const, label: t('apiService.fields.returned') }, { key: 'filter' as const, label: t('apiService.fields.filter') }] : []),
])
type Flag = 'accept' | 'required' | 'returned' | 'filter'
function can(field: ApiEndpointField, flag: Flag) {
  if (flag === 'accept') return field.acceptable && !field.form_required
  if (flag === 'required') return field.accept && !field.form_required
  if (flag === 'filter') return field.filterable && field.returned
  return true
}
function set(field: ApiEndpointField, flag: Flag, value: boolean) {
  const patch: Partial<Record<Flag, boolean>> = { [flag]: value }
  if (flag === 'accept' && !value) patch.required = false
  if (flag === 'returned' && !value) patch.filter = false
  emit('change', field.key, patch)
}
const why = (field: ApiEndpointField) => {
  const reason = notAcceptedReason(field)
  return reason ? t(`apiService.fields.why.${reason}`) : field.form_required ? t('apiService.fields.formRequired') : ''
}
</script>

<template>
  <div class="flex flex-col">
    <AppEmpty v-if="!fields.length" size="xs" icon="i-lucide-list-checks" :title="t('apiService.fields.none')" />
    <div v-else class="overflow-hidden rounded-lg border border-default">
      <div class="hidden items-center gap-3 border-b border-default bg-elevated/50 px-3 py-2 text-xs font-medium text-muted sm:flex">
        <span class="flex-1">{{ t('apiService.fields.question') }}</span>
        <span v-for="column in columns" :key="column.key" class="w-20 text-center">{{ column.label }}</span>
      </div>
      <ul class="divide-y divide-default">
        <li v-for="field in fields" :key="field.key" class="flex flex-col gap-2 px-3 py-2.5 sm:flex-row sm:items-center sm:gap-3">
          <div class="flex min-w-0 flex-1 items-center gap-2.5">
            <span class="flex size-7 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="icon(field.type)" class="size-3.5 text-muted" /></span>
            <div class="flex min-w-0 flex-col">
              <span class="truncate text-sm text-highlighted">{{ field.label }}</span>
              <span class="truncate text-[11px] text-muted"><code class="font-mono" dir="ltr">{{ field.key }}</code><template v-if="why(field) && writes"> · {{ why(field) }}</template></span>
            </div>
          </div>
          <div class="flex flex-wrap gap-x-4 gap-y-1.5 ps-9.5 sm:flex-nowrap sm:gap-0 sm:ps-0">
            <div v-for="column in columns" :key="column.key" class="flex items-center gap-1.5 sm:w-20 sm:justify-center">
              <UCheckbox
                v-if="editable"
                :model-value="field[column.key]"
                :disabled="!can(field, column.key)"
                color="neutral"
                :aria-label="`${column.label}: ${field.label}`"
                @update:model-value="value => set(field, column.key, !!value)"
              />
              <UIcon v-else :name="field[column.key] ? 'i-lucide-check' : 'i-lucide-minus'" class="size-4" :class="field[column.key] ? 'text-highlighted' : 'text-dimmed'" :aria-label="`${column.label}: ${field[column.key] ? t('dataSources.yes') : t('dataSources.no')}`" />
              <span class="text-xs text-muted sm:hidden">{{ column.label }}</span>
            </div>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>
