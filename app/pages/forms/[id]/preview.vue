<!--
  Preview page (F10 M3 item 6): the form exactly as respondents see it, inside a phone, a tablet
  (portrait or turned sideways) or a desktop browser window. Draft or live version, jump to any
  page or the thank-you screen, fill it in to try the rules and logic: nothing is sent or saved.
  Open to "Can view" and up (decision 97); phones show the form full width without a frame.
-->
<script setup lang="ts">
import type { FormPreview } from '#shared/types/forms'
import { formLanguages, translateSchema } from '#shared/utils/forms/translations'
import { formLink, publicHosts } from '#shared/utils/urls/public'
import { channelsOf } from '#shared/types/forms'

definePageMeta({ breadcrumb: 'preview.crumb' })

const { t } = useI18n()
const route = useRoute()
const api = useApi()
const { handle } = useErrorHandler()
const { setLabel } = useBreadcrumbs()
const id = String(route.params.id)

const data = ref<FormPreview | null>(null)
const loading = ref(true)
const failed = ref<string | null>(null)
useHead({ title: () => (data.value ? `${data.value.form.name} · ${t('preview.crumb')}` : t('preview.crumb')) })

/** Draft or the version respondents fill in now. Editors start on the draft, everyone else on live. */
const version = ref<'draft' | 'live'>('draft')
async function load() {
  loading.value = true
  failed.value = null
  try {
    data.value = (await api.get<FormPreview>(`/forms/${id}/preview`)).data
    setLabel(`/forms/${id}`, data.value.form.name)
    const asked = route.query.v
    version.value = data.value.live && (asked === 'live' || (asked !== 'draft' && !canEditForm(data.value.form))) ? 'live' : 'draft'
  } catch (error) {
    failed.value = handle(error, { silent: true }).code
  } finally {
    loading.value = false
  }
}
onMounted(load)

const base = computed(() => (version.value === 'live' ? data.value?.live : data.value?.draft) ?? null)
// Forms in several languages (decision 99): the switcher on the form, like respondents get it.
const languages = computed(() => formLanguages(base.value))
const language = ref('')
// Starts in the form's main language, and again when the main language changes (or the form loads).
watch(
  languages,
  (offered, before) => {
    if (!offered.includes(language.value) || offered[0] !== before?.[0]) language.value = offered[0] ?? 'en'
  },
  { immediate: true },
)
const schema = computed(() => (base.value ? translateSchema(base.value, language.value) : null))
const versions = computed(() => [
  { value: 'draft', label: t('preview.draft'), icon: 'i-lucide-pencil-line' },
  { value: 'live', label: t('preview.live', { n: data.value?.published_version ?? 1 }), icon: 'i-lucide-globe' },
])

// Device (remembered on this browser), sideways, and phones without a frame.
const device = useLocalStorage<'desktop' | 'tablet' | 'phone'>('formalie.preview.device', 'desktop')
const landscape = ref(false)
const devices = computed(() => [
  { value: 'desktop', label: t('builder.preview.desktop'), icon: 'i-lucide-monitor' },
  { value: 'tablet', label: t('builder.preview.tablet'), icon: 'i-lucide-tablet' },
  { value: 'phone', label: t('builder.preview.phone'), icon: 'i-lucide-smartphone' },
])
const small = useMediaQuery('(max-width: 639px)')

// Where the respondent is, and jumping anywhere (answers kept). Start again = a fresh form.
const at = ref<number | 'thanks'>(0)
const goTo = ref<{ at: number | 'thanks'; n: number }>()
const fresh = ref(0)
const pages = computed(() => [
  ...(schema.value?.pages ?? []).map((page, index) => ({
    value: index,
    label: page.title?.trim() || t('preview.page', { n: index + 1 }),
    icon: 'i-lucide-file',
  })),
  { value: 'thanks' as const, label: t('designer.screen.thanks'), icon: 'i-lucide-party-popper' },
])
const jump = (value: number | 'thanks') => (goTo.value = { at: value, n: (goTo.value?.n ?? 0) + 1 })
function restart() {
  fresh.value++
  at.value = 0
}
watch(version, restart)

const config = useRuntimeConfig().public
const tenant = useTenant()
const request = useRequestURL()
const address = computed(() => {
  if (!data.value) return ''
  const link = formLink(publicHosts(config, request.port), data.value.form.custom_link || data.value.form.public_key, 'fill', tenant.profile.value?.subdomain ?? null)
  return language.value && language.value !== languages.value[0] ? `${link}?lang=${language.value}` : link
})

defineShortcuts({
  '1': () => (device.value = 'desktop'),
  '2': () => (device.value = 'tablet'),
  '3': () => (device.value = 'phone'),
  r: () => device.value !== 'desktop' && (landscape.value = !landscape.value),
})
</script>

