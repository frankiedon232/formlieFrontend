<script setup lang="ts">
// One section's legal text, rendered from Markdown with MDC (never v-html). Used with `hydrate-never`: the
// prerendered HTML stays as it is and the Markdown parser never loads in the browser; newer text from the API
// mounts a fresh copy (the page keys it by version and length).
defineProps<{ markdown: string }>()
</script>

<template>
  <MDC
    :value="markdown"
    tag="div"
    class="mt-5 text-[15px]/7 text-toned sm:ps-13 [&_a]:font-medium [&_a]:text-highlighted [&_strong]:text-highlighted"
  />
</template>
