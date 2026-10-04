<!--
  Template page side panel (F9): what's in the template as tiles, each calculation as a code
  snippet (team-only results marked), and usage with the latest forms made from it.
-->
<script setup lang="ts">
import type { TemplateDetail } from '#shared/types/templates'
import { allFields } from '#shared/utils/forms/build'

const props = defineProps<{ template: TemplateDetail }>()
const emit = defineEmits<{ use: [] }>()
const { t } = useI18n()

const tiles = computed(() => [
  { icon: 'i-lucide-files', value: props.template.pages_count, label: t('templates.facts.pagesLabel') },
  { icon: 'i-lucide-list', value: props.template.fields_count, label: t('templates.col.questions') },
  { icon: 'i-lucide-git-branch', value: props.template.logic_count, label: t('templates.badge.logic') },
  {
    icon: 'i-lucide-calculator',
    value: props.template.calculations_count,
    label: t('templates.badge.calculations'),
  },
])
/** Field key → question label, so formula references explain themselves on hover. */
const labels = computed(() =>
  Object.fromEntries(allFields(props.template.schema).map(field => [field.key, field.label])),
)
</script>

<template>
  <aside class="flex min-w-0 flex-col gap-3">
    <section
      class="flex flex-col gap-3 rounded-lg border border-default p-4"
      :aria-label="t('templates.included')"
    >
      <div class="flex items-center justify-between gap-2">
        <h2 class="text-xs font-medium text-muted uppercase">{{ t('templates.included') }}</h2>
        <UBadge
          :label="t('templates.minutes', { n: template.minutes })"
          icon="i-lucide-timer"
          color="neutral"
          variant="soft"
          size="sm"
        />
      </div>
      <div class="grid grid-cols-2 gap-2">
        <div
          v-for="tile in tiles"
          :key="tile.icon"
          class="flex items-center gap-2.5 rounded-md bg-elevated/60 p-2.5"
        >
          <span
            class="flex size-8 shrink-0 items-center justify-center rounded-md border border-default bg-default"
          >
            <UIcon :name="tile.icon" class="size-4 text-highlighted" />
          </span>
          <span class="flex min-w-0 flex-col">
            <span class="text-base leading-tight font-semibold text-highlighted tabular-nums">{{
              tile.value
            }}</span>
            <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
          </span>
        </div>
      </div>
    </section>

    <section
      v-if="template.calculations.length"
      class="flex flex-col gap-2 rounded-lg border border-default p-4"
      :aria-label="t('templates.calculationsTitle')"
    >
      <h2 class="text-xs font-medium text-muted uppercase">{{ t('templates.calculationsTitle') }}</h2>
      <TemplatesFormula
        v-for="calc in template.calculations"
        :key="calc.label + calc.formula"
        :label="calc.label"
        :formula="calc.formula"
        :internal="calc.internal"
        :fields="labels"
      />
    </section>

    <TemplatesFormsFrom :template="template" @use="emit('use')" />

    <p class="flex items-start gap-2 px-1 text-xs text-muted">
      <UIcon name="i-lucide-pencil-ruler" class="mt-0.5 size-3.5 shrink-0" />
      {{ t('templates.editableHint') }}
    </p>
  </aside>
</template>
