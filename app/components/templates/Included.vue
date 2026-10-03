<!--
  Template page side panel (F9): what's in the template (pages, questions, logic, calculations,
  time), each calculation with its formula and whether respondents see the result, the design,
  and how often the workspace used it.
-->
<script setup lang="ts">
import type { TemplateDetail } from '#shared/types/templates'

const props = defineProps<{ template: TemplateDetail }>()
const { t } = useI18n()
const { number, relative } = useFormat()

const facts = computed(() => [
  { icon: 'i-lucide-files', label: t('templates.facts.pages', { count: props.template.pages_count }, props.template.pages_count) },
  { icon: 'i-lucide-list', label: t('templates.questions', { count: props.template.fields_count }, props.template.fields_count) },
  { icon: 'i-lucide-git-branch', label: t('templates.facts.logic', { count: props.template.logic_count }, props.template.logic_count) },
  { icon: 'i-lucide-calculator', label: t('templates.facts.calculations', { count: props.template.calculations_count }, props.template.calculations_count) },
  { icon: 'i-lucide-timer', label: t('templates.minutes', { n: props.template.minutes }) },
])
const usage = computed(() => [
  { label: t('templates.stats.forms'), value: number(props.template.forms_count) },
  { label: t('templates.stats.responses'), value: number(props.template.responses_count) },
  { label: t('templates.stats.lastUsed'), value: props.template.last_used_at ? relative(props.template.last_used_at) : t('templates.neverUsed') },
])
</script>

<template>
  <aside class="flex min-w-0 flex-col gap-3">
    <UCard variant="outline" :ui="{ body: 'p-4 sm:p-4' }">
      <h2 class="mb-3 text-xs font-medium text-muted uppercase">{{ t('templates.included') }}</h2>
      <ul class="flex flex-col gap-2">
        <li v-for="fact in facts" :key="fact.icon" class="flex items-center gap-2 text-sm text-default">
          <UIcon :name="fact.icon" class="size-4 shrink-0 text-muted" />
          {{ fact.label }}
        </li>
      </ul>
    </UCard>

    <UCard v-if="template.calculations.length" variant="outline" :ui="{ body: 'p-4 sm:p-4' }">
      <h2 class="mb-3 text-xs font-medium text-muted uppercase">{{ t('templates.calculationsTitle') }}</h2>
      <ul class="flex flex-col gap-3">
        <li v-for="calc in template.calculations" :key="calc.label" class="flex flex-col gap-1">
          <span class="flex flex-wrap items-center gap-1.5 text-sm font-medium text-highlighted">
            {{ calc.label }}
            <UBadge v-if="calc.internal" :label="t('templates.teamOnly')" icon="i-lucide-eye-off" color="neutral" variant="soft" size="sm" />
          </span>
          <code class="block overflow-x-auto rounded-md bg-elevated px-2 py-1 font-mono text-xs text-muted">{{ calc.formula }}</code>
        </li>
      </ul>
    </UCard>

    <UCard variant="outline" :ui="{ body: 'p-4 sm:p-4' }">
      <h2 class="mb-3 text-xs font-medium text-muted uppercase">{{ t('templates.usage') }}</h2>
      <dl class="grid grid-cols-3 gap-2 lg:grid-cols-1 xl:grid-cols-3">
        <div v-for="item in usage" :key="item.label" class="flex min-w-0 flex-col">
          <dt class="truncate text-xs text-muted">{{ item.label }}</dt>
          <dd class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ item.value }}</dd>
        </div>
      </dl>
    </UCard>

    <p class="flex items-start gap-2 px-1 text-xs text-muted">
      <UIcon name="i-lucide-pencil-ruler" class="mt-0.5 size-3.5 shrink-0" />
      {{ t('templates.editableHint') }}
    </p>
  </aside>
</template>
