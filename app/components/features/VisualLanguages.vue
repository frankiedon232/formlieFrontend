<script setup lang="ts">
// One form in many languages (drawn): the same question turns from language to language, right to left
// included, while the language switch follows. Still for reduced motion (the visitor's own language shows).
const { t, locale } = useI18n()
const root = useTemplateRef<HTMLElement>('root')
const { still, paused } = useSectionMotion(root)

// Sample form content in several languages (what a respondent would see), not site copy.
const SAMPLES = [
  { code: 'en', flag: 'i-circle-flags-us', dir: 'ltr', text: 'How would you rate your visit?' },
  { code: 'fr', flag: 'i-circle-flags-fr', dir: 'ltr', text: 'Comment évaluez-vous votre visite ?' },
  { code: 'ar', flag: 'i-circle-flags-sa', dir: 'rtl', text: 'كيف تقيّم زيارتك؟' },
  { code: 'ja', flag: 'i-circle-flags-jp', dir: 'ltr', text: 'ご来店はいかがでしたか？' },
  { code: 'es', flag: 'i-circle-flags-es', dir: 'ltr', text: '¿Cómo valoras tu visita?' },
  { code: 'sw', flag: 'i-circle-flags-ke', dir: 'ltr', text: 'Unaipimaje ziara yako?' },
  { code: 'hi', flag: 'i-circle-flags-in', dir: 'ltr', text: 'आप अपनी यात्रा को कैसे आंकेंगे?' },
] as const

const index = ref(0)
const sample = computed(() => (still.value ? null : SAMPLES[index.value]))
useIntervalFn(() => {
  if (!still.value && !paused.value) index.value = (index.value + 1) % SAMPLES.length
}, 2200)
</script>

<template>
  <div ref="root" aria-hidden="true" class="relative" :class="{ 'motion-paused': paused }">
    <div class="absolute -inset-6 rounded-[2rem] bg-violet-500/10 blur-2xl" />
    <div class="relative rounded-3xl bg-default p-6 shadow-2xl shadow-black/10 ring-1 ring-default sm:p-8">
      <div class="flex items-center justify-between">
        <span class="flex items-center gap-2 text-sm font-semibold text-highlighted">
          <UIcon name="i-formalie-mark" class="size-4" />
          Formalie
        </span>
        <!-- The respondent's language switch -->
        <span class="flex items-center gap-1 rounded-full bg-elevated p-1 ring-1 ring-default">
          <span
            v-for="item in SAMPLES"
            :key="item.code"
            class="flex size-6 items-center justify-center rounded-full transition-all duration-300"
            :class="
              (sample?.code ?? locale) === item.code
                ? 'scale-110 bg-default shadow ring-1 ring-default'
                : 'opacity-50'
            "
          >
            <UIcon :name="item.flag" class="size-4" />
          </span>
        </span>
      </div>

      <!-- A new key for each language replays the rise entrance -->
      <p
        :key="sample?.code ?? 'own'"
        :dir="sample?.dir ?? undefined"
        :lang="sample?.code ?? locale"
        class="mt-8 min-h-14 text-xl font-semibold text-highlighted motion-safe:animate-rise sm:text-2xl"
      >
        {{ sample?.text ?? t('features.languages.question') }}
      </p>

      <div class="mt-5 flex gap-2" dir="ltr">
        <span
          v-for="star in 5"
          :key="star"
          class="flex size-10 items-center justify-center rounded-lg ring-1 ring-default"
          :class="star <= 4 ? 'bg-inverted text-inverted' : 'text-dimmed'"
        >
          <UIcon name="i-lucide-star" class="size-4" />
        </span>
      </div>
      <div class="mt-6 h-10 w-32 rounded-lg bg-inverted" />
    </div>
  </div>
</template>
