<script setup lang="ts">
// `compact`: the small trail under the page title in the header bar.
const props = defineProps<{ compact?: boolean }>()
const { t } = useI18n()
const { items } = useBreadcrumbs()

const ui = computed(() =>
  props.compact
    ? { root: 'min-w-0', link: 'text-xs font-normal', separatorIcon: 'size-3' }
    : { root: 'min-w-0' },
)
</script>

<template>
  <UBreadcrumb :items="items" :aria-label="t('navbar.breadcrumb')" :ui="ui" />
</template>
