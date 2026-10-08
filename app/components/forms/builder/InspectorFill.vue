<!--
  Field settings → Fill other fields (F15 M4) for one-choice fields whose options carry details (a list
  with columns): each detail can fill a question of the form when an option is chosen, and can lock it
  (people can't change it, the server fills it too). Stored as `props.fills`; the logic engine applies it.
-->
<script setup lang="ts">
import { allFields, type FormField } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'
import { fillsOf, type FieldFill } from '#shared/utils/forms/fills'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()
const library = useFieldLibrary()
onMounted(() => library.load())

/** The list's columns, else the detail keys its options carry. */
const columns = computed(() => {
  const list = props.field.option_set_id ? library.lists.value.find(item => item.id === props.field.option_set_id) : undefined
  if (list?.columns?.length) return list.columns
  const keys = new Set((props.field.options ?? []).flatMap(option => Object.keys((option as { attrs?: Record<string, unknown> }).attrs ?? {})))
  return [...keys].map(key => ({ key, label: key }))
})
const NONE = 'none'
const fills = computed(() => fillsOf(props.field))
const targets = computed(() => [
  // A select item can't have an empty value: "none" stands for no fill
  { value: NONE, label: t('builder.fill.none') },
  ...(builder.schema.value ? allFields(builder.schema.value) : [])
    .filter(item => item.id !== props.field.id && isInputField(item.type) && !['file_upload', 'image_upload', 'signature', 'calculated', 'hidden'].includes(item.type))
    .map(item => ({ value: item.id, label: item.label || t('builder.untitled') })),
])
const fillFor = (key: string) => fills.value.find(item => item.column === key)
function save(next: FieldFill[]) {
  builder.updateProps(props.field.id, { fills: next.length ? next : undefined })
}
const setTarget = (key: string, target: unknown) =>
  save([...fills.value.filter(item => item.column !== key), ...(typeof target === 'string' && target && target !== NONE ? [{ column: key, target, lock: fillFor(key)?.lock ?? true }] : [])])
const setLock = (key: string, lock: boolean) => save(fills.value.map(item => (item.column === key ? { ...item, lock } : item)))
</script>

<template>
  <section v-if="columns.length && (field.type === 'dropdown' || field.type === 'radio')" class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.fill.title') }}</h3>
    <p class="text-xs text-muted">{{ t('builder.fill.hint') }}</p>
    <div v-for="column in columns" :key="column.key" class="flex flex-col gap-1.5 rounded-md border border-default p-2">
      <div class="flex items-center gap-2">
        <span class="w-24 shrink-0 truncate text-xs font-medium text-highlighted" :title="column.label">{{ column.label }}</span>
        <UIcon name="i-lucide-arrow-right" class="size-3.5 shrink-0 text-muted rtl:rotate-180" />
        <USelect :model-value="fillFor(column.key)?.target ?? NONE" :items="targets" value-key="value" size="xs" class="min-w-0 flex-1" :aria-label="t('builder.fill.target', { name: column.label })" @update:model-value="value => setTarget(column.key, value)" />
      </div>
      <USwitch v-if="fillFor(column.key)" :model-value="fillFor(column.key)!.lock !== false" :label="t('builder.fill.lock')" size="xs" color="neutral" @update:model-value="value => setLock(column.key, !!value)" />
    </div>
  </section>
</template>
