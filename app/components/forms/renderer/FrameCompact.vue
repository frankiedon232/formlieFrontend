<!--
  Page style "Compact" (page designs, owner 2026-10-04): one slim bar in the chosen tone with the
  organisation and the form's title side by side and the website link at the end, then the form and
  a slim footer. The most room for the form itself.
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
const { frame, primary, onPrimary, tone, website, initials, year } = useFrameParts(props)
</script>

<template>
  <div class="flex flex-col">
    <header class="border-b" :style="tone">
      <div class="mx-auto flex h-14 max-w-5xl items-center gap-3 px-4 @xl:px-6">
        <FormsRendererFrameOrg :org="org" :initials="initials" :accent="primary" :on-accent="onPrimary" :inverse="frame.tone === 'brand'" class="min-w-0" />
        <span class="hidden opacity-40 @xl:inline" aria-hidden="true">/</span>
        <span class="hidden min-w-0 truncate text-sm font-medium opacity-85 @xl:block">{{ title }}</span>
        <div class="ms-auto flex shrink-0 items-center gap-2">
          <slot name="language" />
          <FormsRendererFrameWebsite v-if="website" :href="website" :org-name="org.name" />
        </div>
      </div>
    </header>
    <div class="flex-1 [&>div]:min-h-full"><slot /></div>
    <FormsRendererFrameFooter :org="org" :year="year" slim />
  </div>
</template>
