<!--
  Where a form's responses are kept, shown after its folder in the form and response lists (owner
  2026-10-05): a thin divider, then a database icon (stored on a connection) or the Formalie mark
  (Formalie's encrypted storage). The tooltip names the connection.
-->
<script setup lang="ts">
import type { StorageMark } from '#shared/types/destinations'

const props = defineProps<{ storage?: StorageMark | null; size?: 'xs' | 'sm' }>()
const { t } = useI18n()
const label = computed(() => (props.storage?.mode === 'database' ? t('destinations.mark.database', { name: props.storage.datasource ?? '' }) : t('destinations.mark.formalie')))
</script>

<template>
  <span v-if="storage" class="inline-flex shrink-0 items-center gap-1.5">
    <span class="h-3 w-px shrink-0 bg-(--ui-border-accented)" aria-hidden="true" />
    <UTooltip :text="label">
      <UIcon v-if="storage.mode === 'database'" name="i-lucide-database" :class="size === 'xs' ? 'size-3' : 'size-3.5'" class="shrink-0 text-highlighted" role="img" :aria-label="label" />
      <span v-else class="inline-flex shrink-0 items-center justify-center rounded-[3px] bg-inverted text-inverted" :class="size === 'xs' ? 'size-3' : 'size-3.5'" role="img" :aria-label="label">
        <UIcon name="i-lucide-file-check-2" :class="size === 'xs' ? 'size-2' : 'size-2.5'" />
      </span>
    </UTooltip>
  </span>
</template>
