<!--
  Enterprise enquiry (F24, owner 2026-10-10): "Contact us" opens this form inside the app (never a mail program or
  another site). It asks what the Formalie team needs to prepare an offer (company, contact, size, volume, needs,
  data residency, timing, message), filled in from the workspace and the person where it can. The Formalie team
  reads it in the platform admin and replies by email.
-->
<script setup lang="ts">
import { z } from 'zod'
import type { EnterpriseEnquiry } from '#shared/types/billing'

const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const api = useApi()
const session = useSession()
const store = useWorkspaceSettings()
const tenant = useTenant()

const NEEDS = ['sso', 'dedicated', 'residency', 'sla', 'security', 'invoice', 'onboarding', 'custom_limits'] as const
/** The inputs hold text; empty optional answers are sent as null. */
type Draft = Omit<EnterpriseEnquiry, 'phone' | 'role' | 'country' | 'data_residency'> & { phone: string; role: string; country: string; data_residency: string }
const blank = (): Draft => ({
  company: store.settings.value?.company.display_name || tenant.profile.value?.name || '',
  name: [session.user.value?.first_name, session.user.value?.last_name].filter(Boolean).join(' '),
  email: session.user.value?.email ?? '',
  phone: '',
  role: '',
  country: '',
  size: '51-200',
  responses_per_month: '100k_1m',
  needs: [],
  data_residency: '',
  message: '',
  start: 'quarter',
})
const state = ref<Draft>(blank())
const sent = ref<string | null>(null)
watch(open, value => value && ((state.value = blank()), (sent.value = null)))

const schema = computed(() =>
  z.object({
    company: z.string().trim().min(2, t('billing.enquiry.required')),
    name: z.string().trim().min(2, t('billing.enquiry.required')),
    email: z.email(t('billing.enquiry.email')),
    message: z.string().trim().min(10, t('billing.enquiry.messageShort')),
  }),
)
const options = (key: string, values: readonly string[]) => values.map(value => ({ value, label: t(`billing.enquiry.${key}.${value}`) }))
const toggleNeed = (need: (typeof NEEDS)[number]) => (state.value.needs = state.value.needs.includes(need) ? state.value.needs.filter(item => item !== need) : [...state.value.needs, need])

const { busy, run } = useBusy()
async function send() {
  await run(async () => {
    const { data } = await api.post<{ id: string; received_at: string }>('/billing/enterprise-enquiries', { ...state.value, phone: state.value.phone || null, role: state.value.role || null, country: state.value.country || null, data_residency: state.value.data_residency || null } satisfies EnterpriseEnquiry)
    sent.value = data.id
  })
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('billing.enquiry.title')" :description="t('billing.enquiry.desc')" keep-open :ui="{ content: 'sm:max-w-2xl' }">
    <template #body>
      <AppEmpty
        v-if="sent"
        icon="i-lucide-mail-check"
        :title="t('billing.enquiry.sentTitle')"
        :description="t('billing.enquiry.sentDesc', { email: state.email })"
        :actions="[{ label: t('billing.enquiry.close'), color: 'neutral', variant: 'outline', onClick: () => (open = false) }]"
      />
      <UForm v-else id="enterprise-enquiry" :schema="schema" :state="state" class="flex flex-col gap-5" @submit="send">
        <section class="flex flex-col gap-3">
          <h3 class="text-xs font-medium text-muted uppercase">{{ t('billing.enquiry.you') }}</h3>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <UFormField name="company" :label="t('billing.enquiry.company')" required><UInput v-model="state.company" icon="i-lucide-building-2" class="w-full" /></UFormField>
            <UFormField name="name" :label="t('billing.enquiry.name')" required><UInput v-model="state.name" icon="i-lucide-user-round" class="w-full" autocomplete="name" /></UFormField>
            <UFormField name="email" :label="t('billing.enquiry.workEmail')" required><UInput v-model="state.email" type="email" icon="i-lucide-mail" class="w-full" autocomplete="email" /></UFormField>
            <UFormField :label="t('billing.enquiry.phone')"><UInput v-model="state.phone" type="tel" icon="i-lucide-phone" placeholder="+44 7700 900123" class="w-full" autocomplete="tel" /></UFormField>
            <UFormField :label="t('billing.enquiry.role')"><UInput v-model="state.role" icon="i-lucide-briefcase" class="w-full" /></UFormField>
            <UFormField :label="t('billing.enquiry.country')"><UInput v-model="state.country" icon="i-lucide-map-pin" class="w-full" autocomplete="country-name" /></UFormField>
          </div>
        </section>

        <section class="flex flex-col gap-3">
          <h3 class="text-xs font-medium text-muted uppercase">{{ t('billing.enquiry.scale') }}</h3>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <UFormField :label="t('billing.enquiry.sizeLabel')"><USelect v-model="state.size" :items="options('size', ['1-50', '51-200', '201-1000', '1001-5000', '5000+'])" class="w-full" /></UFormField>
            <UFormField :label="t('billing.enquiry.volumeLabel')"><USelect v-model="state.responses_per_month" :items="options('volume', ['under_100k', '100k_1m', '1m_10m', 'over_10m'])" class="w-full" /></UFormField>
            <UFormField :label="t('billing.enquiry.startLabel')"><USelect v-model="state.start" :items="options('startWhen', ['now', 'quarter', 'later'])" class="w-full" /></UFormField>
          </div>
        </section>

        <section class="flex flex-col gap-3">
          <h3 class="text-xs font-medium text-muted uppercase">{{ t('billing.enquiry.needsLabel') }}</h3>
          <div class="flex flex-wrap gap-2" role="group" :aria-label="t('billing.enquiry.needsLabel')">
            <UButton v-for="need in NEEDS" :key="need" :label="t(`billing.enquiry.need.${need}`)" :icon="state.needs.includes(need) ? 'i-lucide-check' : undefined" color="neutral" :variant="state.needs.includes(need) ? 'solid' : 'outline'" size="sm" class="rounded-full" :aria-pressed="state.needs.includes(need)" @click="toggleNeed(need)" />
          </div>
          <UFormField v-if="state.needs.includes('residency')" :label="t('billing.enquiry.residency')" :help="t('billing.enquiry.residencyHelp')"><UInput v-model="state.data_residency" icon="i-lucide-globe-lock" class="w-full sm:max-w-sm" /></UFormField>
        </section>

        <UFormField name="message" :label="t('billing.enquiry.message')" :help="t('billing.enquiry.messageHelp')" required>
          <UTextarea v-model="state.message" :rows="5" :maxlength="4000" class="w-full" />
        </UFormField>
        <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-shield-check" class="mt-0.5 size-3.5 shrink-0" />{{ t('billing.enquiry.privacy') }}</p>
      </UForm>
    </template>
    <template v-if="!sent" #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="ghost" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="enterprise-enquiry" :label="t('billing.enquiry.send')" icon="i-lucide-send" color="neutral" :loading="busy" />
      </div>
    </template>
  </AppModal>
</template>
