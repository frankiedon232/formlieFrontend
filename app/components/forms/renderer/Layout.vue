<!--
  Layout blocks as respondents see them (no answer collected):
  - section: title (large / medium / small) + optional description + divider line; start or centre.
  - paragraph: rich text (HTML, shown through the read-only editor — never v-html); old plain text still works.
  - divider: solid / dashed / dotted line with small / medium / large spacing.
  - image: uploaded or linked picture at 25–100 % width, aligned start / centre / end, optional
    caption, rounded corners and a link (http / https only, opens in a new tab).
  Slots `label` / `description` let the builder swap in inline editors.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField; mode: 'builder' | 'live' }>()
const { t } = useI18n()
const p = computed(() => (props.field.props ?? {}) as Record<string, unknown>)
const str = (key: string) => (typeof p.value[key] === 'string' ? (p.value[key] as string) : '')

const SECTION_SIZE: Record<string, string> = { lg: 'text-xl', md: 'text-lg', sm: 'text-base' }
const centred = computed(() => p.value.align === 'center')
const dividerType = computed(() => (['dashed', 'dotted'].includes(str('style')) ? str('style') : 'solid') as 'solid' | 'dashed' | 'dotted')
const DIVIDER_SPACE: Record<string, string> = { sm: 'py-1', md: 'py-3', lg: 'py-6' }
const IMAGE_ALIGN: Record<string, string> = { start: 'items-start', center: 'items-center', end: 'items-end' }
const imageWidth = computed(() => `${Math.min(100, Math.max(10, Number(p.value.size ?? 100)))}%`)
/** Only web links — never javascript: or data: URLs. */
const safeHref = computed(() => (/^https?:\/\//i.test(str('href')) ? str('href') : ''))
const html = computed(() => str('html'))
</script>

<template>
  <div v-if="field.type === 'section'" class="flex flex-col gap-1 pt-2" :class="centred ? 'items-center text-center' : ''">
    <h2
      v-if="field.label || mode === 'builder' || $slots.label"
      class="flex items-center gap-2 font-semibold text-highlighted"
      :class="[SECTION_SIZE[str('size') || 'lg'], centred ? 'justify-center' : '']"
    >
      <slot name="label">{{ field.label || t('builder.field.section') }}</slot>
      <UIcon v-if="mode === 'builder' && p.collapsible" name="i-lucide-chevrons-up-down" class="size-4 text-muted" />
    </h2>
    <slot name="description">
      <p v-if="str('description')" class="text-sm whitespace-pre-line text-muted">{{ str('description') }}</p>
    </slot>
    <USeparator v-if="p.divider !== false" class="mt-2 w-full" />
  </div>

  <div v-else-if="field.type === 'paragraph'">
    <FormsRendererRichView v-if="html" :html="html" />
    <p v-else-if="str('text')" class="text-sm whitespace-pre-line text-default">{{ str('text') }}</p>
  </div>

  <USeparator
    v-else-if="field.type === 'divider'"
    :type="dividerType"
    :class="DIVIDER_SPACE[str('spacing') || 'md']"
  />

  <figure v-else-if="field.type === 'image' && str('src')" class="flex flex-col gap-1.5" :class="IMAGE_ALIGN[str('align') || 'center']">
    <component
      :is="safeHref ? 'a' : 'div'"
      :href="safeHref || undefined"
      :target="safeHref ? '_blank' : undefined"
      :rel="safeHref ? 'noopener noreferrer' : undefined"
      class="block max-w-full"
      :style="{ width: imageWidth }"
    >
      <img
        :src="str('src')"
        :alt="str('alt')"
        loading="lazy"
        class="h-auto w-full object-contain"
        :class="p.rounded === false ? '' : 'rounded-md'"
      >
    </component>
    <figcaption v-if="str('caption')" class="text-xs text-muted" :style="{ width: imageWidth }">{{ str('caption') }}</figcaption>
  </figure>
</template>
