<!--
  Rich text answer — Nuxt UI editor (UEditor + UEditorToolbar, TipTap inside). The answer is
  stored as Markdown (safe to show again, readable in exports). Toolbar: "basic" (marks, lists,
  quote, link, undo) or "full" (+ headings, alignment, code). Read-only / disabled hide the toolbar
  and stop editing. Max length counts the Markdown text.
-->
<script setup lang="ts">
import type { EditorToolbarItem } from '@nuxt/ui'
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()

const locked = computed(() => !!props.field.readonly || !!props.field.disabled)
const full = computed(() => props.field.props?.toolbar === 'full')
const max = computed(() => (props.field.validation?.max_length as number | undefined) ?? undefined)

const text = computed({
  get: () => (typeof value.value === 'string' ? value.value : ''),
  set: next => (value.value = next.trim() ? next : ''),
})
const tooLong = computed(() => !!max.value && text.value.length > max.value)

const items = computed<EditorToolbarItem[][]>(() => [
  ...(full.value
    ? [[
        { kind: 'heading', level: 2, icon: 'i-lucide-heading-2', tooltip: { text: t('renderer.rich.heading') } },
        { kind: 'heading', level: 3, icon: 'i-lucide-heading-3', tooltip: { text: t('renderer.rich.subheading') } },
      ] as EditorToolbarItem[]]
    : []),
  [
    { kind: 'mark', mark: 'bold', icon: 'i-lucide-bold', tooltip: { text: t('renderer.rich.bold') } },
    { kind: 'mark', mark: 'italic', icon: 'i-lucide-italic', tooltip: { text: t('renderer.rich.italic') } },
    { kind: 'mark', mark: 'underline', icon: 'i-lucide-underline', tooltip: { text: t('renderer.rich.underline') } },
    { kind: 'mark', mark: 'strike', icon: 'i-lucide-strikethrough', tooltip: { text: t('renderer.rich.strike') } },
  ],
  [
    { kind: 'bulletList', icon: 'i-lucide-list', tooltip: { text: t('renderer.rich.bullets') } },
    { kind: 'orderedList', icon: 'i-lucide-list-ordered', tooltip: { text: t('renderer.rich.numbers') } },
    { kind: 'blockquote', icon: 'i-lucide-text-quote', tooltip: { text: t('renderer.rich.quote') } },
    { kind: 'link', icon: 'i-lucide-link', tooltip: { text: t('renderer.rich.link') } },
  ],
  ...(full.value
    ? [[
        { kind: 'textAlign', align: 'left', icon: 'i-lucide-align-left', tooltip: { text: t('renderer.rich.alignStart') } },
        { kind: 'textAlign', align: 'center', icon: 'i-lucide-align-center', tooltip: { text: t('renderer.rich.alignCenter') } },
        { kind: 'mark', mark: 'code', icon: 'i-lucide-code', tooltip: { text: t('renderer.rich.code') } },
      ] as EditorToolbarItem[]]
    : []),
  [
    { kind: 'clearFormatting', icon: 'i-lucide-remove-formatting', tooltip: { text: t('renderer.rich.clear') } },
    { kind: 'undo', icon: 'i-lucide-undo-2', tooltip: { text: t('builder.undo') } },
    { kind: 'redo', icon: 'i-lucide-redo-2', tooltip: { text: t('builder.redo') } },
  ],
])
</script>

<template>
  <div
    :id="id"
    class="overflow-hidden rounded-md border bg-default"
    :class="[tooLong ? 'border-error' : 'border-accented', field.disabled ? 'opacity-75' : '']"
    role="group"
    :aria-label="field.label"
  >
    <UEditor
      v-slot="{ editor }"
      v-model="text"
      content-type="markdown"
      :editable="!locked"
      :placeholder="field.placeholder || t('renderer.rich.placeholder')"
      :image="false"
      :mention="false"
      :ui="{ base: 'min-h-28 px-3 py-2 text-sm leading-5 *:my-0.5 sm:px-3 [&_p]:leading-5 [&_li]:leading-5' }"
      class="w-full"
    >
      <UEditorToolbar
        v-if="!locked"
        :editor="editor"
        :items="items"
        layout="fixed"
        :ui="{ root: 'border-b border-default bg-elevated/40 px-1 py-1', base: 'flex-wrap gap-1' }"
      />
    </UEditor>
    <p v-if="max" class="border-t border-default px-3 py-1 text-end text-xs" :class="tooLong ? 'text-error' : 'text-muted'">
      {{ t('renderer.rich.count', { n: text.length, max }) }}
    </p>
  </div>
</template>
