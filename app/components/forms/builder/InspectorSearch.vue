<!--
  Field settings → Search as you type (F15 M3) for dropdowns and multi-selects: on by itself for more
  than SEARCH_FROM options, or set by hand (`props.search`). Very long lists always search on the public
  page, where their options come from the server.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'
import { REMOTE_FROM, SEARCH_FROM, searchesAsYouType } from '#shared/utils/forms/options'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()

const on = computed(() => searchesAsYouType(props.field))
const set = (value: boolean) => builder.updateProps(props.field.id, { search: value })
const hint = computed(() => ((props.field.options?.length ?? 0) > REMOTE_FROM ? t('builder.inspector.searchServer', { n: REMOTE_FROM }) : t('builder.inspector.searchHint', { n: SEARCH_FROM })))
</script>

<template>
  <USwitch v-if="field.type === 'dropdown' || field.type === 'multi_select'" :model-value="on" :label="t('builder.inspector.search')" :description="hint" color="neutral" @update:model-value="value => set(!!value)" />
</template>
