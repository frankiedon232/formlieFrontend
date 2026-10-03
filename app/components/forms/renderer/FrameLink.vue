<!--
  A link on a public form page that opens in the in-app browser (the form stays, nothing typed in
  is lost). A real link underneath: Ctrl / Cmd / middle click still opens a new tab.
-->
<script setup lang="ts">
const props = defineProps<{ href: string; title?: string }>()
const browser = useInAppBrowser()

function onClick(event: MouseEvent) {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  browser.open(props.href, props.title)
}
</script>

<template>
  <a :href="href" target="_blank" rel="noopener noreferrer" @click="onClick"><slot /></a>
</template>
