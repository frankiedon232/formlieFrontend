<!--
  Field settings for a field from a large list (F15 M5): its options stay on the server, so there is no
  options editor; it says how many there are, that they load as people type, and links to the list.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField; withLink?: boolean }>()
const { t } = useI18n()
const { number } = useFormat()
const total = computed(() => props.field.options_large?.total ?? 0)
</script>

<template>
  <div class="flex flex-col gap-2">
    <UAlert color="neutral" variant="subtle" icon="i-lucide-server" :title="t('builder.large.title', { count: number(total) }, total)" :description="t('builder.large.desc')" :ui="{ title: 'text-xs', description: 'text-xs' }" />
    <UButton v-if="withLink && field.option_set_id" :label="t('builder.level.editList')" icon="i-lucide-external-link" color="neutral" variant="link" size="xs" class="w-fit px-0" :to="`/option-sets/${field.option_set_id}`" target="_blank" />
  </div>
</template>
