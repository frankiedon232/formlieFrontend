<!--
  Field settings → Show as (owner 2026-10-07: settings live in the right panel, not while adding): a
  choice field switches between dropdown, multi-select, single choice (radio) and checkboxes, keeping
  its options. A level of a list with levels uses its own One / Several switch (InspectorLevel).
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'
import type { FieldType } from '#shared/utils/forms/fields'
import { LIVE_FROM } from '#shared/utils/forms/options'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()

const STYLES: FieldType[] = ['dropdown', 'multi_select', 'radio', 'checkbox']
// Options kept on the server (lists above 20, large lists) or more than 20 typed: a dropdown or multi-select only
const styles = computed(() => (props.field.options_large || (props.field.options?.length ?? 0) > LIVE_FROM ? STYLES.slice(0, 2) : STYLES))
const items = computed(() => styles.value.map(type => ({ value: type, label: t(`builder.field.${type}`), icon: fieldIcon(type) })))
const pick = (value: unknown) => styles.value.includes(value as FieldType) && value !== props.field.type && builder.updateField(props.field.id, { type: value as FieldType })
</script>

<template>
  <section class="flex flex-col gap-2">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.inspector.showAs') }}</h3>
    <USelect :model-value="(field.type as FieldType)" :items="items" value-key="value" size="sm" class="w-full" :aria-label="t('builder.inspector.showAs')" @update:model-value="pick" />
    <FormsBuilderInspectorSearch :field="field" />
  </section>
</template>
