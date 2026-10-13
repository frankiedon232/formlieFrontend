<script setup lang="ts">
// The designer, animated: the same form restyles itself, look after look, while the swatches follow.
const { t } = useI18n()
const root = useTemplateRef<HTMLElement>('root')

// Three starting looks, drawn with the site's tokens plus each look's own accent (it's the customer's design).
const LOOKS = [
  {
    key: 'minimal',
    swatch: 'bg-white ring-neutral-300',
    page: 'bg-neutral-100',
    card: 'bg-white text-neutral-900 rounded-xl',
    band: 'bg-neutral-900',
    input: 'rounded-lg ring-1 ring-neutral-300 bg-white',
    button: 'bg-neutral-900 text-white rounded-lg',
    star: 'bg-neutral-900 text-white',
  },
  {
    key: 'bold',
    swatch: 'bg-neutral-950 ring-neutral-700',
    page: 'bg-neutral-900',
    card: 'bg-neutral-950 text-white rounded-none',
    band: 'bg-violet-600',
    input: 'rounded-none ring-1 ring-white/20 bg-white/5',
    button: 'bg-violet-500 text-white rounded-none',
    star: 'bg-violet-500 text-white',
  },
  {
    key: 'soft',
    swatch: 'bg-violet-100 ring-violet-300',
    page: 'bg-violet-50',
    card: 'bg-white text-neutral-900 rounded-3xl',
    band: 'bg-gradient-to-r from-violet-400 to-fuchsia-400',
    input: 'rounded-full ring-1 ring-violet-200 bg-violet-50/60',
    button: 'bg-violet-600 text-white rounded-full',
    star: 'bg-violet-100 text-violet-700',
  },
] as const

const { step } = useDemoLoop(root, LOOKS.length - 1, 2400, 1)
const look = computed(() => LOOKS[step.value]!)
</script>

<template>
  <div ref="root">
    <DemoWindow :title="t('home.tabs.design.label')" icon="i-lucide-palette">
      <div class="grid grid-cols-[8.5rem_minmax(0,1fr)] gap-4">
        <!-- Starting looks -->
        <ul class="space-y-1.5">
          <li
            v-for="item in LOOKS"
            :key="item.key"
            class="flex items-center gap-2 rounded-xl p-1.5 text-[11px] font-medium transition-all duration-300"
            :class="
              item.key === look.key ? 'bg-elevated text-highlighted ring-1 ring-inverted' : 'text-muted'
            "
          >
            <span class="size-7 shrink-0 rounded-lg ring-1" :class="item.swatch" />
            {{ t(`demo.looks.${item.key}`) }}
          </li>
        </ul>

        <!-- The live preview -->
        <div class="min-w-0 rounded-xl p-3 transition-colors duration-500" :class="look.page">
          <!-- The same form, restyled: colours and shapes glide from one look to the next -->
          <div class="overflow-hidden shadow-lg transition-all duration-700" :class="look.card">
            <div class="h-10 transition-colors duration-700" :class="look.band" />
            <div class="space-y-3 p-4">
              <p class="text-[13px] font-semibold">{{ t('demo.feedbackForm') }}</p>
              <p class="text-[11px] opacity-70">{{ t('features.languages.question') }}</p>
              <div class="flex gap-1.5" dir="ltr">
                <span
                  v-for="n in 5"
                  :key="n"
                  class="flex size-6 items-center justify-center"
                  :class="[look.star, look.input.includes('rounded-full') ? 'rounded-full' : 'rounded-md']"
                >
                  <UIcon name="i-lucide-star" class="size-3" />
                </span>
              </div>
              <div class="flex h-8 items-center px-3 text-[10px] opacity-70" :class="look.input">
                {{ t('demo.yourEmail') }}
              </div>
              <span class="inline-flex px-4 py-1.5 text-[11px] font-semibold" :class="look.button">{{
                t('demo.send')
              }}</span>
            </div>
          </div>
        </div>
      </div>
    </DemoWindow>
  </div>
</template>
