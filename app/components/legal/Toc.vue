<script setup lang="ts">
// "On this page" for a legal document (owner, 2026-10-13: compact, not long): one short numbered line per section,
// the section being read highlighted, reading progress in the header, a capped height that scrolls inside itself.
const props = defineProps<{
  sections: { id: string; number: string | null; title: string }[]
  progress: number
}>()
const { t } = useI18n()

// The section being read is the last one whose top has passed under the header.
const active = ref(props.sections[0]?.id ?? '')
const { y } = useWindowScroll()
function update() {
  let current = props.sections[0]?.id ?? ''
  for (const section of props.sections) {
    const el = document.getElementById(section.id)
    if (el && el.getBoundingClientRect().top <= 140) current = section.id
  }
  active.value = current
}
onMounted(update)
watchThrottled(y, update, { throttle: 80 })

// Keep the highlighted line in view inside the list.
const list = useTemplateRef<HTMLElement>('list')
watch(active, id => {
  const box = list.value
  const item = box?.querySelector<HTMLElement>(`[data-id="${id}"]`)
  if (!box || !item) return
  // Only the list scrolls, never the page.
  if (item.offsetTop < box.scrollTop) box.scrollTop = item.offsetTop - 8
  else if (item.offsetTop + item.offsetHeight > box.scrollTop + box.clientHeight)
    box.scrollTop = item.offsetTop + item.offsetHeight - box.clientHeight + 8
})

const toTop = () => window.scrollTo({ top: 0, behavior: 'smooth' })
</script>

<template>
  <nav
    :aria-label="t('legalPage.onThisPage')"
    class="rounded-2xl bg-default/80 p-3 shadow-lg shadow-black/5 ring-1 ring-default backdrop-blur"
  >
    <div class="flex items-center justify-between gap-2 px-1">
      <p class="text-xs font-semibold tracking-wide text-highlighted uppercase">
        {{ t('legalPage.onThisPage') }}
      </p>
      <span class="text-[11px] text-muted tabular-nums">{{ progress }}%</span>
    </div>
    <div
      class="mx-1 mt-2 h-0.5 overflow-hidden rounded-full bg-elevated"
      role="progressbar"
      :aria-label="t('legalPage.progress')"
      :aria-valuenow="progress"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <div
        class="h-full rounded-full bg-inverted transition-[width] duration-200"
        :style="{ width: `${progress}%` }"
      />
    </div>

    <ul
      ref="list"
      class="relative mt-2 max-h-[min(22rem,55vh)] space-y-px overflow-y-auto overscroll-contain pe-1"
    >
      <li v-for="section in sections" :key="section.id">
        <a
          :href="`#${section.id}`"
          :data-id="section.id"
          :aria-current="active === section.id ? 'location' : undefined"
          class="flex items-center gap-2 rounded-lg px-1.5 py-1 text-[12.5px] leading-5 transition-colors"
          :class="
            active === section.id
              ? 'bg-elevated font-medium text-highlighted'
              : 'text-muted hover:text-highlighted'
          "
        >
          <span
            class="w-5 shrink-0 font-mono text-[10.5px] tabular-nums"
            :class="active === section.id ? 'text-highlighted' : 'text-dimmed'"
          >
            {{ section.number ?? '·' }}
          </span>
          <span class="truncate">{{ section.title }}</span>
        </a>
      </li>
    </ul>

    <UButton
      :label="t('legalPage.backToTop')"
      icon="i-lucide-arrow-up"
      color="neutral"
      variant="ghost"
      size="xs"
      class="mt-2 w-full justify-center"
      @click="toTop"
    />
  </nav>
</template>
