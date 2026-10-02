<!--
  Calculated fields: one row per field with its formula, the problem (if any) and the number
  fields it can use as chips (click → inserts {key} at the end). Formulas are stored on the field.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const { t } = useI18n()
const builder = useBuilder()
const logic = useLogicRules()

const formulaOf = (field: FormField) => String(field.props?.formula ?? '')
const setFormula = (field: FormField, formula: string) =>
  builder.updateProps(field.id, { formula }, `formula:${field.id}`)
const insert = (field: FormField, key: string) =>
  setFormula(field, `${formulaOf(field).trimEnd()} {${key}}`.trimStart())
const keysFor = (field: FormField) => logic.numericKeys.value.filter(key => key !== field.key)
</script>

<template>
  <UCard :ui="{ header: 'flex items-center gap-2 p-3 sm:px-4', body: 'p-0 sm:p-0' }">
    <template #header>
      <h2 class="text-sm font-semibold text-highlighted">{{ t('logic.calc.title') }}</h2>
      <UBadge :label="String(logic.calculated.value.length)" color="neutral" variant="outline" size="sm" class="rounded-md" />
    </template>

    <UEmpty
      v-if="!logic.calculated.value.length"
      icon="i-lucide-calculator"
      :title="t('logic.calc.emptyTitle')"
      :description="t('logic.calc.emptyDesc')"
      :actions="[{ label: t('logic.calc.addField'), icon: 'i-lucide-layout-panel-top', color: 'neutral', variant: 'outline', to: `/forms/${$route.params.id}/build` }]"
      size="sm"
      class="py-8"
    />

    <ul v-else class="divide-y divide-default">
      <li v-for="field in logic.calculated.value" :key="field.id" class="flex flex-col gap-2 p-3 sm:px-4">
        <div class="flex min-w-0 items-center gap-2">
          <UIcon name="i-lucide-calculator" class="size-4 shrink-0 text-muted" />
          <span class="truncate text-sm font-medium text-highlighted">{{ logic.label(field) }}</span>
          <code class="truncate text-xs text-muted">{{ field.key }}</code>
        </div>
        <UFormField :error="logic.formulaProblem(field) ?? undefined" :hint="t('logic.calc.hint')" :ui="{ hint: 'text-xs' }">
          <UInput
            :model-value="formulaOf(field)"
            icon="i-lucide-equal"
            class="w-full font-mono"
            :placeholder="t('logic.calc.placeholder')"
            :aria-label="t('logic.calc.formulaFor', { field: logic.label(field) })"
            @update:model-value="v => setFormula(field, String(v))"
          />
        </UFormField>
        <div v-if="keysFor(field).length" class="flex flex-wrap items-center gap-1">
          <span class="me-1 text-xs text-muted">{{ t('logic.calc.use') }}</span>
          <UButton
            v-for="key in keysFor(field)"
            :key="key"
            :label="`{${key}}`"
            color="neutral"
            variant="outline"
            size="xs"
            class="font-mono"
            @click="insert(field, key)"
          />
        </div>
      </li>
    </ul>
  </UCard>
</template>
