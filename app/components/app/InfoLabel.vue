<!--
  A field label with an info button: the explanation opens on click (or Enter / Space) instead of
  taking room under the field. Use in a UFormField #label slot.
-->
<script setup lang="ts">
defineProps<{ label: string; info: string }>()
const { t } = useI18n()
</script>

<template>
  <span class="inline-flex items-center gap-1">
    {{ label }}
    <UPopover :content="{ side: 'top', align: 'start' }" arrow>
      <UButton
        icon="i-lucide-info"
        color="neutral"
        variant="link"
        size="xs"
        class="p-0.5 text-muted"
        :aria-label="t('renderer.moreInfo', { field: label })"
        @click.stop.prevent
      />
      <template #content>
        <p class="max-w-72 p-3 text-xs text-default">{{ info }}</p>
      </template>
    </UPopover>
  </span>
</template>
