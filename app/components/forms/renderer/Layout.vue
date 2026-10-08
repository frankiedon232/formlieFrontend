<!--
  Layout blocks as respondents see them (no answer collected), in the form theme's block styles
  (theme.blocks, owner 2026-10-08; the builder canvas uses the default look):
  - section: title (large / medium / small) + optional description; start or centre. Theme style:
    plain (with its divider line) · underline (short bar in the theme colour) · accent (edge bar) ·
    band (tinted strip); heading in the text or theme colour, optional small capitals, the theme's
    heading weight.
  - paragraph: rich text (HTML, shown through the read-only editor, never v-html); old plain text
    still works. Theme style: plain · muted · callout (tinted box with an edge).
  - divider: small / medium / large spacing. Theme style: line (solid / dashed / dotted as set on the
    divider) · accent · gradient · dots · space; thin or thick.
  - image: uploaded or linked picture at 25–100 % width, aligned start / centre / end, optional
    caption and a link (http / https only, opens in a new tab). "Fill" spans the field; with a height
    (small / medium / large) the picture is cropped like a banner. Theme: corners, shadow, border
    (an image set to square corners stays square).
  Slots `label` / `description` let the builder swap in inline editors.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField; mode: 'builder' | 'live' }>()
const { t } = useI18n()
const look = useBlockStyle()
const p = computed(() => (props.field.props ?? {}) as Record<string, unknown>)
const str = (key: string) => (typeof p.value[key] === 'string' ? (p.value[key] as string) : '')

const SECTION_SIZE: Record<string, string> = { lg: 'text-xl', md: 'text-lg', sm: 'text-base' }
const CAPS_SIZE: Record<string, string> = { lg: 'text-base', md: 'text-sm', sm: 'text-xs' }
const WEIGHT: Record<string, string> = { medium: 'font-medium', semibold: 'font-semibold', bold: 'font-bold' }
const SECTION_BOX: Record<string, string> = {
  plain: '',
  underline: '',
  accent: 'border-s-4 border-(--ui-primary) ps-3',
  band: 'rounded-lg bg-(--ui-primary)/8 px-4 py-3',
}
const centred = computed(() => p.value.align === 'center')
const headingClass = computed(() => [
  look.value.section_caps ? `${CAPS_SIZE[str('size') || 'lg']} uppercase tracking-wider` : SECTION_SIZE[str('size') || 'lg'],
  WEIGHT[look.value.heading_weight],
  look.value.section_color === 'primary' ? 'text-(--ui-primary)' : 'text-highlighted',
  centred.value ? 'justify-center' : '',
])
/** Plain sections keep their divider line (unless switched off on the section). */
const sectionLine = computed(() => look.value.section === 'plain' && p.value.divider !== false)

const dividerType = computed(() => (['dashed', 'dotted'].includes(str('style')) ? str('style') : 'solid') as 'solid' | 'dashed' | 'dotted')
const DIVIDER_SPACE: Record<string, string> = { sm: 'py-1', md: 'py-3', lg: 'py-6' }
const thick = computed(() => look.value.divider_weight === 'thick')

const PARAGRAPH_BOX: Record<string, string> = { plain: '', muted: 'text-muted', callout: 'rounded-lg border-s-4 border-(--ui-primary) bg-(--ui-primary)/5 px-4 py-3' }

