<!--
  My profile → Two-step sign-in (F16 M5): an authenticator app (set up with a QR code; new recovery
  codes; remove, with the password) and an SMS number for codes by text message (when the workspace
  allows them; checked with a code). Sign-in asks for the app's code first when it is set up.
-->
<script setup lang="ts">
import type { MyProfile } from '#shared/types/profile'

defineProps<{ profile: MyProfile }>()
const emit = defineEmits<{ changed: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()

const setupOpen = ref(false)
const codes = ref<string[] | null>(null)
const openSetup = (fresh: string[] | null = null) => ((codes.value = fresh), (setupOpen.value = true))

// Steps that ask for the password first (remove the app, new recovery codes)
const ask = ref<{ kind: 'remove' | 'recovery' } | null>(null)
const password = ref('')
const busy = ref(false)
async function confirmPassword() {
  if (!ask.value || !password.value || busy.value) return
  busy.value = true
  try {
    if (ask.value.kind === 'remove') {
      await api.post('/me/two-step/app/remove', { password: password.value })
      toast.add({ title: t('profile.twoStep.appRemoved'), color: 'success', icon: 'i-lucide-shield-off' })
      emit('changed')
    } else {
      const { data } = await api.post<{ recovery_codes: string[] }>('/me/two-step/recovery', { password: password.value })
      openSetup(data.recovery_codes)
      emit('changed')
    }
    ask.value = null
  } catch (error) {
    handle(error)
  } finally {
    busy.value = false
    password.value = ''
  }
}

// SMS number: type it, get a code, enter it
const phoneOpen = ref(false)
const phone = ref('')
const phoneCode = ref('')
const sent = ref<{ masked: string; dev?: string } | null>(null)
async function sendPhone() {
  busy.value = true
  try {
    const result = await api.post<{ masked: string }>('/me/two-step/phone', { phone: phone.value.trim() })
    sent.value = { masked: result.data.masked, dev: (result.meta as { dev_code?: string } | undefined)?.dev_code }
  } catch (error) {
    handle(error)
  } finally {
    busy.value = false
  }
}
async function confirmPhone() {
  busy.value = true
  try {
    await api.post('/me/two-step/phone/confirm', { code: phoneCode.value })
    toast.add({ title: t('profile.twoStep.phoneOn'), color: 'success', icon: 'i-lucide-message-square' })
    phoneOpen.value = false
    emit('changed')
  } catch (error) {
    handle(error)
  } finally {
    busy.value = false
  }
}
watch(phoneOpen, value => value && ((phone.value = ''), (phoneCode.value = ''), (sent.value = null)))
async function removePhone() {
  busy.value = true
  try {
    await api.del('/me/two-step/phone')
    toast.add({ title: t('profile.twoStep.phoneRemoved'), color: 'success', icon: 'i-lucide-message-square-x' })
    emit('changed')
  } catch (error) {
    handle(error)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <SettingsBlock :title="t('profile.twoStep.title')" :description="t('profile.twoStep.desc')" icon="i-lucide-shield-check">
    <div class="flex flex-col gap-3">
      <div class="flex flex-wrap items-center gap-3 rounded-lg border border-default p-3">
        <span class="flex size-9 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon name="i-lucide-smartphone" class="size-4 text-highlighted" /></span>
        <div class="flex min-w-0 flex-1 flex-col">
          <span class="text-sm font-medium text-highlighted">{{ t('profile.twoStep.app') }}</span>
          <span class="text-xs text-muted">{{ profile.two_step.app ? t('profile.twoStep.appOn', { n: profile.two_step.recovery_left }, profile.two_step.recovery_left) : t('profile.twoStep.appOff') }}</span>
        </div>
        <template v-if="profile.two_step.app">
          <UButton :label="t('profile.twoStep.newCodes')" icon="i-lucide-list-restart" color="neutral" variant="outline" size="sm" @click="ask = { kind: 'recovery' }" />
          <UButton :label="t('profile.twoStep.remove')" icon="i-lucide-trash-2" color="neutral" variant="ghost" size="sm" @click="ask = { kind: 'remove' }" />
        </template>
        <UButton v-else :label="t('profile.twoStep.setUp')" icon="i-lucide-qr-code" color="neutral" size="sm" @click="openSetup()" />
      </div>
      <div class="flex flex-wrap items-center gap-3 rounded-lg border border-default p-3">
        <span class="flex size-9 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon name="i-lucide-message-square" class="size-4 text-highlighted" /></span>
        <div class="flex min-w-0 flex-1 flex-col">
          <span class="text-sm font-medium text-highlighted">{{ t('profile.twoStep.sms') }}</span>
          <span class="text-xs text-muted" :dir="profile.two_step.phone ? 'ltr' : undefined">{{ profile.two_step.phone ?? (profile.two_step.sms_allowed ? t('profile.twoStep.smsOff') : t('profile.twoStep.smsNotAllowed')) }}</span>
        </div>
        <UButton v-if="profile.two_step.phone" :label="t('profile.twoStep.remove')" icon="i-lucide-trash-2" color="neutral" variant="ghost" size="sm" :loading="busy" @click="removePhone" />
        <UButton v-else-if="profile.two_step.sms_allowed" :label="t('profile.twoStep.addNumber')" icon="i-lucide-plus" color="neutral" variant="outline" size="sm" @click="phoneOpen = true" />
      </div>
    </div>

    <ProfileAppSetup v-model:open="setupOpen" :codes="codes" @done="emit('changed')" />

    <AppModal :open="!!ask" keep-open :title="ask?.kind === 'remove' ? t('profile.twoStep.removeTitle') : t('profile.twoStep.newCodesTitle')" :description="t('profile.twoStep.passwordFirst')" @update:open="value => !value && (ask = null)">
      <template #body>
        <form @submit.prevent="confirmPassword"><UFormField :label="t('auth.fields.password')"><AuthPasswordInput v-model="password" autocomplete="current-password" class="w-full" /></UFormField></form>
      </template>
      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="ask = null" />
          <UButton :label="ask?.kind === 'remove' ? t('profile.twoStep.remove') : t('profile.twoStep.newCodes')" :color="ask?.kind === 'remove' ? 'error' : 'neutral'" :loading="busy" :disabled="!password" @click="confirmPassword" />
        </div>
      </template>
    </AppModal>

    <AppModal v-model:open="phoneOpen" keep-open :title="t('profile.twoStep.phoneTitle')" :description="t('profile.twoStep.phoneDesc')">
      <template #body>
        <form class="flex flex-col gap-4" @submit.prevent="sent ? confirmPhone() : sendPhone()">
          <UFormField :label="t('profile.twoStep.number')" :hint="t('profile.twoStep.numberHint')">
            <UInput v-model="phone" type="tel" placeholder="+44 7700 900123" icon="i-lucide-phone" :disabled="!!sent" dir="ltr" class="w-full" autofocus />
          </UFormField>
          <UFormField v-if="sent" :label="t('profile.twoStep.codeSent', { to: sent.masked })" :hint="sent.dev ? t('profile.twoStep.devCode', { code: sent.dev }) : undefined">
            <UInput v-model="phoneCode" inputmode="numeric" maxlength="6" placeholder="123456" class="w-full font-mono" autofocus />
          </UFormField>
        </form>
      </template>
      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="phoneOpen = false" />
          <UButton v-if="!sent" :label="t('profile.twoStep.sendCode')" icon="i-lucide-send" color="neutral" :loading="busy" :disabled="!/^\+[1-9][\d\s-]{6,18}$/.test(phone.trim())" @click="sendPhone" />
          <UButton v-else :label="t('profile.twoStep.confirm')" icon="i-lucide-check" color="neutral" :loading="busy" :disabled="!/^\d{6}$/.test(phoneCode)" @click="confirmPhone" />
        </div>
      </template>
    </AppModal>
  </SettingsBlock>
</template>
