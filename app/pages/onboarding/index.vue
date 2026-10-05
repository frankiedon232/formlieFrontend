<!--
  Workspace set-up wizard (PROGRESS.md F5): company · branding · regional settings · team · first form.
  Every step is optional; the server remembers progress so the admin resumes where they left off.
  Each step renders <UForm id="onboarding-step">; the footer's Continue submits it.
-->
<script setup lang="ts">
import type { StepperItem } from '@nuxt/ui'
import { ONBOARDING_STEPS, type OnboardingStep } from '#shared/types/onboarding'
import { COUNTRY_CURRENCIES } from '#shared/utils/platform/countries'

definePageMeta({ layout: 'onboarding', breadcrumb: 'onboarding.title' })

const { t } = useI18n()
const session = useSession()
const { current: uiLocale } = useAppLocale()
const onboarding = useOnboarding()
const { state, loading, saving } = onboarding
useHead({ title: () => t('onboarding.title') })

const STEP_ICONS: Record<OnboardingStep, string> = {
  company: 'i-lucide-building-2',
  branding: 'i-lucide-palette',
  localisation: 'i-lucide-globe',
  team: 'i-lucide-users',
  first_form: 'i-lucide-file-plus',
}

const draft = ref<OnboardingDraft | null>(null)
const index = ref(0)
const step = computed<OnboardingStep>(() => ONBOARDING_STEPS[index.value]!)
const isLast = computed(() => index.value === ONBOARDING_STEPS.length - 1)

const items = computed<StepperItem[]>(() =>
  ONBOARDING_STEPS.map(key => ({
    value: ONBOARDING_STEPS.indexOf(key),
    title: t(`onboarding.steps.${key}.title`),
    icon: state.value?.steps[key] === 'done' ? 'i-lucide-check' : STEP_ICONS[key],
  })),
)
const doneCount = computed(() =>
  state.value ? Object.values(state.value.steps).filter(status => status !== 'todo').length : 0,
)

onMounted(async () => {
  if (session.user.value?.role === 'member') return navigateTo('/forms', { replace: true })
  await onboarding.load()
  if (!state.value) return
  draft.value = createOnboardingDraft(state.value, uiLocale.value.code)
  index.value = state.value.status === 'completed' ? 0 : ONBOARDING_STEPS.indexOf(state.value.current_step)
})

// While regional settings are untouched, follow the company's country.
watch(
  () => draft.value?.company.country,
  country => {
    if (!draft.value || !country || state.value?.steps.localisation === 'done') return
    Object.assign(draft.value.localisation, {
      currency: COUNTRY_CURRENCIES[country] ?? draft.value.localisation.currency,
      date_format: suggestDateFormat(country),
      number_format: suggestNumberFormat(country),
      week_start: suggestWeekStart(country),
    })
  },
)

async function done() {
  if (!(await onboarding.finish())) return
  const choice = draft.value?.first_form
  await navigateTo(
    choice?.choice === 'template'
      ? { path: '/forms/new', query: { template: choice.template_key ?? undefined } }
      : choice?.choice === 'blank'
        ? '/forms/new'
        : '/forms',
  )
}

async function save() {
  if (!draft.value) return
  if (!(await onboarding.patch(onboardingPatchFor(step.value, draft.value)))) return
  if (isLast.value) return done()
  index.value++
}

async function skip() {
  if (!(await onboarding.skip(step.value))) return
  if (isLast.value) return done()
  index.value++
}
</script>

<template>
  <div class="flex flex-col gap-6 sm:gap-8">
    <div class="flex flex-col gap-2">
      <h1 class="text-2xl font-semibold tracking-tight text-highlighted sm:text-3xl">
        {{ t('onboarding.heading', { name: session.tenant.value?.name ?? '' }) }}
      </h1>
      <p class="text-muted">{{ t('onboarding.subheading') }}</p>
    </div>

    <template v-if="loading || !draft">
      <USkeleton class="h-14 w-full" />
      <div class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_360px]">
        <USkeleton class="h-96 w-full" />
        <USkeleton class="hidden h-80 w-full lg:block" />
      </div>
    </template>

    <AppEmpty
      v-else-if="onboarding.error.value && !state"
      icon="i-lucide-cloud-alert"
      :title="t('dataView.errorTitle')"
      :actions="[
        { label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: onboarding.load },
      ]"
      variant="outline"
    />

    <template v-else>
      <div>
        <div class="mb-3 flex items-center justify-between gap-2 text-sm sm:hidden">
          <span class="font-medium text-highlighted">{{ items[index]?.title }}</span>
          <span class="text-muted">{{ t('onboarding.stepOf', { n: index + 1, total: items.length }) }}</span>
        </div>
        <UProgress
          :model-value="doneCount"
          :max="items.length"
          color="neutral"
          size="xs"
          class="sm:hidden"
          :aria-label="t('onboarding.progress', { done: doneCount, total: items.length })"
        />
        <!-- Every step is optional, so any step can be opened directly. -->
        <UStepper
          v-model="index"
          :items="items"
          :linear="false"
          color="neutral"
          size="sm"
          class="hidden w-full sm:flex"
        />
      </div>

      <div class="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_360px]">
        <UCard :ui="{ body: 'p-5 sm:p-6', footer: 'p-4 sm:px-6' }">
          <div class="mb-6">
            <h2 class="text-lg font-semibold text-highlighted">{{ t(`onboarding.steps.${step}.title`) }}</h2>
            <p class="mt-1 text-sm text-muted">{{ t(`onboarding.steps.${step}.desc`) }}</p>
          </div>

          <OnboardingCompanyStep v-if="step === 'company'" v-model="draft.company" @submit="save" />
          <OnboardingBrandingStep v-else-if="step === 'branding'" v-model="draft.branding" @submit="save" />
          <OnboardingLocalisationStep
            v-else-if="step === 'localisation'"
            v-model="draft.localisation"
            @submit="save"
          />
          <OnboardingTeamStep v-else-if="step === 'team'" v-model="draft.invites" @submit="save" />
          <OnboardingFirstFormStep v-else v-model="draft.first_form" @submit="save" />

          <template #footer>
            <div class="flex flex-col-reverse gap-2 sm:flex-row sm:items-center">
              <UButton
                v-if="index > 0"
                :label="t('common.back')"
                icon="i-lucide-arrow-left"
                color="neutral"
                variant="ghost"
                class="justify-center rtl:[&_svg]:rotate-180"
                :disabled="saving"
                @click="index--"
              />
              <UButton
                :label="t('onboarding.skip')"
                color="neutral"
                variant="link"
                class="justify-center sm:ms-auto"
                :disabled="saving"
                @click="skip"
              />
              <UButton
                type="submit"
                form="onboarding-step"
                :label="isLast ? t('onboarding.finish') : t('onboarding.continue')"
                :trailing-icon="isLast ? 'i-lucide-check' : 'i-lucide-arrow-right'"
                color="neutral"
                class="justify-center rtl:[&_svg]:rotate-180"
                :loading="saving"
              />
            </div>
          </template>
        </UCard>

        <OnboardingPreview :step="step" :draft="draft" class="hidden lg:block lg:sticky lg:top-24" />
      </div>
    </template>
  </div>
</template>
