<!--
  The page a sign-up link opens (F16 rework), a separate page outside the workspace:
  - activation (a profile an admin made): name filled in, choose a password, then sign in;
  - a personal sign-up link or the workspace's shared link: name, email (shared link), phone, password;
    the account then waits for an admin's approval ("Request sent").
  Expired or used links say so and what to do.
-->
<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import { z } from 'zod'
import type { InvitePreview } from '#shared/types/people'

definePageMeta({ layout: 'auth', auth: false })
const { t } = useI18n()
const { roleName } = useBuiltInNames()
const route = useRoute()
const api = useApi()
const { handle } = useErrorHandler()
const policy = computed(() => useTenant().profile.value?.password_policy)
useHead({ title: () => t('people.join.title') })

const token = String(route.params.token)
const invite = ref<InvitePreview | null>(null)
const problem = ref<string | null>(null)
const sent = ref(false)
onMounted(async () => {
  try {
    invite.value = (await api.get<InvitePreview>(`/public/invites/${token}`)).data
    Object.assign(state, { first_name: invite.value.first_name, last_name: invite.value.last_name })
  } catch (error) {
    problem.value = (error as { code?: string }).code === 'FRM-USER-1001' ? 'expired' : 'invalid'
  }
})
const activation = computed(() => invite.value?.kind === 'activation')
const shared = computed(() => invite.value?.kind === 'link')

const schema = computed(() =>
  z
    .object({
      first_name: z.string().trim().min(1, t('auth.validation.required')).max(60),
      last_name: z.string().trim().min(1, t('auth.validation.required')).max(60),
      email: z.string().refine(value => !shared.value || z.email().safeParse(value).success, t('auth.validation.email')),
      phone: z.string().trim().refine(value => !value || /^\+[1-9][\d\s-]{6,18}$/.test(value), t('people.join.phoneFormat')),
    })
    .and(resetSchema(t, policy.value)),
)
const state = reactive({ first_name: '', last_name: '', email: '', phone: '', password: '', confirm: '' })
const saving = ref(false)
async function join(event: FormSubmitEvent<typeof state>) {
  saving.value = true
  try {
    const { data } = await api.post<{ email: string; status: string }>(`/public/invites/${token}/accept`, {
      first_name: event.data.first_name,
      last_name: event.data.last_name,
      ...(shared.value ? { email: event.data.email } : {}),
      phone: event.data.phone?.trim() || null,
      password: event.data.password,
    })
    if (data.status === 'active') {
      // The address comes along in app state (never the address bar)
      useState<string>('auth:join-email').value = data.email
      await navigateTo({ path: '/auth/login', query: { joined: '1' } })
    } else sent.value = true
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <AppEmpty v-if="problem" :icon="problem === 'expired' ? 'i-lucide-clock-alert' : 'i-lucide-link-2-off'" :title="t(`people.join.${problem}`)" :description="t(`people.join.${problem}Desc`)" :actions="[{ label: t('people.join.toSignIn'), icon: 'i-lucide-log-in', color: 'neutral', variant: 'outline', to: '/auth/login' }]" />
    <AppEmpty v-else-if="sent" icon="i-lucide-mail-check" :title="t('people.join.sent')" :description="t('people.join.sentDesc', { workspace: invite?.workspace ?? '' })" />
    <div v-else-if="!invite" class="flex flex-col gap-4"><USkeleton class="h-8 w-64" /><USkeleton class="h-4 w-80" /><USkeleton v-for="n in 3" :key="n" class="h-11" /></div>
    <template v-else>
      <AuthHeading
        :title="activation ? t('people.join.activateHeading', { workspace: invite.workspace }) : shared ? t('people.join.askHeading', { workspace: invite.workspace }) : t('people.join.heading', { workspace: invite.workspace })"
        :description="activation ? t('people.join.activateDesc', { name: invite.inviter ?? '', role: roleName(invite.role, invite.role_name) }) : shared ? t('people.join.askDesc') : t('people.join.inviteDesc', { name: invite.inviter ?? '' })"
      />
      <blockquote v-if="invite.message" class="mb-6 rounded-lg border-s-2 border-inverted bg-elevated/60 px-4 py-3 text-sm text-default">
        {{ invite.message }}
        <footer class="mt-1 text-xs text-muted">{{ invite.inviter }}</footer>
      </blockquote>
      <UAlert v-if="!activation" icon="i-lucide-hourglass" color="neutral" variant="subtle" :description="t('people.join.approvalNote')" class="mb-5" :ui="{ description: 'text-xs' }" />
      <UForm :schema="schema" :state="state" class="flex flex-col gap-5" @submit="join">
        <UFormField :label="t('auth.fields.email')" name="email" size="lg" :hint="shared && invite.domains.length ? t('people.join.domains', { list: invite.domains.join(', ') }) : undefined" required>
          <UInput v-if="shared" v-model="state.email" type="email" icon="i-lucide-mail" autocomplete="email" size="xl" class="w-full" dir="ltr" autofocus />
          <UInput v-else :model-value="invite.email ?? ''" type="email" icon="i-lucide-mail" size="xl" class="w-full" disabled dir="ltr" />
        </UFormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <UFormField :label="t('auth.fields.firstName')" name="first_name" required>
            <UInput v-model="state.first_name" autocomplete="given-name" size="xl" class="w-full" :autofocus="!shared" />
          </UFormField>
          <UFormField :label="t('auth.fields.lastName')" name="last_name" required>
            <UInput v-model="state.last_name" autocomplete="family-name" size="xl" class="w-full" />
          </UFormField>
        </div>
        <UFormField v-if="!activation" :label="t('people.col.phone')" name="phone" :hint="t('profile.twoStep.numberHint')">
          <UInput v-model="state.phone" type="tel" autocomplete="tel" placeholder="+44 7700 900123" icon="i-lucide-phone" size="xl" class="w-full" dir="ltr" />
        </UFormField>
        <UFormField :label="t('auth.fields.password')" name="password" required>
          <AuthPasswordInput v-model="state.password" autocomplete="new-password" size="xl" icon="i-lucide-lock-keyhole" />
          <AuthPasswordStrength :value="state.password" :policy="policy" />
        </UFormField>
        <UFormField :label="t('people.join.confirm')" name="confirm" required>
          <AuthPasswordInput v-model="state.confirm" autocomplete="new-password" size="xl" icon="i-lucide-lock-keyhole" />
        </UFormField>
        <UButton type="submit" :label="activation ? t('people.join.activate') : t('people.join.request')" color="neutral" size="xl" block :loading="saving" />
      </UForm>
    </template>
  </div>
</template>
