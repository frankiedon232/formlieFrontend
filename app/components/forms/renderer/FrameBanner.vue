<!--
  Page style "Banner" (page designs, owner 2026-10-04): a wide band in the chosen tone carries the
  organisation, the website link, the title, the intro and the quick facts, start-aligned; the form
  follows below it on the page background, then the footer.
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
const { frame, primary, onPrimary, surface, website, initials, facts, year } = useFrameParts(props)
</script>

<template>
  <div class="flex flex-col">
    <section class="px-4 @xl:px-6" :style="surface">
      <div class="mx-auto flex max-w-5xl flex-col gap-8 py-6 @xl:py-10">
        <div class="flex items-center justify-between gap-3">
          <FormsRendererFrameOrg :org="org" :initials="initials" :accent="primary" :on-accent="onPrimary" :inverse="frame.tone !== 'light'" />
          <div class="flex shrink-0 items-center gap-2">
            <slot name="language" />
            <FormsRendererFrameWebsite v-if="website" :href="website" :org-name="org.name" />
          </div>
        </div>
        <div class="flex max-w-3xl flex-col gap-3 pb-2">
          <h1 class="text-3xl leading-tight font-semibold tracking-tight text-balance @4xl:text-4xl">{{ title }}</h1>
          <p v-if="intro" class="max-w-2xl text-sm leading-relaxed opacity-85 @xl:text-base">{{ intro }}</p>
          <ul v-if="facts.length" class="flex flex-wrap gap-x-5 gap-y-2 pt-2 text-sm opacity-90">
            <li v-for="fact in facts" :key="fact.icon" class="flex items-center gap-1.5"><UIcon :name="fact.icon" class="size-4 shrink-0" />{{ fact.label }}</li>
          </ul>
        </div>
      </div>
    </section>
    <div class="flex-1 [&>div]:min-h-full"><slot /></div>
    <FormsRendererFrameFooter :org="org" :year="year" />
  </div>
</template>
