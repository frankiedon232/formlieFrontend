<!--
  The page around a form on its public link (F10, owner 2026-10-03), the organisation's branding,
  a link to its own website (never the portal), quick facts and a secure-by-Formalie footer, in
  styles (theme.frame.style): branded · spotlight · side · minimal here; banner · centred · headline ·
  corporate · compact · floating (page designs, owner 2026-10-04) in their own components (FrameBanner…). Lives inside the form page
  root, so it follows the form's theme (colours, font). The default slot is the form area.
  Text on dark / brand surfaces is black or white for contrast (readableOn).
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
const { frame, primary, onPrimary, brandGradient, tone, surface: sideSurface, website, websiteHost, initials, facts, year } = useFrameParts(props)
const glow = computed(() => `radial-gradient(60% 100% at 50% 0%, color-mix(in oklab, ${primary.value} 14%, transparent), transparent)`)
/** Styles added with page designs (owner 2026-10-04) each have their own component (literal names: Nuxt resolves them at build time). */
const MORE: Record<string, ReturnType<typeof resolveComponent>> = {
  banner: resolveComponent('FormsRendererFrameBanner'),
  centred: resolveComponent('FormsRendererFrameCentred'),
  headline: resolveComponent('FormsRendererFrameHeadline'),
  corporate: resolveComponent('FormsRendererFrameCorporate'),
  compact: resolveComponent('FormsRendererFrameCompact'),
  floating: resolveComponent('FormsRendererFrameFloating'),
}
const more = computed(() => MORE[frame.value.style] ?? null)
</script>

