<!--
  "New here?" (F25, owner 2026-10-10): the first time someone opens a page with a guided tour, a small card at the
  bottom corner offers it, a moment after the page has loaded: Take the tour · Not now · Turn off tips. Shown
  once per page per person (useTours). Keyboard: it takes focus politely (announced, not grabbed); Esc = Not now.
-->
<script setup lang="ts">
const { t } = useI18n()
const route = useRoute()
const tours = useTours()
const help = useHelpPanel()
const { offer } = tours

// A moment after each page change, so the page shows first and quick clicks through pages don't pop cards
let timer: ReturnType<typeof setTimeout> | undefined
watch(
  () => route.path,
  path => {
    clearTimeout(timer)
    offer.value = null
    timer = setTimeout(() => void tours.check(path), 1500)
  },
  { immediate: true },
)
onBeforeUnmount(() => clearTimeout(timer))
// A tour started another way (the "?" panel) takes the place of the offer
watch(() => help.tour.value, value => value && (offer.value = null))
defineShortcuts({ escape: { usingInput: false, handler: () => offer.value && tours.later() } })
</script>

<template>
  <Transition enter-from-class="translate-y-3 opacity-0" leave-to-class="translate-y-3 opacity-0" enter-active-class="transition duration-300" leave-active-class="transition duration-200">
    <div
      v-if="offer"
      role="dialog"
      aria-live="polite"
      :aria-label="t('help.tour.offerTitle')"
      class="fixed end-4 bottom-4 z-50 w-[min(22rem,calc(100vw-2rem))] rounded-xl border border-default bg-default p-4 shadow-xl"
    >
      <div class="flex items-start gap-3">
        <span class="flex size-9 shrink-0 items-center justify-center rounded-full bg-inverted text-inverted"><UIcon name="i-lucide-route" class="size-4" /></span>
        <div class="flex min-w-0 flex-1 flex-col gap-1">
          <span class="text-sm font-semibold text-highlighted">{{ t('help.tour.offerTitle') }}</span>
          <span class="text-xs text-muted">{{ t('help.tour.offerText', { title: offer.title, n: offer.steps.length }, offer.steps.length) }}</span>
        </div>
        <UButton icon="i-lucide-x" color="neutral" variant="ghost" size="xs" square :aria-label="t('help.tour.later')" @click="tours.later()" />
      </div>
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <UButton :label="t('help.tour.take')" icon="i-lucide-play" color="neutral" size="sm" @click="tours.take()" />
        <UButton :label="t('help.tour.later')" color="neutral" variant="outline" size="sm" @click="tours.later()" />
        <UButton :label="t('help.tour.turnOff')" color="neutral" variant="link" size="sm" class="ms-auto" @click="tours.turnOff()" />
      </div>
    </div>
  </Transition>
</template>
