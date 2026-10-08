<!--
  Page style "Centred" (page designs, owner 2026-10-04): no bar; the organisation's logo and name
  centred above the form on the page background, the quick facts under it, the website link and
  the language switcher in the corner; a slim centred footer. Calm, for short forms.
-->
<script setup lang="ts">
import type { FormTheme } from '#shared/utils/forms/theme'

const props = defineProps<{
  theme: FormTheme
  title: string
  intro?: string
  questions: number
  minutes: number
  org: { name: string; logo: string | null; website: string | null }
}>()
const { primary, onPrimary, website, initials, facts, year } = useFrameParts(props)
</script>

<template>
  <div class="flex flex-col" :style="{ color: theme.colors.text }">
    <header class="flex flex-col items-center gap-4 px-4 pt-4 text-center @xl:pt-6">
      <div class="flex min-h-8 w-full max-w-4xl justify-end gap-2">
        <slot name="language" />
        <FormsRendererFrameWebsite v-if="website" :href="website" :org-name="org.name" />
      </div>
      <FormsRendererFrameOrg :org="org" :initials="initials" :accent="primary" :on-accent="onPrimary" :form="theme.header.show_title ? title : null" class="justify-center pt-2" />
      <ul v-if="facts.length" class="flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs opacity-75">
        <li v-for="fact in facts" :key="fact.icon" class="flex items-center gap-1.5"><UIcon :name="fact.icon" class="size-3.5 shrink-0" :style="{ color: primary }" />{{ fact.label }}</li>
      </ul>
    </header>
    <div class="flex-1 [&>div]:min-h-full"><slot /></div>
    <FormsRendererFrameFooter :org="org" :year="year" slim />
  </div>
</template>
