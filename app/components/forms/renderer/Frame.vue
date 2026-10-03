<!--
  The page around a form on its public link (F10, owner 2026-10-03) — the organisation's branding,
  a link to its own website (never the portal), quick facts and a secure-by-Formalie footer, in
  four styles (theme.frame.style): branded · spotlight · side · minimal. Lives inside the form page
  root, so it follows the form's theme (colours, font). The default slot is the form area.
  Text on dark / brand surfaces is black or white for contrast (readableOn).
-->
<script setup lang="ts">
import { readableOn, type FormTheme } from '#shared/utils/forms/theme'

const props = defineProps<{
  theme: FormTheme
  title: string
  intro?: string
  questions: number
  minutes: number
  org: { name: string; logo: string | null; website: string | null }
}>()
const { t } = useI18n()

const frame = computed(() => props.theme.frame)
const primary = computed(() => props.theme.colors.primary)
const onPrimary = computed(() => readableOn(primary.value))
const brandGradient = computed(
  () => `linear-gradient(135deg, ${primary.value}, color-mix(in oklab, ${primary.value} 62%, #000))`,
)

/** Bar / panel surface for the chosen tone. */
const tone = computed(() => {
  switch (frame.value.tone) {
    case 'dark':
      return { background: '#0a0a0a', color: '#fafafa', borderColor: 'rgb(255 255 255 / 0.08)' }
    case 'brand':
      return { background: primary.value, color: onPrimary.value, borderColor: 'transparent' }
    default:
      return {
        background: props.theme.container.bg,
        color: props.theme.colors.text,
        borderColor: 'var(--ui-border)',
      }
  }
})
const sideSurface = computed(() =>
  frame.value.tone === 'light'
    ? { background: props.theme.container.bg, color: props.theme.colors.text }
    : frame.value.tone === 'dark'
      ? { background: '#0a0a0a', color: '#fafafa' }
      : { background: brandGradient.value, color: onPrimary.value },
)

const website = computed(() =>
  frame.value.show_website && props.org.website && /^https:\/\//i.test(props.org.website)
    ? props.org.website
    : null,
)
const websiteHost = computed(() => {
  try {
    return website.value ? new URL(website.value).hostname.replace(/^www\./, '') : ''
  } catch {
    return ''
  }
})
const initials = computed(() =>
  props.org.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(word => word[0]!.toUpperCase())
    .join(''),
)
const facts = computed(() =>
  frame.value.show_facts
    ? [
        { icon: 'i-lucide-timer', label: t('public.frame.minutes', { n: props.minutes }, props.minutes) },
        {
          icon: 'i-lucide-list-checks',
          label: t('public.frame.questions', { n: props.questions }, props.questions),
        },
        { icon: 'i-lucide-lock-keyhole', label: t('public.frame.encrypted') },
      ]
    : [],
)
const year = new Date().getFullYear()
const glow = computed(() => `radial-gradient(60% 100% at 50% 0%, color-mix(in oklab, ${primary.value} 14%, transparent), transparent)`)
</script>

<template>
  <div class="@container flex min-h-full flex-col">
    <!-- ── Side panel ─────────────────────────────────────────────────────────── -->
    <div
      v-if="frame.style === 'side'"
      class="flex flex-1 flex-col @4xl:grid @4xl:grid-cols-[minmax(20rem,38%)_minmax(0,1fr)]"
    >
      <aside
        class="flex flex-col gap-8 px-5 py-6 @xl:px-8 @4xl:sticky @4xl:top-0 @4xl:max-h-dvh @4xl:min-h-dvh @4xl:justify-between @4xl:px-10 @4xl:py-10"
        :class="frame.tone === 'light' ? 'border-b border-(--ui-border) @4xl:border-e @4xl:border-b-0' : ''" :style="sideSurface"
      >
        <FormsRendererFrameOrg :org="org" :initials="initials" :accent="primary" :on-accent="onPrimary" />
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
          <a
            v-if="website"
            :href="website"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-1.5 font-medium underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-current"
          >
            <UIcon name="i-lucide-globe" class="size-3.5" />{{ websiteHost
            }}<UIcon name="i-lucide-arrow-up-right" class="size-3.5" />
          </a>
          <FormsRendererFrameSecured />
        </div>
      </aside>
      <div class="flex min-w-0 flex-col">
        <div class="flex-1"><slot /></div>
        <FormsRendererFrameFooter
          class="@4xl:hidden"
          :org="org"
          :website="website"
          :website-host="websiteHost"
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
          />
          <UButton
            v-if="website"
            :to="website"
            target="_blank"
            external
            :label="t('public.frame.website')"
            trailing-icon="i-lucide-arrow-up-right"
            color="neutral"
            variant="outline"
            size="sm"
            class="shrink-0 rounded-full border-current/25 bg-transparent text-current ring-current/25 hover:bg-current/10 @max-xl:[&>span:first-child]:sr-only"
            :aria-label="t('public.frame.websiteOf', { name: org.name })"
          />
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
        :website="website"
        :website-host="websiteHost"
        :year="year"
        :slim="frame.style === 'minimal'"
      />
    </div>
  </div>
</template>
