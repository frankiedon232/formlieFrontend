<!-- What making a list large means (F15 M5), shown before anyone chooses it: in Size and in the import. -->
<script setup lang="ts">
import { MAX_LARGE_OPTIONS } from '#shared/utils/forms/options'

const { t } = useI18n()
const { number } = useFormat()
const points = computed(() => [
  { icon: 'i-lucide-server', text: t('optionSets.large.point.server', { max: number(MAX_LARGE_OPTIONS) }) },
  { icon: 'i-lucide-list-tree', text: t('optionSets.large.point.levels') },
  { icon: 'i-lucide-search', text: t('optionSets.large.point.search') },
  { icon: 'i-lucide-refresh-ccw', text: t('optionSets.large.point.live') },
  { icon: 'i-lucide-list-checks', text: t('optionSets.large.point.dropdown') },
  { icon: 'i-lucide-wifi', text: t('optionSets.large.point.online') },
])
</script>

<template>
  <ul class="flex flex-col gap-3">
    <li v-for="point in points" :key="point.icon" class="flex items-start gap-3 text-sm">
      <span class="flex size-7 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="point.icon" class="size-4 text-highlighted" /></span>
      <span class="pt-1 text-default">{{ point.text }}</span>
    </li>
  </ul>
</template>
