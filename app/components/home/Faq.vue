<script setup lang="ts">
import type { AccordionItem } from '@nuxt/ui'

// FAQ, premium (owner, 2026-10-13): a sticky dark card with a small live conversation (a question arrives, the
// team types, the answer appears) and a way to ask more; the questions as numbered cards that lift when open.
// One open at a time (docs/DESIGN.md); also given to search engines as FAQPage data.
const { t, tm, rt } = useI18n()
const localePath = useLocalePath()
const root = useTemplateRef<HTMLElement>('root')
const { paused } = useSectionMotion(root)

const items = computed<(AccordionItem & { number: string })[]>(() =>
  (tm('home.faq.items') as { q: unknown; a: unknown }[]).map((item, i) => ({
    label: rt(item.q as string),
    content: rt(item.a as string),
    value: String(i),
    number: String(i + 1).padStart(2, '0'),
  })),
)
const first = computed(() => items.value[0])

useHead(() => ({
  script: [
    {
      key: 'faq-schema',
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: items.value.map(item => ({
          '@type': 'Question',
          name: item.label,
          acceptedAnswer: { '@type': 'Answer', text: item.content },
        })),
      }),
    },
  ],
}))
</script>

<template>
  <UPageSection>
    <div class="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-14">
      <!-- Start side: the conversation card -->
      <div class="lg:sticky lg:top-24 lg:self-start">
        <p class="text-sm font-semibold text-primary">FAQ</p>
        <h2 class="mt-2 text-3xl font-semibold tracking-tight text-pretty text-highlighted sm:text-4xl">
          {{ t('home.faq.title') }}
        </h2>
        <p class="mt-3 text-muted">{{ t('home.faq.description') }}</p>

        <div
          ref="root"
          class="relative isolate mt-8 overflow-hidden rounded-3xl bg-neutral-950 p-6 text-white shadow-2xl shadow-black/15 ring-1 ring-white/10"
          :class="{ 'motion-paused': paused }"
        >
          <div
            aria-hidden="true"
            class="absolute -end-20 -top-20 -z-10 size-64 rounded-full bg-violet-600/30 blur-3xl"
          />

          <!-- A question arrives, the team types, the answer appears (decorative) -->
          <div aria-hidden="true" class="space-y-3">
            <div class="flex justify-end">
              <p
                class="max-w-[85%] rounded-2xl rounded-ee-sm bg-white px-4 py-2.5 text-sm font-medium text-neutral-950 shadow-lg motion-safe:animate-[feed_9s_ease-in-out_infinite] motion-safe:[animation-fill-mode:backwards]"
              >
                {{ first?.label }}
              </p>
            </div>
            <div class="flex items-end gap-2">
              <span
                class="flex size-7 shrink-0 items-center justify-center rounded-full bg-white/10 ring-1 ring-white/15"
              >
                <UIcon name="i-formalie-mark" class="size-3.5" />
              </span>
              <div class="relative min-h-10 max-w-[85%]">
                <!-- Typing, then the answer -->
                <span
                  class="absolute start-0 bottom-0 flex gap-1 rounded-2xl rounded-es-sm bg-white/10 px-3 py-3 motion-safe:animate-[feed_9s_ease-in-out_infinite] motion-safe:[animation-delay:1s] motion-safe:[animation-fill-mode:backwards] motion-reduce:hidden"
                >
                  <span class="size-1.5 rounded-full bg-white/70 motion-safe:animate-pulse" />
                  <span
                    class="size-1.5 rounded-full bg-white/70 motion-safe:animate-pulse [animation-delay:200ms]"
                  />
                  <span
                    class="size-1.5 rounded-full bg-white/70 motion-safe:animate-pulse [animation-delay:400ms]"
                  />
                </span>
                <p
                  class="relative rounded-2xl rounded-es-sm bg-white/10 px-4 py-2.5 text-sm text-white/90 ring-1 ring-white/10 backdrop-blur motion-safe:animate-[feed_9s_ease-in-out_infinite] motion-safe:[animation-delay:2.4s] motion-safe:[animation-fill-mode:backwards]"
                >
                  {{ first?.content }}
                </p>
              </div>
            </div>
          </div>

          <div class="mt-6 border-t border-white/10 pt-5">
            <p class="font-semibold">{{ t('home.faq.stillTitle') }}</p>
            <p class="mt-1 text-sm text-white/65">{{ t('home.faq.stillText') }}</p>
            <UButton
              :to="localePath('/contact')"
              :label="t('nav.contact')"
              trailing-icon="i-lucide-arrow-right"
              color="neutral"
              class="mt-4 bg-white text-neutral-950 hover:bg-white/90"
            />
          </div>
        </div>
      </div>

      <!-- End side: the questions as cards -->
      <UAccordion
        :items="items"
        default-value="0"
        :ui="{
          root: 'flex flex-col gap-3',
          item: 'group/item rounded-2xl border-0 bg-default px-5 ring-1 ring-default transition duration-300 data-[state=open]:shadow-xl data-[state=open]:shadow-black/5 data-[state=open]:ring-inverted hover:ring-accented sm:px-6',
          trigger: 'gap-4 py-5 text-base font-semibold text-highlighted sm:text-lg',
          body: 'pb-6 ps-12 text-base text-muted sm:ps-14',
        }"
      >
        <template #leading="{ item }">
          <span
            class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-elevated font-mono text-xs font-semibold text-muted tabular-nums ring-1 ring-default transition-colors group-data-[state=open]/item:bg-inverted group-data-[state=open]/item:text-inverted sm:size-9"
          >
            {{ (item as { number: string }).number }}
          </span>
        </template>
        <template #trailing>
          <span
            class="ms-auto flex size-8 shrink-0 items-center justify-center rounded-full ring-1 ring-default transition duration-300 group-data-[state=open]/item:rotate-45 group-data-[state=open]/item:bg-inverted group-data-[state=open]/item:text-inverted motion-reduce:transition-none"
          >
            <UIcon name="i-lucide-plus" class="size-4" />
          </span>
        </template>
      </UAccordion>
    </div>
  </UPageSection>
</template>
