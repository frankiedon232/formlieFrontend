<!-- Layout blocks: section heading (+ description), paragraph, divider, image. No answer collected. -->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField; mode: 'builder' | 'live' }>()
const { t } = useI18n()
const p = computed(() => (props.field.props ?? {}) as Record<string, string | undefined>)
</script>

<template>
  <div v-if="field.type === 'section'" class="flex flex-col gap-1 pt-2">
    <h2 class="flex items-center gap-2 text-lg font-semibold text-highlighted">
      {{ field.label || t('builder.field.section') }}
      <UIcon v-if="mode === 'builder' && p.collapsible" name="i-lucide-chevrons-up-down" class="size-4 text-muted" />
    </h2>
    <p v-if="p.description" class="text-sm text-muted">{{ p.description }}</p>
  </div>
  <p v-else-if="field.type === 'paragraph'" class="text-sm whitespace-pre-line text-default">
    {{ p.text || (mode === 'builder' ? t('builder.paragraphEmpty') : '') }}
  </p>
  <USeparator v-else-if="field.type === 'divider'" class="py-2" />
  <figure v-else-if="field.type === 'image'" class="flex flex-col gap-1">
    <img v-if="p.src" :src="p.src" :alt="p.alt ?? ''" class="max-h-80 w-full rounded-md object-contain" >
    <div
      v-else-if="mode === 'builder'"
      class="flex h-32 items-center justify-center gap-2 rounded-md border border-dashed border-default text-sm text-muted"
    >
      <UIcon name="i-lucide-image" class="size-5" /> {{ t('builder.imageEmpty') }}
    </div>
    <figcaption v-if="p.alt && p.src" class="text-xs text-muted">{{ p.alt }}</figcaption>
  </figure>
</template>
