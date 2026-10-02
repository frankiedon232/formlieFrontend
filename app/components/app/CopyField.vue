<!-- Read-only value with a copy button (share links, embed snippets, API keys). -->
<script setup lang="ts">
const props = defineProps<{ value: string; label?: string; monospace?: boolean }>()
const { t } = useI18n()
const { copy, copied } = useClipboard({ legacy: true, copiedDuring: 1500 })
</script>

<template>
  <UFormField :label="props.label">
    <UInput
      :model-value="props.value"
      readonly
      class="w-full"
      :ui="{ base: props.monospace ? 'font-mono text-xs' : '', trailing: 'pe-1' }"
      @focus="($event.target as HTMLInputElement).select()"
    >
      <template #trailing>
        <UTooltip :text="copied ? t('common.copied') : t('common.copy')">
          <UButton
            :icon="copied ? 'i-lucide-check' : 'i-lucide-copy'"
            :color="copied ? 'success' : 'neutral'"
            variant="ghost"
            size="sm"
            :aria-label="t('common.copy')"
            @click="copy(props.value)"
          />
        </UTooltip>
      </template>
    </UInput>
  </UFormField>
</template>
