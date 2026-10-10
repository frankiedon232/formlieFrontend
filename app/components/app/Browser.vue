<!--
  The app's browser window (owner 2026-10-10), in the design of the public forms' link browser: a rounded window
  over most of the screen with the page's name and address (padlock), a loading bar, reload, open in a new tab
  and a clear close button, so the page underneath stays as it was. Formalie's own forms open here (Contact
  support, Enterprise enquiry); when one is sent, the window says so (the embed page tells it). A click outside
  never closes it (owner 2026-10-10): only ✕, Esc or Back to Formalie; with something typed and not sent
  (the embed page says so), closing or reloading asks first.
-->
<script setup lang="ts">
const { t } = useI18n()
const toast = useToast()
const browser = useAppBrowser()
const confirm = useConfirm()

const open = computed({
  get: () => browser.state.open,
  set: value => (value ? (browser.state.open = true) : void leave()),
})
/** Something typed in the form and not sent yet: closing or reloading asks first. */
const typing = ref(false)
async function unsaved() {
  if (!typing.value || sent.value) return false
  return !(await confirm({ title: t('appBrowser.leaveTitle'), description: t('appBrowser.leaveDesc'), confirmLabel: t('appBrowser.leave'), danger: true }))
}
async function leave() {
  if (await unsaved()) return
  typing.value = false
  browser.close()
}
const host = computed(() => {
  try {
    return new URL(browser.state.url).host.replace(/^www\./, '')
  } catch {
    return ''
  }
})
const heading = computed(() => browser.state.title || host.value)

// Loading: a bar and a placeholder until the page has loaded; after 8 s, offer a new tab
const loading = ref(true)
const slow = ref(false)
const sent = ref(false)
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
async function reload() {
  if (await unsaved()) return
  typing.value = false
  sent.value = false
  frameKey.value++
  start()
}
watch(
  () => [browser.state.open, browser.state.url],
  ([isOpen]) => {
    sent.value = false
    typing.value = false
    if (isOpen) start()
    else clearTimeout(timer)
  },
)

// A form inside says it was sent: confirm it here too
const frame = useTemplateRef<HTMLIFrameElement>('frame')
useEventListener(import.meta.client ? window : null, 'message', (event: MessageEvent) => {
  const data = event.data as { type?: string; key?: string } | null
  if (!browser.state.open || event.source !== frame.value?.contentWindow) return
  if (browser.state.form && data?.key !== browser.state.form) return
  if (data?.type === 'formalie:typing') typing.value = true
  if (data?.type !== 'formalie:submitted') return
  sent.value = true
  typing.value = false
  toast.add({ title: t('appBrowser.sent', { name: heading.value }), color: 'success', icon: 'i-lucide-circle-check' })
})
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="heading"
    keep-open
    :ui="{
      content: 'flex h-[86dvh] w-[calc(100vw-1rem)] max-w-none flex-col overflow-hidden rounded-2xl sm:h-[82dvh] sm:w-[82vw] sm:max-w-5xl',
      header: 'gap-3 px-3 py-2.5 sm:px-4',
      body: 'relative min-h-0 flex-1 p-0 sm:p-0',
      footer: 'px-3 py-2 sm:px-4',
    }"
  >
    <template #title>
      <span class="flex min-w-0 items-center gap-3">
        <span class="hidden size-8 shrink-0 items-center justify-center rounded-lg bg-inverted text-inverted sm:flex" aria-hidden="true"><UIcon name="i-formalie-mark" class="size-4" /></span>
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
        <UButton icon="i-lucide-x" color="neutral" variant="solid" size="md" class="rounded-full shadow-md ring-2 ring-(--ui-bg)" :aria-label="t('public.browser.close')" @click="leave" />
      </UTooltip>
    </template>

    <template #body>
      <div v-if="loading" class="absolute inset-x-0 top-0 z-10"><UProgress animation="carousel" size="xs" color="neutral" /></div>
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
        ref="frame"
        :key="`${browser.state.url}-${frameKey}`"
        :src="browser.state.url"
        :title="heading"
        class="size-full border-0 bg-default"
        referrerpolicy="strict-origin-when-cross-origin"
        sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-forms"
        @load="loaded"
      />
    </template>

    <template #footer>
      <div class="flex w-full flex-wrap items-center justify-between gap-2 text-xs text-muted">
        <span class="flex items-center gap-1.5"><UIcon :name="sent ? 'i-lucide-circle-check' : 'i-lucide-shield-check'" class="size-3.5 shrink-0" :class="sent ? 'text-success' : ''" />{{ sent ? t('appBrowser.sentNote') : t('appBrowser.safe') }}</span>
        <UButton :label="t('appBrowser.back')" icon="i-lucide-arrow-left" color="neutral" variant="link" size="xs" class="px-0 rtl:[&_svg]:rotate-180" @click="leave" />
      </div>
    </template>
  </AppModal>
</template>
