<!--
  Page style "Floating" (page designs, owner 2026-10-04): a rounded bar in the chosen tone floats
  over the page background (organisation, website link), the quick facts as small pills under it,
  then the form and the footer. Light and modern, made for gradient or picture backgrounds.
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
const { frame, primary, onPrimary, tone, website, initials, facts, year } = useFrameParts(props)
</script>

<template>
  <div class="flex flex-col">
    <div class="px-3 pt-3 @xl:px-6 @xl:pt-5">
      <header class="mx-auto flex h-14 max-w-4xl items-center justify-between gap-3 rounded-full border px-3 shadow-lg backdrop-blur @xl:px-4" :style="tone">
        <FormsRendererFrameOrg :org="org" :initials="initials" :accent="primary" :on-accent="onPrimary" :inverse="frame.tone === 'brand'" :form="theme.header.show_title ? title : null" class="min-w-0" />
        <div class="flex shrink-0 items-center gap-2">
          <slot name="language" />
          <FormsRendererFrameWebsite v-if="website" :href="website" :org-name="org.name" />
        </div>
      </header>
    </div>
    <ul v-if="facts.length" class="flex flex-wrap justify-center gap-2 px-4 pt-5">
      <li
        v-for="fact in facts"
        :key="fact.icon"
        class="flex items-center gap-1.5 rounded-full border border-(--ui-border) bg-(--form-container-bg)/80 px-3 py-1 text-xs font-medium text-(--ui-text-toned) shadow-xs backdrop-blur"
      >
        <UIcon :name="fact.icon" class="size-3.5 shrink-0" :style="{ color: primary }" />{{ fact.label }}
      </li>
    </ul>
    <div class="flex-1 [&>div]:min-h-full"><slot /></div>
    <FormsRendererFrameFooter :org="org" :year="year" />
  </div>
</template>
