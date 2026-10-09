<!--
  Set up an authenticator app (F16 M5): scan the QR code (or type the key), enter the 6-digit code it
  shows, then keep the ten recovery codes (shown once: copy or download). Each recovery code works once
  at sign-in when the phone is not at hand. Also shows new recovery codes (`codes` given).
-->
<script setup lang="ts">
const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ codes?: string[] | null }>()
const emit = defineEmits<{ done: [] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { copy } = useClipboard({ legacy: true })
const toast = useToast()

const setup = ref<{ secret: string; uri: string } | null>(null)
const code = ref('')
const recovery = ref<string[] | null>(null)
const busy = ref(false)
watch(open, async value => {
  if (!value) return
  code.value = ''
  recovery.value = props.codes ?? null
  setup.value = null
  if (recovery.value) return
  try {
    setup.value = (await api.post<{ secret: string; uri: string }>('/me/two-step/app')).data
  } catch (error) {
    handle(error)
    open.value = false
  }
})
const grouped = computed(() => setup.value?.secret.match(/.{1,4}/g)?.join(' ') ?? '')

async function confirm() {
  if (!/^\d{6}$/.test(code.value) || busy.value) return
  busy.value = true
  try {
    recovery.value = (await api.post<{ recovery_codes: string[] }>('/me/two-step/app/confirm', { code: code.value })).data.recovery_codes
    emit('done')
  } catch (error) {
    handle(error)
  } finally {
    busy.value = false
  }
}
async function copyCodes() {
  await copy(recovery.value!.join('\n'))
  toast.add({ title: t('profile.twoStep.codesCopied'), color: 'success', icon: 'i-lucide-copy' })
}
function download() {
  const blob = new Blob([`${t('profile.twoStep.codesFile')}\n\n${recovery.value!.join('\n')}\n`], { type: 'text/plain' })
  const link = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'formalie-recovery-codes.txt' })
  link.click()
  URL.revokeObjectURL(link.href)
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="recovery ? t('profile.twoStep.codesTitle') : t('profile.twoStep.appTitle')" :description="recovery ? t('profile.twoStep.codesDesc') : t('profile.twoStep.appDesc')" :ui="{ content: 'sm:max-w-lg' }">
    <template #body>
      <div v-if="recovery" class="flex flex-col gap-4">
        <ul class="grid grid-cols-2 gap-2 rounded-lg border border-default bg-elevated/50 p-4 font-mono text-sm text-highlighted" dir="ltr">
          <li v-for="item in recovery" :key="item">{{ item }}</li>
        </ul>
        <div class="flex flex-wrap gap-2">
          <UButton :label="t('common.copy')" icon="i-lucide-copy" color="neutral" variant="outline" size="sm" @click="copyCodes" />
          <UButton :label="t('profile.twoStep.download')" icon="i-lucide-download" color="neutral" variant="outline" size="sm" @click="download" />
        </div>
      </div>
      <div v-else-if="!setup" class="flex flex-col items-center gap-3"><USkeleton class="size-44" /><USkeleton class="h-4 w-56" /></div>
      <form v-else class="flex flex-col items-center gap-4" @submit.prevent="confirm">
        <ol class="w-full list-decimal ps-5 text-sm text-default"><li>{{ t('profile.twoStep.step1') }}</li><li>{{ t('profile.twoStep.step2') }}</li></ol>
        <div class="rounded-xl bg-white p-3"><FormsShareQrCode :value="setup.uri" :label="t('profile.twoStep.qrLabel')" :branded="false" class="size-44" /></div>
        <p class="text-center text-xs text-muted">{{ t('profile.twoStep.key') }} <span class="font-mono text-highlighted" dir="ltr">{{ grouped }}</span></p>
        <UFormField :label="t('profile.twoStep.code')" class="w-full max-w-56">
          <UInput v-model="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="123456" class="w-full font-mono" autofocus />
        </UFormField>
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton v-if="recovery" :label="t('profile.twoStep.saved')" icon="i-lucide-check" color="neutral" @click="open = false" />
        <template v-else>
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
          <UButton :label="t('profile.twoStep.turnOn')" icon="i-lucide-shield-check" color="neutral" :loading="busy" :disabled="!/^\d{6}$/.test(code)" @click="confirm" />
        </template>
      </div>
    </template>
  </AppModal>
</template>
