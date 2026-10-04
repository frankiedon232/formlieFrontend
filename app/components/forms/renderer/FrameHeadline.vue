<!--
  Page style "Headline" (page designs, owner 2026-10-04): a slim bar with the organisation, then on
  wide screens a large headline with the intro and quick facts beside the form (the text stays in
  view while the form scrolls); on phones the headline sits above the form.
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
    <header class="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-3 px-4 @xl:px-6">
      <FormsRendererFrameOrg :org="org" :initials="initials" :accent="primary" :on-accent="onPrimary" />
      <div class="flex shrink-0 items-center gap-2">
        <slot name="language" />
        <FormsRendererFrameWebsite v-if="website" :href="website" :org-name="org.name" />
      </div>
    </header>
    <div class="mx-auto grid w-full max-w-6xl flex-1 @4xl:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] @4xl:items-start @4xl:gap-8 @4xl:px-6 @4xl:py-8">
      <div class="flex flex-col gap-4 px-4 pt-4 @xl:px-6 @4xl:sticky @4xl:top-8 @4xl:px-0 @4xl:pt-14">
        <span class="h-1 w-12 rounded-full" :style="{ background: primary }" aria-hidden="true" />
        <h1 class="text-3xl leading-tight font-semibold tracking-tight text-balance @4xl:text-5xl">{{ title }}</h1>
        <p v-if="intro" class="max-w-prose text-sm leading-relaxed opacity-80 @xl:text-base">{{ intro }}</p>
        <ul v-if="facts.length" class="flex flex-wrap gap-x-5 gap-y-2 pt-1 text-sm opacity-85 @4xl:flex-col">
          <li v-for="fact in facts" :key="fact.icon" class="flex items-center gap-2"><UIcon :name="fact.icon" class="size-4 shrink-0" :style="{ color: primary }" />{{ fact.label }}</li>
        </ul>
      </div>
      <div class="min-w-0 [&>div]:min-h-full"><slot /></div>
    </div>
    <FormsRendererFrameFooter :org="org" :year="year" />
  </div>
</template>
