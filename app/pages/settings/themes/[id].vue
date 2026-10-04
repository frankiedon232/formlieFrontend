<!--
  Theme editor (F9 milestone 2): create or change a workspace theme without a form, the full
  designer on a sample form, live preview on desktop / tablet / phone and the thank-you page.
  `/settings/themes/new` creates a "created" theme; an id opens it. Formalie's system themes open
  read-only (preview + "Duplicate to edit"). Leaving with unsaved changes asks first.
-->
<script setup lang="ts">
import type { SavedTheme } from '#shared/types/forms'
import { systemTemplate, templateSchema } from '#shared/templates'
import { resolveTheme, type FormTheme } from '#shared/utils/forms/theme'

definePageMeta({ breadcrumb: 'themes.editor.crumb' })
const { t } = useI18n()
const route = useRoute()
const library = useThemes()
const branding = useWorkspaceBranding()
const confirm = useConfirm()
const { setLabel } = useBreadcrumbs()
const { handle } = useErrorHandler()

const id = computed(() => String(route.params.id ?? 'new'))
const isNew = computed(() => id.value === 'new')
const theme = ref<SavedTheme | null>(null)
const name = ref('')
const loading = ref(true)
const notFound = ref(false)

// A sample form to design on (a template everyone recognises), holding the theme being edited.
const builder = useFormBuilder()
provideFormBuilder(builder)
/** No tokens = a new theme: it starts from the workspace default, so a starting point applies without asking. */
function load(tokens?: FormTheme) {
  const { theme: _sampleDesign, ...sample } = templateSchema(systemTemplate('contact_lead')!)
  builder.load(
    tokens ? { ...sample, theme: structuredClone(tokens) as unknown as Record<string, unknown> } : sample,
  )
}
const saved = ref('')
const snapshot = () =>
  JSON.stringify({ name: name.value.trim(), tokens: builder.schema.value?.theme ?? null })
const dirty = computed(() => !loading.value && theme.value?.source !== 'system' && snapshot() !== saved.value)

onMounted(async () => {
  try {
    if (isNew.value) {
      name.value = ''
      load()
    } else {
      theme.value = await library.get(id.value)
      name.value = library.nameOf(theme.value)
      load(resolveTheme(theme.value.tokens, branding.value))
    }
    saved.value = snapshot()
  } catch (error) {
    notFound.value = true
    handle(error, { silent: true })
  } finally {
    loading.value = false
  }
})
watch(name, value => setLabel(route.path, value.trim() || t('themes.editor.untitled')), { immediate: true })
useHead({ title: () => name.value.trim() || t('themes.editor.newTitle') })

/** Formalie's own designs can be looked at and copied, not changed. */
const readOnly = computed(() => theme.value?.source === 'system')
const { busy: duplicating, run: runDuplicate } = useBusy()
async function duplicateToEdit() {
  if (!theme.value) return
  const copy = await runDuplicate(() => library.duplicate({ id: theme.value!.id, name: name.value }))
  if (copy) await navigateTo(`/settings/themes/${copy.id}`)
}

const nameError = ref<string | undefined>()
watch(name, value => value.trim() && (nameError.value = undefined))
const { busy, run } = useBusy()
const toast = useToast()
/**
 * Saving without a name (owner 2026-10-04): the field sits at the top of a scrolling panel, so
 * bring it into view and focus it (phones: open the panel first), and say why in a toast.
 */
