<!-- manage.*: email → code → every workspace this email belongs to (no enumeration before the code). -->
<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import type { OtpChannel, WorkspaceLink } from '#shared/types/auth'

definePageMeta({ layout: 'auth', auth: 'guest', manage: 'only' })

const { t } = useI18n()
const auth = useAuth()
const { handle } = useErrorHandler()
const { busy, run } = useBusy()
useHead({ title: () => t('auth.find.title') })

const schema = computed(() => emailOnlySchema(t))
const state = reactive({ email: '' })
const workspaces = ref<WorkspaceLink[] | null>(null)
const step = computed(() =>
  workspaces.value ? 'results' : auth.pending.value?.purpose === 'find' ? 'code' : 'email',
)

async function onSubmit(event: FormSubmitEvent<typeof state>) {
  await run(() => auth.findWorkspace(event.data.email))
}

const otp = useTemplateRef<{ reset: () => void }>('otp')
const verifying = ref(false)
const attemptsLeft = ref<number | null>(null)

async function verify(code: string) {
  verifying.value = true
  try {
    workspaces.value = (await auth.verify(code)) as WorkspaceLink[]
    auth.clearPending()
  } catch (error) {
    const normalised = handle(error)
    const left = normalised.details.find(detail => detail.field === 'attempts_left')
    attemptsLeft.value = left ? Number(left.message) : null
    otp.value?.reset()
  } finally {
    verifying.value = false
  }
}

async function resend(channel?: OtpChannel) {
  try {
    await auth.resend(channel)
  } catch (error) {
    handle(error)
  }
}

function startOver() {
  auth.clearPending()
  workspaces.value = null
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight text-highlighted">{{ t('auth.find.title') }}</h1>
      <p class="mt-1 text-sm text-muted">
        <template v-if="step === 'code' && auth.pending.value">
          {{ t('auth.otp.desc', { destination: auth.pending.value.challenge.masked_destination }) }}
        </template>
        <template v-else-if="step === 'results'">{{ t('auth.find.resultsDesc') }}</template>
        <template v-else>{{ t('auth.find.desc') }}</template>
      </p>
    </div>

    <UForm
      v-if="step === 'email'"
      :schema="schema"
      :state="state"
      class="flex flex-col gap-4"
      @submit="onSubmit"
    >
      <UFormField :label="t('auth.fields.email')" name="email" required>
        <UInput v-model="state.email" type="email" autocomplete="email" class="w-full" autofocus />
      </UFormField>
      <UButton type="submit" :label="t('auth.find.send')" color="neutral" size="lg" block :loading="busy" />
    </UForm>

    <AuthOtpInput
      v-else-if="step === 'code' && auth.pending.value"
      ref="otp"
      :challenge="auth.pending.value.challenge"
      :dev-code="auth.pending.value.devCode"
      :loading="verifying"
      :attempts-left="attemptsLeft"
      @complete="verify"
      @resend="resend"
    />

    <template v-else-if="step === 'results' && workspaces">
      <ul v-if="workspaces.length" class="flex flex-col gap-2">
        <li v-for="workspace in workspaces" :key="workspace.subdomain">
          <UButton
            :to="workspace.url"
            external
            color="neutral"
            variant="outline"
            block
            class="justify-between p-3"
            trailing-icon="i-lucide-arrow-right"
          >
            <span class="flex min-w-0 items-center gap-3 text-start">
              <UAvatar :alt="workspace.name" size="sm" />
              <span class="min-w-0">
                <span class="block truncate font-medium text-highlighted">{{ workspace.name }}</span>
                <span class="block truncate text-xs text-muted"
                  >{{ workspace.subdomain }}.{{ $config.public.rootDomain }}</span
                >
              </span>
            </span>
          </UButton>
        </li>
      </ul>
      <UEmpty
        v-else
        icon="i-lucide-search-x"
        :title="t('auth.find.none')"
        :description="t('auth.find.noneDesc')"
        :actions="[{ label: t('auth.login.createWorkspace'), to: '/auth/signup', color: 'neutral' }]"
        variant="outline"
      />
    </template>

    <p class="text-center text-sm text-muted">
      <UButton
        v-if="step !== 'email'"
        :label="t('auth.find.other')"
        color="neutral"
        variant="link"
        @click="startOver"
      />
      <template v-else>
        {{ t('auth.login.noWorkspace') }}
        <ULink to="/auth/signup" class="font-medium text-highlighted">{{
          t('auth.login.createWorkspace')
        }}</ULink>
      </template>
    </p>
  </div>
</template>