<template>
  <div class="@container flex min-h-full flex-col">
    <component :is="more" v-if="more" v-bind="props" class="flex-1">
      <template #language><slot name="language" /></template>
      <slot />
    </component>
    <!-- ── Side panel ─────────────────────────────────────────────────────────── -->
    <div
      v-else-if="frame.style === 'side'"
      class="flex flex-1 flex-col @4xl:grid @4xl:grid-cols-[minmax(20rem,38%)_minmax(0,1fr)]"
    >
      <aside
        class="flex flex-col gap-8 px-5 py-6 @xl:px-8 @4xl:sticky @4xl:top-0 @4xl:max-h-dvh @4xl:min-h-dvh @4xl:justify-between @4xl:px-10 @4xl:py-10"
        :class="frame.tone === 'light' ? 'border-b border-(--ui-border) @4xl:border-e @4xl:border-b-0' : ''" :style="sideSurface"
      >
        <div class="flex items-center justify-between gap-3">
          <FormsRendererFrameOrg :org="org" :initials="initials" :accent="primary" :on-accent="onPrimary" />
          <slot name="language" />
        </div>
        <div class="flex flex-col gap-4">
          <h1
            class="text-2xl leading-tight font-semibold tracking-tight text-balance @xl:text-3xl @4xl:text-4xl"
          >
            {{ title }}
          </h1>
          <p v-if="intro" class="max-w-prose text-sm leading-relaxed opacity-85 @xl:text-base">{{ intro }}</p>
          <ul v-if="facts.length" class="flex flex-wrap gap-2 pt-1 @4xl:flex-col @4xl:gap-3">
            <li v-for="fact in facts" :key="fact.icon" class="flex items-center gap-2 text-sm opacity-90">
              <UIcon :name="fact.icon" class="size-4 shrink-0" />{{ fact.label }}
            </li>
          </ul>
        </div>
        <div class="hidden flex-col gap-3 text-xs opacity-80 @4xl:flex">
          <FormsRendererFrameLink
            v-if="website"
            :href="website"
            :title="org.name"
            class="inline-flex items-center gap-1.5 font-medium underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-current"
          >
            <UIcon name="i-lucide-globe" class="size-3.5" />{{ websiteHost
            }}<UIcon name="i-lucide-arrow-up-right" class="size-3.5" />
          </FormsRendererFrameLink>
          <FormsRendererFrameSecured />
        </div>
      </aside>
      <div class="flex min-w-0 flex-col">
        <div class="flex-1"><slot /></div>
        <FormsRendererFrameFooter
          class="@4xl:hidden"
          :org="org"
          :year="year"
        />
      </div>
    </div>

    <!-- ── Branded · Spotlight · Minimal ──────────────────────────────────────── -->
    <div v-else class="flex flex-1 flex-col">
      <header
        v-if="frame.style !== 'minimal'"
        class="relative z-10 border-b"
        :style="
          frame.style === 'spotlight'
            ? { background: 'transparent', color: onPrimary, borderColor: 'transparent' }
            : tone
        "
      >
        <div
          v-if="frame.style === 'branded' && frame.tone !== 'brand'"
          class="h-1"
          :style="{ background: primary }"
          aria-hidden="true"
        />
        <div class="mx-auto flex h-16 max-w-5xl items-center justify-between gap-3 px-4 @xl:px-6">
          <FormsRendererFrameOrg
            :org="org"
            :initials="initials"
            :accent="primary"
            :on-accent="onPrimary"
            :inverse="frame.style === 'spotlight'"
            :form="frame.style === 'branded' && theme.header.show_title ? title : null"
          />
          <div class="flex shrink-0 items-center gap-2">
            <!-- Forms in several languages: the switcher sits beside "Visit website" (owner, 2026-10-04). -->
            <slot name="language" />
            <FormsRendererFrameWebsite v-if="website" :href="website" :org-name="org.name" />
          </div>
        </div>
      </header>

      <!-- Spotlight: the hero carries the title; the form card rises into it. -->
      <section
        v-if="frame.style === 'spotlight'"
        class="-mt-16 px-4 pt-24 pb-28 @xl:px-6 @xl:pt-28 @xl:pb-36"
        :style="{ background: brandGradient, color: onPrimary }"
      >
        <div class="mx-auto flex max-w-3xl flex-col items-center gap-4 text-center">
          <h1
            class="text-3xl leading-tight font-semibold tracking-tight text-balance @xl:text-4xl @4xl:text-5xl"
          >
            {{ title }}
          </h1>
          <p v-if="intro" class="max-w-2xl text-sm leading-relaxed opacity-85 @xl:text-lg">{{ intro }}</p>
          <ul v-if="facts.length" class="flex flex-wrap justify-center gap-2 pt-2">
            <li
              v-for="fact in facts"
              :key="fact.icon"
              class="flex items-center gap-1.5 rounded-full border border-current/20 bg-current/10 px-3 py-1 text-xs font-medium @xl:text-sm"
            >
              <UIcon :name="fact.icon" class="size-3.5 shrink-0" />{{ fact.label }}
            </li>
          </ul>
        </div>
      </section>

      <div class="relative flex flex-1 flex-col" :class="frame.style === 'spotlight' ? '-mt-28 @xl:-mt-36' : ''">
        <!-- Branded: a soft glow of the brand colour under the bar and the quick facts above the form. -->
        <template v-if="frame.style === 'branded'">
          <div class="pointer-events-none absolute inset-x-0 top-0 h-72" :style="{ background: glow }" aria-hidden="true" />
          <ul v-if="facts.length" class="relative flex flex-wrap justify-center gap-2 px-4 pt-6 @xl:pt-8">
            <li
              v-for="fact in facts"
              :key="fact.icon"
              class="flex items-center gap-1.5 rounded-full border border-(--ui-border) bg-(--form-container-bg) px-3 py-1 text-xs font-medium text-(--ui-text-toned) shadow-xs"
            >
              <UIcon :name="fact.icon" class="size-3.5 shrink-0" :style="{ color: primary }" />{{ fact.label }}
            </li>
          </ul>
        </template>
        <div class="relative flex-1 [&>div]:min-h-full"><slot /></div>
      </div>

      <FormsRendererFrameFooter
        :org="org"
        :year="year"
        :slim="frame.style === 'minimal'"
      />
    </div>
  </div>
</template>
