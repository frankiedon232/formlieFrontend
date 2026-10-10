<!--
  Page editor (Resources → Landing pages; owner 2026-10-04): create or change a page design, the page around
  a form on its public link, without a form. The designer's own Page and Background controls on a
  sample form, live preview with the page frame on desktop / tablet / phone. `/settings/landing-pages/new`
  creates a "created" design; an id opens it. Formalie's designs open read-only (preview +
  "Duplicate to edit"). Saving without a name shows the field; leaving with changes asks first.
-->
<script setup lang="ts">
import type { PageDesign } from '#shared/types/forms'
import { systemTemplate, templateSchema } from '#shared/templates'
import { pageTokensOf, withPageDesign, type PageDesignTokens } from '#shared/utils/forms/page-design'
import { defaultTheme, resolveTheme } from '#shared/utils/forms/theme'

definePageMeta({ breadcrumb: 'pages.editor.crumb' })
const { t } = useI18n()
const route = useRoute()
const library = usePageDesigns()
const branding = useWorkspaceBranding()
const confirm = useConfirm()
const toast = useToast()
const { setLabel } = useBreadcrumbs()
const { handle } = useErrorHandler()

const id = computed(() => String(route.params.id ?? 'new'))
const isNew = computed(() => id.value === 'new')
const page = ref<PageDesign | null>(null)
const name = ref('')
const loading = ref(true)
const notFound = ref(false)

// A sample form to show the page around; only the page tokens of its theme are edited.
const builder = useFormBuilder()
provideFormBuilder(builder)
function load(tokens?: PageDesignTokens) {
  const { theme: _sampleDesign, ...sample } = templateSchema(systemTemplate('contact_lead')!)
  const base = defaultTheme(branding.value)
  builder.load({ ...sample, theme: (tokens ? withPageDesign(base, tokens) : base) as unknown as Record<string, unknown> })
}
const tokens = () => pageTokensOf(resolveTheme(structuredClone(toRaw(builder.schema.value?.theme)), branding.value))
const saved = ref('')
const snapshot = () => JSON.stringify({ name: name.value.trim(), tokens: builder.schema.value ? tokens() : null })
const dirty = computed(() => !loading.value && page.value?.source !== 'system' && snapshot() !== saved.value)

onMounted(async () => {
  try {
    if (isNew.value) load()
    else {
      page.value = await library.get(id.value)
      name.value = library.nameOf(page.value)
      load(page.value.tokens)
    }
    saved.value = snapshot()
  } catch (error) {
    notFound.value = true
    handle(error, { silent: true })
  } finally {
    loading.value = false
  }
})
watch(name, value => setLabel(route.path, value.trim() || t('pages.editor.untitled')), { immediate: true })
useHead({ title: () => name.value.trim() || t('pages.editor.newTitle') })

/** Formalie's own designs, and pages this person may not change (F22 R2 M3), can be looked at, and copied with "duplicate". */
const readOnly = computed(() => !!page.value && !page.value.can?.edit)
const { busy: duplicating, run: runDuplicate } = useBusy()
async function duplicateToEdit() {
  if (!page.value) return
  const copy = await runDuplicate(() => library.duplicate({ id: page.value!.id, name: name.value }))
  if (copy) await navigateTo(`/settings/landing-pages/${copy.id}`)
}

const large = useMediaQuery('(min-width: 1024px)')
const panelOpen = ref(false)
const nameError = ref<string | undefined>()
watch(name, value => value.trim() && (nameError.value = undefined))
const { busy, run } = useBusy()
async function save() {
  const trimmed = name.value.trim()
  nameError.value = trimmed ? undefined : t('library.nameRequired')
  if (!trimmed) {
    toast.add({ title: t('pages.editor.nameFirst'), icon: 'i-lucide-pencil-line', color: 'warning' })
    if (!large.value) panelOpen.value = true
    await nextTick()
    setTimeout(() => revealField(large.value ? 'page-name' : 'page-name-panel'), large.value ? 0 : 250)
    return
  }
  const result = await run(() => (isNew.value ? library.create(trimmed, tokens(), 'created') : library.update(id.value, { name: trimmed, tokens: tokens() })))
  if (!result) return
  page.value = result
  name.value = library.nameOf(result)
  saved.value = snapshot()
  if (isNew.value) await navigateTo(`/settings/landing-pages/${result.id}`, { replace: true })
}
onBeforeRouteLeave(async () => {
  if (!dirty.value || busy.value) return true
  return await confirm({ title: t('themes.editor.leaveTitle'), description: t('themes.editor.leaveDesc'), confirmLabel: t('themes.editor.leave'), danger: true })
})
defineShortcuts({ meta_s: { usingInput: true, handler: () => void (readOnly.value ? undefined : save()) } })

