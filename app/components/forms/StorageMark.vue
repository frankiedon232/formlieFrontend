<!--
  Where a form's responses are kept, shown after its folder in the form and response lists (owner
  2026-10-05): a thin divider, then the engine's own logo (PostgreSQL, MySQL, …) when they are
  stored on a connection. Formalie's own storage (the default) shows nothing. Drawn in the text
  colour so it reads clearly in both themes; the tooltip names the connection.
-->
<script setup lang="ts">
import type { StorageMark } from '#shared/types/destinations'

const props = defineProps<{ storage?: StorageMark | null; size?: 'xs' | 'sm' }>()
const { t } = useI18n()
const label = computed(() => t('destinations.mark.database', { name: props.storage?.datasource ?? '' }))
const icon = computed(() => (props.storage?.engine ? engineIcon(props.storage.engine) : 'i-lucide-database'))
</script>

<template>
  <span v-if="storage?.mode === 'database'" class="inline-flex shrink-0 items-center gap-1.5">
    <span class="h-3 w-px shrink-0 bg-(--ui-border-accented)" aria-hidden="true" />
    <UTooltip :text="label">
      <UIcon :name="icon" class="shrink-0 text-highlighted" :class="size === 'xs' ? 'size-3.5' : 'size-4'" role="img" :aria-label="label" />
    </UTooltip>
  </span>
</template>
