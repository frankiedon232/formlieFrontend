<!--
  Dropdown, multi-select, radio, checkboxes and toggle. Options come from the field; a level of a list
  with levels shows only what is under the choice above (F15 M2). Long lists (F15 M3): a dropdown or
  multi-select with many options searches as you type (a search box, long lists drawn as they scroll);
  on the public page a very long list asks the server for matches (useRemoteOptions).
-->
<script setup lang="ts">
import { isLocked, type FormField } from '#shared/utils/forms/build'
import { cascadeOptions } from '#shared/utils/forms/cascade'
import { searchesAsYouType } from '#shared/utils/forms/options'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()
const { number } = useFormat()
// Size and style follow the form theme (F8); plain defaults elsewhere.
const control = useControlStyle()

// A level of a list with levels offers only what sits under the choice above (F15 M2)
// (the form hides a level with nothing to offer; the builder canvas keeps it, locked, saying what to choose first)
const live = inject(RENDERER_ANSWERS, null)
const cascading = computed(() => !!live && !!props.field.option_parent)
const own = computed(() =>
  (cascading.value ? cascadeOptions(props.field, live!.fieldsById.value, live!.answers.value) : (props.field.options ?? [])).map(option => ({ value: option.value, label: option.label })),
)
const one = computed({
  get: () => (typeof value.value === 'string' ? value.value : undefined),
  set: next => (value.value = next),
})
const many = computed({
  get: () => (Array.isArray(value.value) ? (value.value as string[]) : []),
  set: next => (value.value = next),
})
const on = computed({
  get: () => value.value === true,
  set: next => (value.value = next),
})

// Long lists: a search box; options from the server when the page left them out
const searching = computed(() => searchesAsYouType(props.field))
const server = useRemoteOptions(() => props.field, () => (one.value ? [one.value] : many.value))
const items = computed(() => (server.remote.value ? server.items.value : own.value))
const searchInput = computed(() => (searching.value ? { placeholder: t('renderer.typeToSearch'), icon: 'i-lucide-search' } : false))
const more = computed(() => (server.remote.value && server.total.value > server.items.value.length ? t('renderer.moreMatches', { shown: number(server.items.value.length), total: number(server.total.value) }) : ''))

const closed = computed(() => cascading.value && !own.value.length)
const above = computed(() => (props.field.option_parent ? live?.fieldsById.value.get(props.field.option_parent)?.label : '') || t('builder.untitled'))
const placeholder = (fallback: string) => (closed.value ? t('renderer.chooseAboveFirst', { name: above.value }) : props.field.placeholder || (searching.value ? t('renderer.typeToSearch') : fallback))
const icon = useFieldIcon(() => props.field)
// Read-only and disabled both block changes here (Nuxt UI choice controls have no read-only state).
const disabled = computed(() => isLocked(props.field) || closed.value)
</script>

<template>
  <USelect
    v-if="field.type === 'dropdown' && !searching"
    v-bind="control"
    :id="id"
    v-model="one"
    :items="items"
    value-key="value"
    :placeholder="placeholder(t('renderer.choose'))"
    :icon="icon"
    :disabled="disabled"
    class="w-full"
  />
  <USelectMenu
    v-else-if="field.type === 'dropdown' || field.type === 'multi_select'"
    v-bind="control"
    :id="id"
    v-model:search-term="server.term.value"
    :model-value="field.type === 'multi_select' ? many : one"
    :items="items"
    value-key="value"
    :multiple="field.type === 'multi_select'"
    :search-input="searchInput"
    :ignore-filter="server.remote.value"
    :loading="server.loading.value"
    :virtualize="items.length > 100"
    :placeholder="placeholder(field.type === 'multi_select' ? t('renderer.chooseMany') : t('renderer.choose'))"
    :icon="icon"
    :disabled="disabled"
    class="w-full"
    @update:model-value="(next: unknown) => (value = next)"
  >
    <template v-if="more || server.failed.value" #content-bottom>
      <p class="border-t border-default px-3 py-2 text-xs text-muted">
        <template v-if="server.failed.value">{{ t('renderer.searchFailed') }} <button type="button" class="underline" @click="server.retry()">{{ t('common.retry') }}</button></template>
        <template v-else>{{ more }}</template>
      </p>
    </template>
  </USelectMenu>
  <URadioGroup
    v-else-if="field.type === 'radio'"
    :id="id"
    v-model="one"
    :items="items"
    color="neutral"
    :disabled="disabled"
    :ui="{ fieldset: 'gap-2' }"
  />
  <UCheckboxGroup
    v-else-if="field.type === 'checkbox'"
    :id="id"
    v-model="many"
    :items="items"
    color="neutral"
    :disabled="disabled"
    :ui="{ fieldset: 'gap-2' }"
  />
  <USwitch
    v-else
    :id="id"
    v-model="on"
    color="neutral"
    :disabled="disabled"
    :aria-label="field.label"
  />
</template>
