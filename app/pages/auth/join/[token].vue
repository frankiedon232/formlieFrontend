<!--
  An invitation link (F16 M2): who invited the person and to which workspace, then their name and a
  password (the workspace's password rules), and they are in. Then sign in as usual (with the code).
  An expired or withdrawn link says so and what to do.
-->
<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import { z } from 'zod'
import type { InvitePreview } from '#shared/types/people'

definePageMeta({ layout: 'auth', auth: false })
const { t } = useI18n()
const route = useRoute()
const api = useApi()
const { handle } = useErrorHandler()
const policy = computed(() => useTenant().profile.value?.password_policy)
useHead({ title: () => t('people.join.title') })

const token = String(route.params.token)
const invite = ref<InvitePreview | null>(null)
const problem = ref<string | null>(null)
onMounted(async () => {
  try {
    invite.value = (await api.get<InvitePreview>(`/public/invites/${token}`)).data
  } catch (error) {
    problem.value = (error as { code?: string }).code === 'FRM-USER-1001' ? 'expired' : 'invalid'
  }
})

const schema = computed(() =>
  z
    .object({ first_name: z.string().trim().min(1, t('auth.validation.required')).max(60), last_name: z.string().trim().min(1, t('auth.validation.required')).max(60) })
    .and(resetSchema(t, policy.value)),
)
const state = reactive({ first_name: '', last_name: '', password: '', confirm: '' })
const saving = ref(false)
async function join(event: FormSubmitEvent<typeof state>) {
  saving.value = true
  try {
    const { data } = await api.post<{ email: string }>(`/public/invites/${token}/accept`, { first_name: event.data.first_name, last_name: event.data.last_name, password: event.data.password })
    // The address comes along in app state (never the address bar)
    useState<string>('auth:join-email').value = data.email
    await navigateTo({ path: '/auth/login', query: { joined: '1' } })
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
    <div v-else-if="!invite" class="flex flex-col gap-4"><USkeleton class="h-8 w-64" /><USkeleton class="h-4 w-80" /><USkeleton v-for="n in 3" :key="n" class="h-11" /></div>
    <template v-else>
      <AuthHeading :title="t('people.join.heading', { workspace: invite.workspace })" :description="t('people.join.desc', { name: invite.inviter, role: t(`people.role.${invite.role}`) })" />
      <blockquote v-if="invite.message" class="mb-6 rounded-lg border-s-2 border-inverted bg-elevated/60 px-4 py-3 text-sm text-default">
        {{ invite.message }}
        <footer class="mt-1 text-xs text-muted">{{ invite.inviter }}</footer>
      </blockquote>
      <UForm :schema="schema" :state="state" class="flex flex-col gap-5" @submit="join">
        <UFormField :label="t('auth.fields.email')" size="lg">
          <UInput :model-value="invite.email" type="email" icon="i-lucide-mail" size="xl" class="w-full" disabled dir="ltr" />
        </UFormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <UFormField :label="t('auth.fields.firstName')" name="first_name" required>
            <UInput v-model="state.first_name" autocomplete="given-name" size="xl" class="w-full" autofocus />
          </UFormField>
          <UFormField :label="t('auth.fields.lastName')" name="last_name" required>
            <UInput v-model="state.last_name" autocomplete="family-name" size="xl" class="w-full" />
          </UFormField>
        </div>
        <UFormField :label="t('auth.fields.password')" name="password" required>
          <AuthPasswordInput v-model="state.password" autocomplete="new-password" size="xl" icon="i-lucide-lock-keyhole" />
          <AuthPasswordStrength :value="state.password" :policy="policy" />
        </UFormField>
        <UFormField :label="t('people.join.confirm')" name="confirm" required>
          <AuthPasswordInput v-model="state.confirm" autocomplete="new-password" size="xl" icon="i-lucide-lock-keyhole" />
        </UFormField>
        <UButton type="submit" :label="t('people.join.submit')" color="neutral" size="xl" block :loading="saving" />
      </UForm>
    </template>
  </div>
</template>
