<!--
  Rich text answer, Nuxt UI editor (UEditor + UEditorToolbar, TipTap inside, plus the TipTap
  text-align extension). The answer is HTML (Markdown can't keep alignment); the server sanitises
  it on submit and wherever it is shown again. Toolbar: "basic" (marks, lists, quote, link, undo)
  or "full" (+ paragraph / heading 1–6 menu, inline code, code block, alignment). Read-only / disabled hide the toolbar
  and stop editing. Max length counts the visible text, not the HTML.
-->
<script setup lang="ts">
import type { EditorToolbarItem } from '@nuxt/ui'
import TextAlign from '@tiptap/extension-text-align'
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()

const locked = computed(() => !!props.field.readonly || !!props.field.disabled)
const full = computed(() => props.field.props?.toolbar !== 'basic')
const max = computed(() => (props.field.validation?.max_length as number | undefined) ?? undefined)

// Alignment works on headings and paragraphs (left / centre / right / justify).
const extensions = [TextAlign.configure({ types: ['heading', 'paragraph'] })]

/** The answer is HTML (alignment can't be kept in Markdown); empty editors store ''. */
const html = computed({
  get: () => (typeof value.value === 'string' ? value.value : ''),
  set: next => (value.value = plain(next).trim() ? next : ''),
})
/** Visible text only, what "max characters" counts. */
function plain(source: string) {
  return source.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').replace(/&[a-z]+;|&#\d+;/gi, 'x')
}
const length = computed(() => plain(html.value).length)
const tooLong = computed(() => !!max.value && length.value > max.value)

const HEADINGS = [1, 2, 3, 4, 5, 6] as const
const items = computed<EditorToolbarItem[][]>(() => [
  ...(full.value
    ? [[
        {
          icon: 'i-lucide-heading',
          trailingIcon: 'i-lucide-chevron-down',
          color: 'neutral',
          variant: 'ghost',
          tooltip: { text: t('renderer.rich.textStyle') },
          'aria-label': t('renderer.rich.textStyle'),
          items: [
            { kind: 'paragraph', icon: 'i-lucide-pilcrow', label: t('renderer.rich.paragraph') },
            ...HEADINGS.map(level => ({
              kind: 'heading' as const,
              level,
              icon: `i-lucide-heading-${level}`,
              label: t('renderer.rich.headingN', { n: level }),
            })),
          ],
        },
      ] as EditorToolbarItem[]]
    : []),
  [
    { kind: 'mark', mark: 'bold', icon: 'i-lucide-bold', tooltip: { text: t('renderer.rich.bold') } },
    { kind: 'mark', mark: 'italic', icon: 'i-lucide-italic', tooltip: { text: t('renderer.rich.italic') } },
    { kind: 'mark', mark: 'underline', icon: 'i-lucide-underline', tooltip: { text: t('renderer.rich.underline') } },
    { kind: 'mark', mark: 'strike', icon: 'i-lucide-strikethrough', tooltip: { text: t('renderer.rich.strike') } },
    ...(full.value
      ? ([{ kind: 'mark', mark: 'code', icon: 'i-lucide-code', tooltip: { text: t('renderer.rich.code') } }] as EditorToolbarItem[])
      : []),
  ],
  [
    { kind: 'bulletList', icon: 'i-lucide-list', tooltip: { text: t('renderer.rich.bullets') } },
    { kind: 'orderedList', icon: 'i-lucide-list-ordered', tooltip: { text: t('renderer.rich.numbers') } },
    { kind: 'blockquote', icon: 'i-lucide-text-quote', tooltip: { text: t('renderer.rich.quote') } },
    ...(full.value
      ? ([{ kind: 'codeBlock', icon: 'i-lucide-square-code', tooltip: { text: t('renderer.rich.codeBlock') } }] as EditorToolbarItem[])
      : []),
    { kind: 'link', icon: 'i-lucide-link', tooltip: { text: t('renderer.rich.link') } },
  ],
  ...(full.value
    ? [[
        { kind: 'textAlign', align: 'left', icon: 'i-lucide-align-left', tooltip: { text: t('renderer.rich.alignLeft') } },
        { kind: 'textAlign', align: 'center', icon: 'i-lucide-align-center', tooltip: { text: t('renderer.rich.alignCenter') } },
        { kind: 'textAlign', align: 'right', icon: 'i-lucide-align-right', tooltip: { text: t('renderer.rich.alignRight') } },
        { kind: 'textAlign', align: 'justify', icon: 'i-lucide-align-justify', tooltip: { text: t('renderer.rich.justify') } },
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
      v-model="html"
      content-type="html"
      :extensions="extensions"
      :editable="!locked"
      :placeholder="field.placeholder || t('renderer.rich.placeholder')"
      :image="false"
      :mention="false"
      :ui="{
        base: 'min-h-28 px-3 py-2 text-sm leading-5 *:my-0.5 sm:px-3 [&_p]:leading-5 [&_li]:leading-5 [&_pre]:my-1.5',
      }"
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
      {{ t('renderer.rich.count', { n: length, max }) }}
    </p>
  </div>
</template>
