<!--
  6-digit code entry (FRONTEND-SPEC §4): auto-advance + paste (UPinInput), auto-submit when full,
  resend countdown, channel switch, attempts left. Dev + mock only: shows the mock's code.
-->
<script setup lang="ts">
import type { DeepReadonly } from 'vue'
import type { LoginChallenge, OtpChannel } from '#shared/types/auth'

const props = defineProps<{
  challenge: DeepReadonly<LoginChallenge>
  loading?: boolean
  attemptsLeft?: number | null
  devCode?: string | null
}>()
const emit = defineEmits<{ complete: [code: string]; resend: [channel?: OtpChannel] }>()

const { t } = useI18n()
const config = useRuntimeConfig()
const digits = ref<number[]>([])

const remaining = ref(props.challenge.resend_after)
const { pause, resume } = useIntervalFn(() => {
  remaining.value = Math.max(0, remaining.value - 1)
  if (remaining.value === 0) pause()
}, 1000)

watch(
  () => props.challenge,
  challenge => {
    remaining.value = challenge.resend_after
    digits.value = []
    resume()
  },
)

const showDevCode = computed(() => import.meta.dev && config.public.apiMock && !!props.devCode)
const CHANNEL_ICONS: Record<OtpChannel, string> = {
  email: 'i-lucide-mail',
  sms: 'i-lucide-message-square',
  totp: 'i-lucide-smartphone',
}

function onComplete(value: number[]) {
  const code = value.join('')
  if (/^\d{6}$/.test(code)) emit('complete', code)
}

/** Clear the boxes after a wrong code so the next attempt starts fresh. */
function reset() {
  digits.value = []
}

defineExpose({ reset })
</script>

<template>
  <div class="flex flex-col gap-5">
    <UPinInput
      v-model="digits"
      :length="6"
      type="number"
      otp
      autofocus
      size="xl"
      :disabled="loading"
      :aria-label="t('auth.otp.label')"
      class="justify-between"
      :ui="{ base: 'size-12 text-lg sm:size-13' }"
      @complete="onComplete"
    />

    <p v-if="attemptsLeft != null" class="text-sm text-error" aria-live="polite">
      {{ t('auth.otp.attemptsLeft', { count: attemptsLeft }, attemptsLeft) }}
    </p>

    <UAlert
      v-if="showDevCode"
      icon="i-lucide-flask-conical"
      color="neutral"
      variant="subtle"
      :title="t('auth.otp.devCode', { code: devCode })"
    />

    <div class="flex flex-wrap items-center justify-between gap-2 text-sm">
      <UButton
        v-if="remaining > 0"
        :label="t('auth.otp.resendIn', { seconds: remaining })"
        color="neutral"
        variant="link"
        class="px-0"
        disabled
      />
      <UButton
        v-else
        :label="t('auth.otp.resend')"
        icon="i-lucide-rotate-cw"
        color="neutral"
        variant="link"
        class="px-0"
        :disabled="loading"
        @click="emit('resend')"
      />

      <div v-if="challenge.channels.length > 1" class="flex items-center gap-1">
        <UTooltip
          v-for="channel in challenge.channels"
          :key="channel"
          :text="t(`auth.otp.channel.${channel}`)"
        >
          <UButton
            :icon="CHANNEL_ICONS[channel]"
            color="neutral"
            :variant="channel === challenge.channel ? 'soft' : 'ghost'"
            size="sm"
            square
            :aria-pressed="channel === challenge.channel"
            :aria-label="t(`auth.otp.channel.${channel}`)"
            :disabled="loading || remaining > 0 || channel === challenge.channel"
            @click="emit('resend', channel)"
          />
        </UTooltip>
      </div>
    </div>
  </div>
</template>
