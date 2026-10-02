<!-- Status badge · "Changes not published" · saving icon + "Saved just now" (header and full-screen bar). -->
<script setup lang="ts">
const props = defineProps<{ session: BuilderSession }>()
const { t } = useI18n()
const { form, autosave } = props.session

const icon = computed(() =>
  autosave.state.value === 'saving' || autosave.state.value === 'pending'
    ? 'i-lucide-loader-circle'
    : autosave.state.value === 'error' || autosave.state.value === 'conflict'
      ? 'i-lucide-cloud-alert'
      : 'i-lucide-cloud-check',
)
</script>

<template>
  <span v-if="form" class="flex min-w-0 items-center gap-1.5 text-xs text-muted" aria-live="polite">
    <DataStatusBadge :status="form.status" />
    <UBadge
      v-if="form.has_unpublished_changes"
      :label="t('builder.unpublished')"
      color="warning"
      variant="subtle"
      size="sm"
      class="hidden rounded-md sm:inline-flex"
    />
    <UIcon
      :name="icon"
      class="size-3.5 shrink-0"
      :class="[
        autosave.state.value === 'saving' || autosave.state.value === 'pending' ? 'animate-spin' : '',
        autosave.state.value === 'error' || autosave.state.value === 'conflict' ? 'text-warning' : '',
      ]"
    />
    <span class="truncate">{{ session.statusText.value }}</span>
  </span>
</template>
