<!--
  "Visit website" on a public form page: the organisation's own site (never the portal), opened in
  the in-app browser over the form (Ctrl / Cmd / middle click: a new tab). Takes the colour of the
  bar it sits on; on narrow pages only the arrow shows.
-->
<script setup lang="ts">
const props = defineProps<{ href: string; orgName: string }>()
const { t } = useI18n()
const browser = useInAppBrowser()
function visit(event: MouseEvent) {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  browser.open(props.href, props.orgName)
}
</script>

<template>
  <UButton
    :to="href"
    target="_blank"
    external
    :label="t('public.frame.website')"
    trailing-icon="i-lucide-arrow-up-right"
    color="neutral"
    variant="outline"
    size="sm"
    class="shrink-0 rounded-full border-current/25 bg-transparent text-current ring-current/25 hover:bg-current/10 @max-xl:[&>span:first-child]:sr-only"
    :aria-label="t('public.frame.websiteOf', { name: orgName })"
    @click="visit"
  />
</template>
