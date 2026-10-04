<!--
  In-app browser for public form pages (owner, 2026-10-03): the organisation's website, terms and
  privacy pages open here, a window over about 80% of the screen, rounded, with the organisation's
  branding, a loading bar, reload / open-in-new-tab and a clear close button, so the form
  underneath (and everything typed in) stays. Some sites refuse to be shown inside another page;
  browsers don't say so, so "Open in a new tab" is always one click away and offered again when a
  page takes long.
-->
<script setup lang="ts">
const { t } = useI18n()
const browser = useInAppBrowser()
const { profile } = useTenant()

const open = computed({
  get: () => browser.state.open,
  set: value => (browser.state.open = value),
})
const host = computed(() => {
  try {
    return new URL(browser.state.url).host.replace(/^www\./, '')
  } catch {
    return ''
  }
})
const heading = computed(() => browser.state.title || host.value)
const org = computed(() => ({ name: profile.value?.name ?? '', logo: profile.value?.logo_url ?? null }))
const initials = computed(() =>
  org.value.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(word => word[0]!.toUpperCase())
    .join(''),
)

// Loading: a bar and a placeholder until the page has loaded; after 8 s, offer a new tab.
const loading = ref(true)
const slow = ref(false)
const frameKey = ref(0)
let timer: ReturnType<typeof setTimeout> | undefined
function start() {
  loading.value = true
  slow.value = false
  clearTimeout(timer)
  timer = setTimeout(() => (slow.value = loading.value), 8000)
}
function loaded() {
  loading.value = false
  slow.value = false
  clearTimeout(timer)
}
function reload() {
  frameKey.value++
  start()
}
watch(
  () => [browser.state.open, browser.state.url],
  ([isOpen]) => (isOpen ? start() : clearTimeout(timer)),
)
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="heading"
    :ui="{
      content: 'flex h-[86dvh] w-[calc(100vw-1rem)] max-w-none flex-col overflow-hidden rounded-2xl sm:h-[82dvh] sm:w-[82vw] sm:max-w-7xl',
      header: 'gap-3 px-3 py-2.5 sm:px-4',
      body: 'relative min-h-0 flex-1 p-0 sm:p-0',
      footer: 'px-3 py-2 sm:px-4',
    }"
  >
    <template #title>
      <span class="flex min-w-0 items-center gap-3">
        <img v-if="org.logo" :src="org.logo" :alt="org.name" class="hidden h-7 max-w-28 shrink-0 object-contain sm:block" />
        <span v-else-if="initials" class="hidden size-8 shrink-0 items-center justify-center rounded-lg bg-inverted text-xs font-semibold text-inverted sm:flex" aria-hidden="true">
          {{ initials }}
        </span>
        <span class="flex min-w-0 flex-col">
          <span class="truncate text-sm font-semibold text-highlighted">{{ heading }}</span>
          <span class="flex min-w-0 items-center gap-1 text-xs font-normal text-muted">
            <UIcon name="i-lucide-lock" class="size-3 shrink-0 text-success" />
            <span class="truncate">{{ host }}</span>
          </span>
        </span>
      </span>
    </template>

    <template #actions>
      <UTooltip :text="t('public.browser.reload')">
        <UButton icon="i-lucide-rotate-cw" color="neutral" variant="ghost" :aria-label="t('public.browser.reload')" @click="reload" />
      </UTooltip>
      <UTooltip :text="t('public.browser.newTab')">
        <UButton icon="i-lucide-external-link" color="neutral" variant="ghost" :to="browser.state.url" target="_blank" external :aria-label="t('public.browser.newTab')" />
      </UTooltip>
    </template>

    <template #close>
      <UTooltip :text="t('public.browser.close')" :kbds="['esc']">
        <UButton
          icon="i-lucide-x"
          color="neutral"
          variant="solid"
          size="md"
          class="rounded-full shadow-md ring-2 ring-(--ui-bg)"
          :aria-label="t('public.browser.close')"
          @click="browser.close()"
        />
      </UTooltip>
    </template>

    <template #body>
      <!-- Loading bar along the top edge -->
      <div v-if="loading" class="absolute inset-x-0 top-0 z-10">
        <UProgress animation="carousel" size="xs" color="neutral" />
      </div>
      <!-- Placeholder while loading -->
      <div v-if="loading" class="absolute inset-0 z-[5] flex flex-col items-center justify-center gap-3 bg-elevated/50 px-6 text-center">
        <UIcon name="i-lucide-loader-circle" class="size-7 animate-spin text-muted" />
        <p class="text-sm font-medium text-highlighted">{{ t('public.browser.loading', { host }) }}</p>
        <div v-if="slow" class="flex flex-col items-center gap-2">
          <p class="max-w-sm text-xs text-muted">{{ t('public.browser.slow') }}</p>
          <UButton :label="t('public.browser.newTab')" icon="i-lucide-external-link" color="neutral" variant="outline" size="sm" :to="browser.state.url" target="_blank" external />
        </div>
      </div>
      <iframe
        v-if="browser.state.open && browser.state.url"
        :key="`${browser.state.url}-${frameKey}`"
        :src="browser.state.url"
        :title="heading"
        class="size-full border-0 bg-white"
        referrerpolicy="no-referrer"
        sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-forms"
        @load="loaded"
      />
    </template>

    <template #footer>
      <div class="flex w-full flex-wrap items-center justify-between gap-2 text-xs text-muted">
        <span class="flex items-center gap-1.5"><UIcon name="i-lucide-shield-check" class="size-3.5 shrink-0" />{{ t('public.browser.safe') }}</span>
        <UButton :label="t('public.browser.backToForm')" icon="i-lucide-arrow-left" color="neutral" variant="link" size="xs" class="px-0 rtl:[&_svg]:rotate-180" @click="browser.close()" />
      </div>
    </template>
  </AppModal>
</template>