<template>
  <AppPanel id="form-preview" :title="data?.form.name ?? t('preview.crumb')" :subtitle="t('preview.subtitle')" subtitle-icon="i-lucide-eye">
    <template v-if="data" #actions>
      <UTabs
        v-if="data.live"
        v-model="version"
        :items="versions"
        :content="false"
        color="neutral"
        size="sm"
        :ui="{ ...SEGMENTED_UI, label: 'hidden lg:inline' }"
        :aria-label="t('preview.version')"
      />
      <UButton
        v-if="data.live && version === 'live' && channelsOf(data.form).includes('link')"
        :to="address"
        external
        target="_blank"
        icon="i-lucide-external-link"
        :label="t('preview.openLive')"
        color="neutral"
        variant="outline"
        :ui="{ label: 'hidden md:inline' }"
      />
      <UButton v-if="canEditForm(data.form)" icon="i-lucide-pencil-ruler" :label="t('forms.detail.edit')" color="neutral" :to="`/forms/${id}/build`" :ui="{ label: 'hidden sm:inline' }" />
    </template>

    <div v-if="loading" class="flex flex-col gap-3" :aria-label="t('common.loading')">
      <div class="flex justify-between gap-2">
        <USkeleton class="h-8 w-48" />
        <USkeleton class="hidden h-8 w-64 sm:block" />
      </div>
      <USkeleton class="h-[calc(100dvh-16rem)] min-h-96 w-full rounded-lg" />
    </div>

    <AppEmpty
      v-else-if="failed || !schema"
      icon="i-lucide-file-question"
      :title="failed === 'FRM-GEN-1004' ? t('forms.detail.notFound') : t('dataView.errorTitle')"
      :actions="[
        ...(failed === 'FRM-GEN-1004' ? [] : [{ label: t('common.retry'), color: 'neutral' as const, variant: 'outline' as const, onClick: load }]),
        { label: t('nav.forms'), to: '/forms', color: 'neutral' as const },
      ]"
      variant="outline"
    />

    <div v-else class="flex flex-col gap-3">
      <!-- Preview controls: where you are, start again, device and orientation. -->
      <div class="flex flex-wrap items-center gap-2">
        <USelectMenu
          :model-value="at"
          :items="pages"
          value-key="value"
          :search-input="false"
          icon="i-lucide-file-stack"
          size="sm"
          class="w-44 sm:w-56"
          :aria-label="t('preview.goTo')"
          @update:model-value="value => jump(value as number | 'thanks')"
        />
        <UTooltip :text="t('builder.preview.restart')">
          <UButton icon="i-lucide-rotate-ccw" color="neutral" variant="outline" size="sm" square :aria-label="t('builder.preview.restart')" @click="restart" />
        </UTooltip>
        <UBadge :label="t('preview.nothingSent')" icon="i-lucide-shield-check" color="neutral" variant="subtle" class="hidden md:inline-flex" />
        <div class="ms-auto hidden items-center gap-2 sm:flex">
          <UTooltip v-if="device !== 'desktop'" :text="t('preview.rotate')" :kbds="['r']">
            <UButton
              icon="i-lucide-rotate-cw-square"
              color="neutral"
              variant="outline"
              size="sm"
              square
              :aria-label="t('preview.rotate')"
              :aria-pressed="landscape"
              :class="landscape ? 'bg-elevated' : ''"
              @click="landscape = !landscape"
            />
          </UTooltip>
          <UTabs
            v-model="device"
            :items="devices"
            :content="false"
            color="neutral"
            size="sm"
            :ui="{ ...SEGMENTED_UI, label: 'hidden lg:inline' }"
            :aria-label="t('builder.preview.device')"
          />
        </div>
      </div>

      <!-- Phones: the form itself, full width. -->
      <div v-if="small" class="overflow-hidden rounded-lg border border-default @container">
        <FormsRendererPage :key="`${version}-${fresh}`" :schema="schema" :title="data!.form.name" preview framed :go-to="goTo" :languages="languages" :language="language" @at="at = $event" @language="language = $event" />
      </div>
      <div v-else class="h-[calc(100dvh-15rem)] min-h-[28rem] rounded-lg bg-elevated/40 p-3 sm:p-4">
        <FormsPreviewDevice :device="device" :landscape="landscape" :address="address">
          <FormsRendererPage :key="`${version}-${fresh}`" :schema="schema" :title="data!.form.name" preview framed :go-to="goTo" :languages="languages" :language="language" @at="at = $event" @language="language = $event" />
        </FormsPreviewDevice>
      </div>
    </div>
  </AppPanel>
</template>
