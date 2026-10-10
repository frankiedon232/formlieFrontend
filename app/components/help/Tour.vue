<!--
  Guided tours and "Show me" (F25 M3): the page dims, the control the step is about (marked data-help="…") is
  ringed, and a card beside it says what it does, with Back / Next / Done (← → or Enter, Esc ends). "Show me"
  links (?show=target) point at one control the same way. A control that isn't on this screen (a phone hides
  some) is skipped, never a dead end.
-->
<script setup lang="ts">
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const help = useHelpPanel()

const rect = ref<DOMRect | null>(null)
const steps = computed(() => (help.tour.value ? help.tour.value.steps : help.spotlight.value ? [{ target: help.spotlight.value, title: t('help.tour.hereTitle'), text: t('help.tour.hereText') }] : []))
const current = computed(() => steps.value[help.step.value] ?? null)
const active = computed(() => !!current.value)

const find = (target: string) => [...document.querySelectorAll<HTMLElement>(`[data-help="${target}"]`)].find(element => element.offsetParent !== null || element.getClientRects().length) ?? null

/** Point at the step's control, waiting a moment for a page that is still loading; skip it if it never shows. */
async function locate() {
  rect.value = null
  const step = current.value
  if (!step) return
  for (let tries = 0; tries < 20; tries++) {
    const element = find(step.target)
    if (element) {
      element.scrollIntoView({ block: 'center', inline: 'nearest' })
      await new Promise(resolve => setTimeout(resolve, 150))
      rect.value = element.getBoundingClientRect()
      return
    }
    await new Promise(resolve => setTimeout(resolve, 150))
  }
  if (help.tour.value && help.step.value < steps.value.length - 1) help.step.value += 1
  else end()
}
watch(current, () => void locate(), { immediate: true })
useEventListener(window, 'resize', () => active.value && void locate())

function end() {
  help.endTour()
  help.spotlight.value = null
  rect.value = null
}
const next = () => (help.step.value < steps.value.length - 1 ? (help.step.value += 1) : end())
const back = () => help.step.value > 0 && (help.step.value -= 1)
useEventListener(window, 'keydown', (event: KeyboardEvent) => {
  if (!active.value) return
  if (event.key === 'Escape') end()
  else if (event.key === 'ArrowRight' || event.key === 'Enter') next()
  else if (event.key === 'ArrowLeft') back()
  else return
  event.preventDefault()
})

// "Show me" links arrive as ?show=target: point at it, then tidy the address
watch(
  () => route.query.show,
  value => {
    if (typeof value !== 'string' || !value) return
    help.endTour()
    help.spotlight.value = value
    const { show: _show, ...rest } = route.query
    void router.replace({ query: rest })
  },
  { immediate: true },
)

const PAD = 6
const card = computed(() => {
  if (!rect.value) return null
  const below = rect.value.bottom + 180 < window.innerHeight
  const left = Math.min(Math.max(12, rect.value.left), window.innerWidth - 300)
  return below ? { top: `${rect.value.bottom + PAD + 10}px`, left: `${left}px` } : { top: `${Math.max(12, rect.value.top - PAD - 170)}px`, left: `${left}px` }
})
</script>

<template>
  <Teleport to="body">
    <div v-if="active && rect" class="fixed inset-0 z-[100]" role="dialog" aria-modal="true" :aria-label="current!.title">
      <!-- The dimmed page with a hole around the control -->
      <div
        class="pointer-events-none fixed rounded-lg ring-2 ring-(--ui-border-inverted) transition-all duration-200"
        :style="{ top: `${rect.top - PAD}px`, left: `${rect.left - PAD}px`, width: `${rect.width + PAD * 2}px`, height: `${rect.height + PAD * 2}px`, boxShadow: '0 0 0 9999px rgb(0 0 0 / 0.55)' }"
      />
      <div class="fixed inset-0" @click="end" />
      <div class="fixed flex w-72 flex-col gap-2 rounded-xl border border-default bg-default p-4 shadow-xl" :style="card!">
        <div class="flex items-start justify-between gap-2">
          <span class="text-sm font-semibold text-highlighted">{{ current!.title }}</span>
          <span v-if="help.tour.value" class="shrink-0 text-xs text-muted tabular-nums">{{ t('help.tour.step', { n: help.step.value + 1, total: steps.length }) }}</span>
        </div>
        <p class="text-sm text-muted">{{ current!.text }}</p>
        <div class="mt-1 flex items-center justify-between gap-2">
          <UButton v-if="help.tour.value" :label="t('help.tour.end')" color="neutral" variant="ghost" size="xs" @click="end" />
          <span v-else />
          <div class="flex gap-1.5">
            <UButton v-if="help.tour.value && help.step.value > 0" :label="t('help.tour.back')" color="neutral" variant="outline" size="xs" @click="back" />
            <UButton :label="help.step.value < steps.length - 1 ? t('help.tour.next') : t('help.tour.done')" color="neutral" size="xs" autofocus @click="next" />
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
