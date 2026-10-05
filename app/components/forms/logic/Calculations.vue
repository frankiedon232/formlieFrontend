<!--
  Calculated fields: one row per field with its formula and its problem (if any), chips that
  insert a field ({key}) or a function, and a short guide: choice answers count as the number
  given to each option (Options → "Give options numbers"), and if() picks a value by condition.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const { t } = useI18n()
const builder = useBuilder()
const logic = useLogicRules()

const FUNCTIONS = ['if({a} > 0, 1, 0)', 'round(, 2)', 'min(, )', 'max(, )', 'sum(, )']
const formulaOf = (field: FormField) => String(field.props?.formula ?? '')
const setFormula = (field: FormField, formula: string) =>
  builder.updateProps(field.id, { formula }, `formula:${field.id}`)
const insert = (field: FormField, piece: string) => setFormula(field, `${formulaOf(field).trimEnd()} ${piece}`.trimStart())
const usable = (field: FormField) => logic.formulaSources.value.filter(f => f.key !== field.key)
const isChoice = (f: FormField) => !!f.options?.length
const scored = (f: FormField) => !!f.options?.some(o => typeof o.score === 'number')
</script>

<template>
  <UCard :ui="{ header: 'flex items-center gap-2 p-3 sm:px-4', body: 'p-0 sm:p-0' }">
    <template #header>
      <h2 class="text-sm font-semibold text-highlighted">{{ t('logic.calc.title') }}</h2>
      <UBadge :label="String(logic.calculated.value.length)" color="neutral" variant="outline" size="sm" class="rounded-md" />
    </template>

    <AppEmpty
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
        <UFormField :error="logic.formulaProblem(field) ?? undefined">
          <UInput
            :model-value="formulaOf(field)"
            icon="i-lucide-equal"
            class="w-full font-mono"
            :placeholder="t('logic.calc.placeholder')"
            :aria-label="t('logic.calc.formulaFor', { field: logic.label(field) })"
            @update:model-value="v => setFormula(field, String(v))"
          />
        </UFormField>
        <div v-if="usable(field).length" class="flex flex-wrap items-center gap-1">
          <span class="me-1 text-xs text-muted">{{ t('logic.calc.use') }}</span>
          <UTooltip
            v-for="source in usable(field)"
            :key="source.id"
            :text="isChoice(source) ? (scored(source) ? t('logic.calc.choiceScored') : t('logic.calc.choiceUnscored')) : logic.label(source)"
          >
            <UButton
              :label="`{${source.key}}`"
              :icon="fieldIcon(source.type)"
              color="neutral"
              :variant="isChoice(source) && !scored(source) ? 'ghost' : 'outline'"
              size="xs"
              class="font-mono"
              @click="insert(field, `{${source.key}}`)"
            />
          </UTooltip>
        </div>
        <div class="flex flex-wrap items-center gap-1">
          <span class="me-1 text-xs text-muted">{{ t('logic.calc.functions') }}</span>
          <UButton
            v-for="fn in FUNCTIONS"
            :key="fn"
            :label="fn.split('(')[0] + '()'"
            color="neutral"
            variant="outline"
            size="xs"
            class="font-mono"
            @click="insert(field, fn)"
          />
        </div>
      </li>
    </ul>

    <details class="group border-t border-default px-3 py-2.5 text-xs text-muted sm:px-4">
      <summary class="flex cursor-pointer list-none items-center gap-1.5 font-medium text-default">
        <UIcon name="i-lucide-circle-help" class="size-3.5" />{{ t('logic.calc.guideTitle') }}
        <UIcon name="i-lucide-chevron-down" class="ms-auto size-3.5 transition-transform group-open:rotate-180" />
      </summary>
      <ul class="mt-2 flex list-disc flex-col gap-1.5 ps-4">
        <li>{{ t('logic.calc.guideMath') }}</li>
        <li>{{ t('logic.calc.guideOptions') }}</li>
        <li>{{ t('logic.calc.guideIf') }}</li>
        <li>{{ t('logic.calc.guideFunctions') }}</li>
      </ul>
    </details>
  </UCard>
</template>