async function showNameField() {
  toast.add({ title: t('themes.editor.nameFirst'), icon: 'i-lucide-pencil-line', color: 'warning' })
  if (!large.value) panelOpen.value = true
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, large.value ? 0 : 250))
  const field = document.getElementById(large.value ? 'theme-name' : 'theme-name-panel')
  if (!field) return
  // Scroll the panel that holds it (scrollIntoView doesn't move nested scroll areas reliably).
  let box = field.parentElement
  while (box && !(box.scrollHeight > box.clientHeight && /auto|scroll/.test(getComputedStyle(box).overflowY)))
    box = box.parentElement
  field.focus({ preventScroll: true })
  if (!box) return field.scrollIntoView({ block: 'center' })
  const top = Math.max(
    0,
    box.scrollTop + field.getBoundingClientRect().top - box.getBoundingClientRect().top - 48,
  )
  box.scrollTo({ top, behavior: 'smooth' })
  // Some browsers ignore smooth scrolling here; jump instead if nothing moved.
  const from = box.scrollTop
  setTimeout(
    () => box && Math.abs(box.scrollTop - top) > 4 && box.scrollTop === from && box.scrollTo({ top }),
    350,
  )
}
async function save() {
  const trimmed = name.value.trim()
  nameError.value = trimmed ? undefined : t('library.nameRequired')
  if (!trimmed) return showNameField()
  // The designer writes the full theme into the sample form; resolve fills anything missing.
  const tokens = resolveTheme(structuredClone(toRaw(builder.schema.value?.theme)), branding.value)
  const result = await run(() =>
    isNew.value
      ? library.create(trimmed, tokens, 'created')
      : library.update(id.value, { name: trimmed, tokens }),
  )
  if (!result) return
  theme.value = result
  name.value = result.name
  saved.value = snapshot()
  if (isNew.value) await navigateTo(`/settings/themes/${result.id}`, { replace: true })
}

onBeforeRouteLeave(async () => {
  if (!dirty.value || busy.value) return true
  return await confirm({
    title: t('themes.editor.leaveTitle'),
    description: t('themes.editor.leaveDesc'),
    confirmLabel: t('themes.editor.leave'),
    danger: true,
  })
})
defineShortcuts({ meta_s: { usingInput: true, handler: () => void (readOnly.value ? undefined : save()) } })

const device = ref<'desktop' | 'tablet' | 'phone'>('desktop')
const devices = computed(() => [
  { value: 'desktop', label: t('builder.preview.desktop'), icon: 'i-lucide-monitor' },
  { value: 'tablet', label: t('builder.preview.tablet'), icon: 'i-lucide-tablet' },
  { value: 'phone', label: t('builder.preview.phone'), icon: 'i-lucide-smartphone' },
])
const WIDTH = { desktop: 'max-w-full', tablet: 'max-w-[768px]', phone: 'max-w-[390px]' }
const screen = ref<'form' | 'thanks'>('form')
const screens = computed(() => [
  { value: 'form', label: t('designer.screen.form') },
  { value: 'thanks', label: t('designer.screen.thanks') },
])
const large = useMediaQuery('(min-width: 1024px)')
const panelOpen = ref(false)
</script>