const IMAGE_ALIGN: Record<string, string> = { start: 'items-start', center: 'items-center', end: 'items-end', fill: 'items-stretch' }
const IMAGE_RADIUS: Record<string, string> = { none: 'rounded-none', sm: 'rounded-sm', md: 'rounded-md', lg: 'rounded-xl', xl: 'rounded-3xl' }
/** "Fill" spans the field; with a height the picture is cropped to cover it, like a banner. */
const fill = computed(() => str('align') === 'fill')
const IMAGE_HEIGHT: Record<string, string> = { sm: 'h-40', md: 'h-60', lg: 'h-90' }
const banner = computed(() => (fill.value && IMAGE_HEIGHT[str('height')]) || '')
const imageWidth = computed(() => (fill.value ? '100%' : `${Math.min(100, Math.max(10, Number(p.value.size ?? 100)))}%`))
const imageClass = computed(() => [
  p.value.rounded === false ? 'rounded-none' : IMAGE_RADIUS[look.value.image_radius],
  look.value.image_shadow ? 'shadow-md' : '',
  look.value.image_border ? 'ring-1 ring-(--ui-border)' : '',
  banner.value ? `${banner.value} object-cover` : 'h-auto object-contain',
])
/** Only web links, never javascript: or data: URLs. */
const safeHref = computed(() => (/^https?:\/\//i.test(str('href')) ? str('href') : ''))
const html = computed(() => str('html'))
</script>

<template>
  <div v-if="field.type === 'section'" class="flex flex-col gap-1 pt-2" :class="centred ? 'items-center text-center' : ''">
    <div class="flex w-full flex-col gap-1" :class="[SECTION_BOX[look.section], centred ? 'items-center' : '']">
      <h2 v-if="field.label || mode === 'builder' || $slots.label" class="flex items-center gap-2" :class="headingClass">
        <slot name="label">{{ field.label || t('builder.field.section') }}</slot>
        <UIcon v-if="mode === 'builder' && p.collapsible" name="i-lucide-chevrons-up-down" class="size-4 text-muted" />
      </h2>
      <span v-if="look.section === 'underline'" class="mt-0.5 h-1 w-12 rounded-full bg-(--ui-primary)" aria-hidden="true" />
      <slot name="description">
        <p v-if="str('description')" class="text-sm whitespace-pre-line text-muted">{{ str('description') }}</p>
      </slot>
    </div>
    <USeparator v-if="sectionLine" class="mt-2 w-full" />
  </div>

  <div v-else-if="field.type === 'paragraph'" :class="PARAGRAPH_BOX[look.paragraph]">
    <FormsRendererRichView v-if="html" :html="html" />
    <p v-else-if="str('text')" class="text-sm whitespace-pre-line" :class="look.paragraph === 'muted' ? 'text-muted' : 'text-default'">{{ str('text') }}</p>
  </div>

  <div v-else-if="field.type === 'divider'" :class="DIVIDER_SPACE[str('spacing') || 'md']" :role="look.divider === 'line' || look.divider === 'accent' ? undefined : 'separator'">
    <USeparator v-if="look.divider === 'line' || look.divider === 'accent'" :type="dividerType" :size="thick ? 'sm' : 'xs'" :ui="look.divider === 'accent' ? { border: 'border-(--ui-primary)' } : undefined" />
    <div v-else-if="look.divider === 'gradient'" class="w-full rounded-full bg-linear-to-r from-transparent via-(--ui-primary) to-transparent" :class="thick ? 'h-0.5' : 'h-px'" aria-hidden="true" />
    <div v-else-if="look.divider === 'dots'" class="flex justify-center gap-2" aria-hidden="true">
      <span v-for="n in 3" :key="n" class="rounded-full bg-(--ui-primary)/60" :class="thick ? 'size-2' : 'size-1.5'" />
    </div>
  </div>

  <figure v-else-if="field.type === 'image' && str('src')" class="flex flex-col gap-1.5" :class="IMAGE_ALIGN[str('align') || 'center']">
    <component
      :is="safeHref ? 'a' : 'div'"
      :href="safeHref || undefined"
      :target="safeHref ? '_blank' : undefined"
      :rel="safeHref ? 'noopener noreferrer' : undefined"
      class="block max-w-full"
      :style="{ width: imageWidth }"
    >
      <img :src="str('src')" :alt="str('alt')" loading="lazy" class="w-full" :class="imageClass">
    </component>
    <figcaption v-if="str('caption')" class="text-xs text-muted" :style="{ width: imageWidth }">{{ str('caption') }}</figcaption>
  </figure>
</template>
