<!--
  Shows saved rich text (HTML) safely: a read-only Nuxt UI editor parses it into its schema, so
  only known nodes and marks survive (no scripts, no unknown attributes), no v-html anywhere.
  Same look as the editor (RichText.vue) and the paragraph block.
-->
<script setup lang="ts">
import TextAlign from '@tiptap/extension-text-align'

defineProps<{ html: string }>()
const extensions = [TextAlign.configure({ types: ['heading', 'paragraph'] })]
</script>

<template>
  <UEditor
    :model-value="html"
    content-type="html"
    :editable="false"
    :extensions="extensions"
    :image="false"
    :mention="false"
    :ui="{ base: RICH_TEXT_BASE }"
    class="w-full"
  />
</template>
