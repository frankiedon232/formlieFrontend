<!--
  Inspector for a level of a list with levels (F15 M2): where it sits (Country → Region → City, this
  one highlighted), what it filters by, one or several choices, and a way to refresh the options from
  the list. Its options come from the list (edited in List Option), so there is no options editor here.
-->
<script setup lang="ts">
import { allFields, type FormField } from '#shared/utils/forms/build'
import { cascadeChain } from '#shared/utils/forms/cascade'
import { matchesList, offeredOptions } from '#shared/utils/forms/options'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()
const library = useFieldLibrary()
onMounted(() => library.load())

const chain = computed(() => (builder.schema.value ? cascadeChain(props.field, allFields(builder.schema.value)) : [props.field]))
const parent = computed(() => chain.value.find(item => item.id === props.field.option_parent) ?? null)
const list = computed(() => library.lists.value.find(item => item.id === props.field.option_set_id) ?? null)
const changed = computed(() => !!list.value && !matchesList(props.field.options, list.value, props.field.option_level ?? 0))
const several = computed(() => props.field.type === 'multi_select')
const setSeveral = (on: boolean) => builder.updateField(props.field.id, { type: on ? 'multi_select' : 'dropdown' })
/** The whole chain takes the list as it is now. */
function refresh() {
  if (!list.value) return
  for (const item of chain.value) builder.updateField(item.id, { options: offeredOptions(toRaw(list.value), item.option_level ?? 0) })
}
</script>

<template>
  <section class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.level.title') }}</h3>
    <ol class="flex flex-wrap items-center gap-1 text-xs" :aria-label="t('builder.level.chain')">
      <template v-for="(item, index) in chain" :key="item.id">
        <li>
          <button type="button" class="rounded-md px-1.5 py-0.5 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" :class="item.id === field.id ? 'bg-inverted font-medium text-inverted' : 'bg-elevated text-default hover:text-highlighted'" :aria-current="item.id === field.id ? 'true' : undefined" @click="builder.select(item.id)">{{ item.label || t('builder.untitled') }}</button>
        </li>
        <li v-if="index < chain.length - 1" aria-hidden="true"><UIcon name="i-lucide-chevron-right" class="size-3 text-muted rtl:rotate-180" /></li>
      </template>
    </ol>
    <p class="text-xs text-muted">
      {{ parent ? t('builder.level.filtered', { n: (field.option_level ?? 0) + 1, total: chain.length, parent: parent.label || t('builder.untitled') }) : t('builder.level.top', { total: chain.length }) }}
      {{ t('builder.level.fromList', { name: list?.name ?? t('builder.level.deletedList') }) }}
    </p>
    <USwitch :model-value="several" :label="t('builder.level.several')" :description="t('builder.level.severalHint')" color="neutral" @update:model-value="value => setSeveral(!!value)" />
    <UAlert v-if="changed && list" color="warning" variant="subtle" icon="i-lucide-refresh-ccw" :title="t('library.listChanged', { name: list.name })" :actions="[{ label: t('library.updateFromList'), color: 'neutral', variant: 'outline', size: 'xs', onClick: refresh }]" :ui="{ title: 'text-xs' }" />
    <UButton :label="t('builder.level.editList')" icon="i-lucide-external-link" color="neutral" variant="link" size="xs" class="w-fit px-0" :to="list ? `/option-sets/${list.id}` : undefined" :disabled="!list" target="_blank" />
    <FormsBuilderInspectorSearch :field="field" />
  </section>
</template>
