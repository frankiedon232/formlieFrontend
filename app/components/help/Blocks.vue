<!--
  An article's content (F25): paragraphs, headings (anchors for "On this page"), numbered steps, lists, tips /
  notes / warnings, "Show me" links that open the real page (and highlight the control), and the screenshots,
  GIFs and videos (with captions) the Formalie team adds. Used on the article page and in the help panel.
-->
<script setup lang="ts">
import type { HelpBlock } from '#shared/types/help'

const props = withDefaults(defineProps<{ blocks: HelpBlock[]; compact?: boolean }>(), { compact: false })
const emit = defineEmits<{ show: [] }>()
const { t } = useI18n()
const ALERT = {
  tip: { icon: 'i-lucide-lightbulb', color: 'neutral', title: 'help.block.tip' },
  note: { icon: 'i-lucide-info', color: 'neutral', title: 'help.block.note' },
  warning: { icon: 'i-lucide-triangle-alert', color: 'warning', title: 'help.block.warning' },
} as const
/** Heading anchors: stable from their position. */
const anchor = (index: number) => `section-${index}`
defineExpose({ headings: computed(() => props.blocks.flatMap((block, index) => (block.type === 'h' ? [{ id: anchor(index), text: block.text }] : []))) })
</script>

<template>
  <div class="flex flex-col" :class="compact ? 'gap-3' : 'gap-4'">
    <template v-for="(block, index) in blocks" :key="index">
      <p v-if="block.type === 'p'" class="text-sm leading-relaxed text-default"><HelpRich :text="block.text" /></p>
      <h2 v-else-if="block.type === 'h'" :id="anchor(index)" class="mt-2 scroll-mt-4 text-base font-semibold text-highlighted">{{ block.text }}</h2>
      <ol v-else-if="block.type === 'steps'" class="flex flex-col gap-2.5">
        <li v-for="(item, step) in block.items" :key="step" class="flex items-start gap-3 text-sm text-default">
          <span class="flex size-6 shrink-0 items-center justify-center rounded-full bg-inverted text-xs font-semibold text-inverted tabular-nums">{{ step + 1 }}</span>
          <span class="pt-0.5 leading-relaxed"><HelpRich :text="item" /></span>
        </li>
      </ol>
      <ul v-else-if="block.type === 'list'" class="flex flex-col gap-1.5 ps-1">
        <li v-for="(item, entry) in block.items" :key="entry" class="flex items-start gap-2 text-sm leading-relaxed text-default">
          <span class="mt-2 size-1.5 shrink-0 rounded-full bg-(--ui-text-muted)" /><HelpRich :text="item" />
        </li>
      </ul>
      <UAlert v-else-if="block.type === 'tip' || block.type === 'note' || block.type === 'warning'" :color="ALERT[block.type].color" variant="subtle" :icon="ALERT[block.type].icon" :title="t(ALERT[block.type].title)">
        <template #description><HelpRich :text="block.text" /></template>
      </UAlert>
      <div v-else-if="block.type === 'show'">
        <UButton :label="block.label" icon="i-lucide-mouse-pointer-click" color="neutral" variant="outline" size="sm" :to="block.target ? { path: block.to, query: { show: block.target } } : block.to" @click="emit('show')" />
      </div>
      <figure v-else-if="block.type === 'media'" class="flex flex-col items-center gap-2 rounded-lg border border-default bg-elevated/50 p-3 sm:p-4">
        <video v-if="block.kind === 'video'" :src="block.src" controls preload="metadata" class="w-full rounded-lg border border-default" :aria-label="block.caption">
          <track v-if="block.captions_src" kind="captions" :src="block.captions_src" default>
        </video>
        <!-- Screenshots are phone-sized pages: keep them narrow so the steps stay close; click opens the full image -->
        <a v-else :href="block.src" target="_blank" rel="noopener" class="block w-full rounded-md focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" :class="compact ? 'max-w-56' : 'max-w-xs'">
          <img :src="block.src" :alt="block.caption" loading="lazy" class="w-full rounded-md border border-default shadow-sm">
        </a>
        <figcaption class="text-center text-xs text-muted">{{ block.caption }}</figcaption>
      </figure>
    </template>
  </div>
</template>
