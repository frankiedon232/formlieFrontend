<!-- Live preview beside the wizard (lg+): what each step changes, before it is saved. -->
<script setup lang="ts">
import type { OnboardingStep } from '#shared/types/onboarding'
import { STARTER_TEMPLATES } from '#shared/utils/templates/starters'

const props = defineProps<{ step: OnboardingStep; draft: OnboardingDraft }>()
const { t } = useI18n()
const session = useSession()
const config = useRuntimeConfig()

const name = computed(() => props.draft.company.name || session.tenant.value?.name || '')
const initial = computed(() => name.value.trim().charAt(0).toUpperCase() || 'F')
const brand = computed(() => props.draft.branding.brand_color ?? '#18181B')
const host = computed(() => `${session.tenant.value?.subdomain ?? 'workspace'}.${config.public.rootDomain}`)

const loc = computed(() => props.draft.localisation)
const now = new Date()
const samples = computed(() => {
  const { language, timezone, currency, date_format, number_format } = loc.value
  const symbol =
    new Intl.NumberFormat(language, { style: 'currency', currency, currencyDisplay: 'narrowSymbol' })
      .formatToParts(0)
      .find(part => part.type === 'currency')?.value ?? currency
  return [
    { label: t('onboarding.preview.date'), value: formatDatePattern(now, date_format, timezone) },
    {
      label: t('onboarding.preview.time'),
      value: new Intl.DateTimeFormat(language, { timeStyle: 'short', timeZone: timezone }).format(now),
    },
    { label: t('onboarding.preview.number'), value: formatNumberPattern(1234567.89, number_format) },
    { label: t('onboarding.preview.price'), value: `${symbol} ${formatNumberPattern(49.9, number_format)}` },
  ]
})
const weekDays = computed(() => {
  const first = { monday: 1, sunday: 0, saturday: 6 }[loc.value.week_start]
  const formatter = new Intl.DateTimeFormat(loc.value.language, { weekday: 'narrow', timeZone: 'UTC' })
  // 2026-01-04 is a Sunday.
  return Array.from({ length: 7 }, (_, i) =>
    formatter.format(new Date(Date.UTC(2026, 0, 4 + ((first + i) % 7)))),
  )
})

const invites = computed(() => props.draft.invites.filter(invite => invite.email.trim()))
const template = computed(() =>
  STARTER_TEMPLATES.find(item => item.key === props.draft.first_form.template_key),
)
const formTitle = computed(() =>
  template.value ? t(`templates.starter.${template.value.key}.name`) : t('onboarding.firstForm.untitled'),
)
</script>

<template>
  <UCard :ui="{ body: 'p-5' }" class="bg-elevated/40">
    <p class="mb-4 flex items-center gap-2 text-xs font-medium tracking-wide text-muted uppercase">
      <UIcon name="i-lucide-eye" class="size-3.5" /> {{ t('onboarding.preview.title') }}
    </p>

    <!-- Company + branding: the workspace sign-in page -->
    <div
      v-if="step === 'company' || step === 'branding'"
      class="rounded-xl border border-default bg-default p-5 shadow-sm"
    >
      <div class="flex items-center gap-3">
        <img
          v-if="draft.branding.logo_url"
          :src="draft.branding.logo_url"
          alt=""
          class="size-10 rounded-lg border border-default bg-default object-contain p-0.5"
        >
        <span
          v-else
          class="flex size-10 items-center justify-center rounded-lg text-lg font-semibold text-white"
          :style="{ backgroundColor: brand }"
          aria-hidden="true"
          >{{ initial }}</span
        >
        <span class="truncate font-semibold text-highlighted">{{ name }}</span>
      </div>
      <p class="mt-5 text-lg font-semibold text-highlighted">{{ t('auth.login.title') }}</p>
      <p class="text-xs text-muted">{{ t('auth.login.desc', { workspace: name }) }}</p>
      <div class="mt-4 space-y-2" aria-hidden="true">
        <div class="h-9 rounded-md border border-default" />
        <div class="h-9 rounded-md border border-default" />
        <div
          class="flex h-9 items-center justify-center rounded-md text-sm font-medium text-white"
          :style="{ backgroundColor: brand }"
        >
          {{ t('auth.login.submit') }}
        </div>
      </div>
      <p class="mt-4 truncate text-center font-mono text-[11px] text-muted">{{ host }}</p>
    </div>

    <!-- Regional settings -->
    <div v-else-if="step === 'localisation'" class="space-y-4">
      <dl class="divide-y divide-default rounded-xl border border-default bg-default">
        <div
          v-for="sample in samples"
          :key="sample.label"
          class="flex items-center justify-between gap-3 px-4 py-2.5 text-sm"
        >
          <dt class="text-muted">{{ sample.label }}</dt>
          <dd class="font-medium text-highlighted tabular-nums" dir="ltr">{{ sample.value }}</dd>
        </div>
      </dl>
      <div class="rounded-xl border border-default bg-default p-4">
        <p class="mb-2 text-xs text-muted">{{ t('onboarding.preview.week') }}</p>
        <div class="grid grid-cols-7 gap-1 text-center text-xs">
          <span
            v-for="(day, i) in weekDays"
            :key="i"
            class="rounded-md py-1.5"
            :class="i === 0 ? 'bg-inverted font-semibold text-inverted' : 'bg-elevated text-default'"
            >{{ day }}</span
          >
        </div>
      </div>
    </div>

    <!-- Team -->
    <ul
      v-else-if="step === 'team'"
      class="divide-y divide-default rounded-xl border border-default bg-default"
    >
      <li class="flex items-center justify-between gap-3 px-4 py-2.5">
        <UUser
          :name="session.displayName.value"
          :description="session.user.value?.email"
          size="sm"
          :avatar="{ alt: session.displayName.value }"
        />
        <UBadge :label="t('onboarding.team.owner')" color="neutral" variant="soft" size="sm" />
      </li>
      <li
        v-for="invite in invites"
        :key="invite.email"
        class="flex items-center justify-between gap-3 px-4 py-2.5"
      >
        <UUser
          :name="invite.email"
          :description="t('onboarding.preview.pending')"
          size="sm"
          :avatar="{ icon: 'i-lucide-mail' }"
          :ui="{ name: 'truncate max-w-44' }"
        />
        <UBadge :label="t(`onboarding.team.${invite.role}`)" color="neutral" variant="outline" size="sm" />
      </li>
      <li v-if="!invites.length" class="px-4 py-6 text-center text-sm text-muted">
        {{ t('onboarding.preview.noInvites') }}
      </li>
    </ul>

    <!-- First form -->
    <div v-else class="rounded-xl border border-default bg-default p-5">
      <div class="flex items-center gap-3">
        <span class="flex size-9 items-center justify-center rounded-md border border-default bg-elevated/50">
          <UIcon :name="template?.icon ?? 'i-lucide-file-plus'" class="size-4 text-highlighted" />
        </span>
        <span class="truncate font-semibold text-highlighted">{{ formTitle }}</span>
      </div>
      <div class="mt-5 space-y-3" aria-hidden="true">
        <div v-for="n in Math.min(template?.fields ?? 2, 4)" :key="n" class="space-y-1.5">
          <div class="h-2.5 w-24 rounded bg-elevated" />
          <div class="h-8 rounded-md border border-default" />
        </div>
        <div
          class="flex h-9 items-center justify-center rounded-md text-sm font-medium text-white"
          :style="{ backgroundColor: brand }"
        >
          {{ t('onboarding.preview.submit') }}
        </div>
      </div>
    </div>
  </UCard>
</template>
