<!--
  Paragraph block on the canvas: edit the text in place (Nuxt UI editor). Select text for a small
  bubble toolbar — bold, italic, underline, link, lists, alignment. Saved as HTML (props.html),
  one undo step per typing burst. Old plain-text paragraphs are converted on first edit.
-->
<script setup lang="ts">
import type { EditorToolbarItem } from '@nuxt/ui'
import TextAlign from '@tiptap/extension-text-align'
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()
const extensions = [TextAlign.configure({ types: ['heading', 'paragraph'] })]

const escape = (text: string) => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const html = computed({
  get: () => {
    const p = props.field.props ?? {}
    if (typeof p.html === 'string' && p.html) return p.html
    const legacy = typeof p.text === 'string' ? p.text : ''
    return legacy ? legacy.split(/\n{2,}/).map(part => `<p>${escape(part).replace(/\n/g, '<br>')}</p>`).join('') : ''
  },
  set: next => {
    const empty = !next.replace(/<[^>]*>/g, '').trim()
    builder.updateProps(props.field.id, { html: empty ? '' : next, text: undefined }, `paragraph:${props.field.id}`)
  },
})

const items = computed<EditorToolbarItem[][]>(() => [
  [
    { kind: 'mark', mark: 'bold', icon: 'i-lucide-bold', tooltip: { text: t('renderer.rich.bold') } },
    { kind: 'mark', mark: 'italic', icon: 'i-lucide-italic', tooltip: { text: t('renderer.rich.italic') } },
    { kind: 'mark', mark: 'underline', icon: 'i-lucide-underline', tooltip: { text: t('renderer.rich.underline') } },
    { kind: 'link', icon: 'i-lucide-link', tooltip: { text: t('renderer.rich.link') } },
  ],
  [
    { kind: 'bulletList', icon: 'i-lucide-list', tooltip: { text: t('renderer.rich.bullets') } },
    { kind: 'orderedList', icon: 'i-lucide-list-ordered', tooltip: { text: t('renderer.rich.numbers') } },
  ],
  [
    { kind: 'textAlign', align: 'left', icon: 'i-lucide-align-left', tooltip: { text: t('renderer.rich.alignLeft') } },
    { kind: 'textAlign', align: 'center', icon: 'i-lucide-align-center', tooltip: { text: t('renderer.rich.alignCenter') } },
    { kind: 'textAlign', align: 'right', icon: 'i-lucide-align-right', tooltip: { text: t('renderer.rich.alignRight') } },
  ],
])
</script>

<template>
  <UEditor
    v-slot="{ editor }"
    v-model="html"
    content-type="html"
    :extensions="extensions"
    :image="false"
    :mention="false"
    :placeholder="{ placeholder: t('builder.blocks.paragraphPlaceholder'), mode: 'firstLine' }"
    :ui="{ base: `${RICH_TEXT_BASE} min-h-6 cursor-text` }"
    class="w-full"
    :aria-label="t('builder.field.paragraph')"
  >
    <UEditorToolbar
      :editor="editor"
      :items="items"
      layout="bubble"
      :ui="{ base: 'gap-0.5 shadow-md' }"
    />
  </UEditor>
</template>