<template>
  <AppPanel
    id="theme-editor"
    :title="name.trim() || (isNew ? t('themes.editor.newTitle') : t('themes.editor.untitled'))"
    :subtitle="
      readOnly
        ? t('themes.editor.systemDesc')
        : dirty
          ? t('themes.editor.unsaved')
          : isNew
            ? t('themes.editor.newDesc')
            : t('themes.editor.savedState')
    "
    :subtitle-icon="dirty ? 'i-lucide-circle-dot' : 'i-lucide-palette'"
  >
    <template v-if="readOnly" #actions>
      <UButton
        :label="t('nav.themesAll')"
        icon="i-lucide-arrow-left"
        color="neutral"
        variant="outline"
        to="/settings/themes"
      />
      <UButton
        :label="t('themes.duplicateToEdit')"
        icon="i-lucide-copy-plus"
        color="neutral"
        :loading="duplicating"
        @click="duplicateToEdit"
      />
    </template>
    <template v-else #actions>
      <UButton
        :label="t('common.cancel')"
        icon="i-lucide-x"
        color="neutral"
        variant="outline"
        to="/settings/themes"
      />
      <UTooltip :text="t('themes.editor.save')" :kbds="['meta', 's']">
        <UButton
          :label="t('themes.editor.save')"
          icon="i-lucide-check"
          color="neutral"
          :loading="busy"
          :disabled="loading || notFound"
          @click="save"
        />
      </UTooltip>
    </template>

    <div
      v-if="loading"
      class="grid gap-4 lg:grid-cols-[340px_minmax(0,1fr)]"
      :aria-label="t('common.loading')"
    >
      <USkeleton class="hidden h-[70vh] lg:block" />
      <USkeleton class="h-[70vh] w-full" />
    </div>

    <UEmpty
      v-else-if="notFound"
      icon="i-lucide-palette"
      :title="t('themes.editor.notFound')"
      :actions="[
        {
          label: t('nav.themesAll'),
          icon: 'i-lucide-arrow-left',
          to: '/settings/themes',
          color: 'neutral',
          variant: 'subtle',
        },
      ]"
      class="my-auto"
    />

    <div
      v-else-if="builder.schema.value"
      class="grid items-start gap-4"
      :class="readOnly ? '' : 'lg:grid-cols-[340px_minmax(0,1fr)]'"
    >
      <UAlert
        v-if="readOnly"
        icon="i-lucide-sparkles"
        color="neutral"
        variant="soft"
        :title="t('themes.editor.systemTitle')"
        :description="t('themes.editor.systemHint')"
      />
      <UCard
        v-if="large && !readOnly"
        class="sticky top-0"
        :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-4 overflow-y-auto h-[calc(100dvh-11rem)]' }"
      >
        <UFormField :label="t('themes.editor.name')" :error="nameError" required>
          <UInput
            id="theme-name"
            v-model="name"
            maxlength="80"
            :placeholder="t('themes.namePlaceholder')"
            class="w-full"
            autofocus
          />
        </UFormField>
        <FormsDesignerPanel standalone />
      </UCard>

      <div class="mb-20 flex min-w-0 flex-col gap-3 rounded-xl bg-elevated/40 p-2 sm:p-3 lg:mb-0">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <UTabs
            v-model="screen"
            :items="screens"
            :content="false"
            color="neutral"
            size="xs"
            :ui="SEGMENTED_UI"
            :aria-label="t('designer.screen.label')"
          />
          <span class="hidden text-xs text-muted md:inline">{{ t('themes.editor.sample') }}</span>
          <UTabs
            v-model="device"
            :items="devices"
            :content="false"
            color="neutral"
            size="xs"
            :ui="{ ...SEGMENTED_UI, label: 'hidden md:inline' }"
            class="hidden sm:flex"
            :aria-label="t('builder.preview.device')"
          />
        </div>
        <div
          class="mx-auto h-[calc(100dvh-14rem)] min-h-96 w-full overflow-y-auto rounded-lg border border-default transition-[max-width] duration-300 @container"
          :class="WIDTH[device]"
        >
          <FormsRendererPage
            :schema="builder.schema.value"
            :title="name.trim() || t('themes.editor.sampleTitle')"
            preview
            :show-thank-you="screen === 'thanks'"
          />
        </div>
      </div>

      <!-- Phones / tablets: the controls open from a floating bar (same as the form designer). -->
      <template v-if="!large && !readOnly">
        <div class="fixed inset-x-0 bottom-4 z-20 flex justify-center">
          <UButton
            :label="t('builder.mode.design')"
            icon="i-lucide-palette"
            color="neutral"
            size="lg"
            class="rounded-full shadow-lg"
            @click="panelOpen = true"
          />
        </div>
        <USlideover v-model:open="panelOpen" :title="t('builder.mode.design')" side="left">
          <template #body>
            <div class="flex flex-col gap-4">
              <UFormField :label="t('themes.editor.name')" :error="nameError" required>
                <UInput
                  id="theme-name-panel"
                  v-model="name"
                  maxlength="80"
                  :placeholder="t('themes.namePlaceholder')"
                  class="w-full"
                />
              </UFormField>
              <FormsDesignerPanel standalone />
            </div>
          </template>
        </USlideover>
      </template>
    </div>
  </AppPanel>
</template>
