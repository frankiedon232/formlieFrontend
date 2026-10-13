<script setup lang="ts">
// "Answers from everywhere": four channel cards, each with a small live picture, all feeding one inbox.
const { t } = useI18n()
const root = useTemplateRef<HTMLElement>('root')
const { paused } = useSectionMotion(root)

const channels = ['link', 'embed', 'qr', 'api'] as const
const icons = {
  link: 'i-lucide-link',
  embed: 'i-lucide-code-xml',
  qr: 'i-lucide-qr-code',
  api: 'i-lucide-braces',
}
</script>

<template>
  <UPageSection
    :headline="t('home.channels.eyebrow')"
    :title="t('home.channels.title')"
    :description="t('home.channels.description')"
  >
    <div ref="root" :class="{ 'motion-paused': paused }">
      <UPageGrid class="lg:grid-cols-4">
        <UPageCard
          v-for="(key, i) in channels"
          :key="key"
          :title="t(`home.channels.${key}.title`)"
          :description="t(`home.channels.${key}.text`)"
          variant="outline"
          class="motion-safe:animate-rise"
          :style="{ animationDelay: `${i * 80}ms` }"
          :ui="{ leading: 'w-full' }"
        >
          <template #leading>
            <div class="flex w-full items-start justify-between">
              <span class="flex size-10 items-center justify-center rounded-lg bg-inverted text-inverted">
                <UIcon :name="icons[key]" class="size-5" />
              </span>

              <!-- A tiny live picture per channel -->
              <div
                aria-hidden="true"
                class="flex h-14 w-28 items-center justify-center rounded-lg bg-elevated/60 ring-1 ring-default"
              >
                <span
                  v-if="key === 'link'"
                  class="mx-2 flex min-w-0 items-center gap-1 overflow-hidden rounded-full bg-default px-2 py-1 font-mono text-[10px] text-muted ring-1 ring-default"
                >
                  <UIcon name="i-lucide-lock" class="size-2.5 shrink-0" />
                  <span class="inline-block overflow-hidden whitespace-nowrap motion-safe:animate-type"
                    >formalie.com/join</span
                  >
                </span>
                <span
                  v-else-if="key === 'embed'"
                  class="flex w-20 flex-col gap-1 rounded-md bg-default p-1.5 ring-1 ring-default"
                >
                  <span class="flex gap-0.5">
                    <span class="size-1 rounded-full bg-muted" />
                    <span class="size-1 rounded-full bg-muted" />
                    <span class="size-1 rounded-full bg-muted" />
                  </span>
                  <span class="h-1 w-3/4 rounded-full bg-accented" />
                  <span class="h-2 w-full rounded-sm ring-1 ring-accented" />
                </span>
                <span
                  v-else-if="key === 'qr'"
                  class="relative size-10 overflow-hidden rounded-md bg-default p-1 ring-1 ring-default"
                >
                  <UIcon name="i-lucide-qr-code" class="size-full text-highlighted" />
                  <span
                    class="absolute inset-x-0 h-0.5 bg-violet-500 shadow-[0_0_8px_#8b5cf6] motion-safe:animate-scan"
                  />
                </span>
                <span v-else class="flex flex-col gap-1 font-mono text-[10px]">
                  <span class="text-muted">POST /responses</span>
                  <span class="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                    <span class="size-1.5 rounded-full bg-current motion-safe:animate-caret" />
                    201 Created
                  </span>
                </span>
              </div>
            </div>
          </template>
        </UPageCard>
      </UPageGrid>

      <!-- They all land in one place -->
      <div aria-hidden="true" class="relative mx-auto mt-2 hidden h-16 max-w-4xl lg:block">
        <svg viewBox="0 0 800 64" class="absolute inset-0 size-full" preserveAspectRatio="none">
          <g fill="none" stroke="currentColor" class="text-accented" stroke-width="1.2">
            <path v-for="x in [100, 300, 500, 700]" :key="x" :d="`M ${x} 0 C ${x} 36, 400 28, 400 64`" />
          </g>
          <g
            fill="none"
            stroke="currentColor"
            class="text-violet-500/70"
            stroke-width="1.2"
            stroke-dasharray="2 10"
          >
            <path
              v-for="x in [100, 300, 500, 700]"
              :key="`d-${x}`"
              :d="`M ${x} 0 C ${x} 36, 400 28, 400 64`"
              class="motion-safe:animate-dash"
            />
          </g>
        </svg>
      </div>
      <div class="mt-4 flex justify-center lg:mt-0">
        <span
          class="inline-flex items-center gap-2 rounded-full bg-inverted px-4 py-2 text-sm font-medium text-inverted shadow-lg shadow-black/10"
        >
          <UIcon name="i-formalie-mark" class="size-4" />
          {{ t('home.channels.inbox') }}
        </span>
      </div>
    </div>
  </UPageSection>
</template>
