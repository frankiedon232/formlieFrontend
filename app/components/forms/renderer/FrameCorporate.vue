<!--
  Page style "Corporate" (page designs, owner 2026-10-04): an official top bar in the chosen tone
  (organisation, "Encrypted", website link) with a brand stripe, the quick facts as one quiet line
  above the form, and a full footer band with the organisation and its website above the legal
  footer. For anyone who wants the form to feel like part of their own site.
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
const { t } = useI18n()
const { frame, primary, onPrimary, tone, website, websiteHost, initials, facts, year } = useFrameParts(props)
</script>

<template>
  <div class="flex flex-col">
    <header class="border-b" :style="tone">
      <div v-if="frame.tone !== 'brand'" class="h-1" :style="{ background: primary }" aria-hidden="true" />
      <div class="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 @xl:px-6">
        <FormsRendererFrameOrg :org="org" :initials="initials" :accent="primary" :on-accent="onPrimary" :inverse="frame.tone === 'brand'" :form="theme.header.show_title ? title : null" />
        <div class="flex shrink-0 items-center gap-3">
          <span class="hidden items-center gap-1.5 text-xs opacity-80 @3xl:flex"><UIcon name="i-lucide-lock-keyhole" class="size-3.5" />{{ t('public.frame.encrypted') }}</span>
          <slot name="language" />
          <FormsRendererFrameWebsite v-if="website" :href="website" :org-name="org.name" />
        </div>
      </div>
    </header>
    <p v-if="facts.length" class="mx-auto flex w-full max-w-6xl flex-wrap gap-x-4 gap-y-1 px-4 pt-6 text-xs text-(--ui-text-muted) @xl:px-6">
      <span v-for="fact in facts" :key="fact.icon" class="flex items-center gap-1.5"><UIcon :name="fact.icon" class="size-3.5" :style="{ color: primary }" />{{ fact.label }}</span>
    </p>
    <div class="flex-1 [&>div]:min-h-full"><slot /></div>
    <section class="mt-6 border-t" :style="tone">
      <div class="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-6 @xl:flex-row @xl:items-center @xl:justify-between @xl:px-6">
        <FormsRendererFrameOrg :org="org" :initials="initials" :accent="primary" :on-accent="onPrimary" :inverse="frame.tone === 'brand'" />
        <FormsRendererFrameLink
          v-if="website"
          :href="website"
          :title="org.name"
          class="inline-flex items-center gap-1.5 text-sm font-medium underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-current"
        >
          <UIcon name="i-lucide-globe" class="size-4" />{{ websiteHost }}<UIcon name="i-lucide-arrow-up-right" class="size-3.5" />
        </FormsRendererFrameLink>
      </div>
    </section>
    <FormsRendererFrameFooter :org="org" :year="year" />
  </div>
</template>