const device = ref<'desktop' | 'tablet' | 'phone'>('desktop')
const devices = computed(() => [
  { value: 'desktop', label: t('builder.preview.desktop'), icon: 'i-lucide-monitor' },
  { value: 'tablet', label: t('builder.preview.tablet'), icon: 'i-lucide-tablet' },
  { value: 'phone', label: t('builder.preview.phone'), icon: 'i-lucide-smartphone' },
])
const WIDTH = { desktop: 'max-w-full', tablet: 'max-w-[768px]', phone: 'max-w-[390px]' }
</script>

<template>
  <AppPanel
    id="page-editor"
    :title="name.trim() || (isNew ? t('pages.editor.newTitle') : t('pages.editor.untitled'))"
    :subtitle="readOnly ? t('pages.editor.systemDesc') : dirty ? t('themes.editor.unsaved') : isNew ? t('pages.editor.newDesc') : t('themes.editor.savedState')"
    :subtitle-icon="dirty ? 'i-lucide-circle-dot' : 'i-lucide-panels-top-left'"
  >
    <template v-if="readOnly" #actions>
      <UButton :label="t('nav.pagesAll')" icon="i-lucide-arrow-left" color="neutral" variant="outline" to="/settings/landing-pages" class="rtl:[&_.iconify]:-scale-x-100" />
      <UButton v-if="useCan().can('pages.duplicate')" :label="t('themes.duplicateToEdit')" icon="i-lucide-copy-plus" color="neutral" :loading="duplicating" @click="duplicateToEdit" />
    </template>
    <template v-else #actions>
      <UButton :label="t('common.cancel')" icon="i-lucide-x" color="neutral" variant="outline" to="/settings/landing-pages" />
      <UTooltip :text="t('pages.editor.save')" :kbds="['meta', 's']">
        <UButton :label="t('pages.editor.save')" icon="i-lucide-check" color="neutral" :loading="busy" :disabled="loading || notFound" @click="save" />
      </UTooltip>
    </template>

    <div v-if="loading" class="grid gap-4 lg:grid-cols-[340px_minmax(0,1fr)]" :aria-label="t('common.loading')">
      <USkeleton class="hidden h-[70vh] lg:block" />
      <USkeleton class="h-[70vh] w-full" />
    </div>

    <AppEmpty
      v-else-if="notFound"
      icon="i-lucide-panels-top-left"
      :title="t('pages.editor.notFound')"
      :actions="[{ label: t('nav.pagesAll'), icon: 'i-lucide-arrow-left', to: '/settings/landing-pages', color: 'neutral', variant: 'subtle', class: 'rtl:[&_.iconify]:-scale-x-100' }]"
      class="my-auto"
    />

    <div v-else-if="builder.schema.value" class="grid items-start gap-4" :class="readOnly ? '' : 'lg:grid-cols-[340px_minmax(0,1fr)]'">
      <UAlert v-if="readOnly" icon="i-lucide-sparkles" color="neutral" variant="soft" :title="t('pages.editor.systemTitle')" :description="t('pages.editor.systemHint')" />
      <UCard v-if="large && !readOnly" class="sticky top-0" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-4 overflow-y-auto h-[calc(100dvh-11rem)]' }">
        <UFormField :label="t('pages.editor.name')" :error="nameError" required>
          <UInput id="page-name" v-model="name" maxlength="80" :placeholder="t('pages.editor.namePlaceholder')" class="w-full" autofocus />
        </UFormField>
        <PageDesignsControls />
      </UCard>

      <div class="mb-20 flex min-w-0 flex-col gap-3 rounded-xl bg-elevated/40 p-2 sm:p-3 lg:mb-0">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="text-xs text-muted">{{ t('pages.editor.sample') }}</span>
          <UTabs v-model="device" :items="devices" :content="false" color="neutral" size="xs" :ui="{ ...SEGMENTED_UI, label: 'hidden md:inline' }" class="hidden sm:flex" :aria-label="t('builder.preview.device')" />
        </div>
        <div class="mx-auto h-[calc(100dvh-14rem)] min-h-96 w-full overflow-y-auto rounded-lg border border-default transition-[max-width] duration-300 @container" :class="WIDTH[device]">
          <FormsRendererPage :schema="builder.schema.value" :title="t('themes.editor.sampleTitle')" preview framed />
        </div>
      </div>

      <!-- Phones / tablets: the controls open from a floating bar (same as the theme editor). -->
      <template v-if="!large && !readOnly">
        <div class="fixed inset-x-0 bottom-4 z-20 flex justify-center">
          <UButton :label="t('pages.editor.controls')" icon="i-lucide-panels-top-left" color="neutral" size="lg" class="rounded-full shadow-lg" @click="panelOpen = true" />
        </div>
        <USlideover v-model:open="panelOpen" :title="t('pages.editor.controls')" side="left">
          <template #body>
            <div class="flex flex-col gap-4">
              <UFormField :label="t('pages.editor.name')" :error="nameError" required>
                <UInput id="page-name-panel" v-model="name" maxlength="80" :placeholder="t('pages.editor.namePlaceholder')" class="w-full" />
              </UFormField>
              <PageDesignsControls />
            </div>
          </template>
        </USlideover>
      </template>
    </div>
  </AppPanel>
</template>
