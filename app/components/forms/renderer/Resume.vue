<!--
  "Save and continue later" (F10 M2): saves the answers now and sends a personal resume link to the
  respondent's email (prefilled from their own email answer). The link brings back the answers and
  the page, on any device, for 30 days. Dev mock: the link is shown here (a real backend emails it).
-->
<script setup lang="ts">
const props = defineProps<{
  defaultEmail: string
  later: (email: string) => Promise<{ sentTo: string | null; devUrl: string | null } | null>
}>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()

const email = ref('')
const sent = ref<{ sentTo: string | null; devUrl: string | null } | null>(null)
watch(
  open,
  value => {
    if (!value) return
    email.value = props.defaultEmail
    sent.value = null
  },
  { immediate: true },
)
const valid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()))

const { busy, run } = useBusy()
async function send() {
  if (!valid.value) return
  await run(async () => {
    sent.value = await props.later(email.value.trim())
  })
}
const { copy } = useClipboard({ legacy: true })
function copyLink() {
  if (!sent.value?.devUrl) return
  copy(sent.value.devUrl)
  toast.add({ title: t('renderer.resume.copied'), icon: 'i-lucide-check', color: 'success' })
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('renderer.resume.title')" :description="sent ? undefined : t('renderer.resume.desc')" :dismissible="!busy">
    <template #body>
      <div v-if="sent" class="flex flex-col items-center gap-3 py-2 text-center">
        <span class="flex size-12 items-center justify-center rounded-full bg-elevated">
          <UIcon name="i-lucide-mail-check" class="size-6 text-success" />
        </span>
        <p class="text-sm font-medium text-highlighted">{{ t('renderer.resume.sent', { email: sent.sentTo ?? email }) }}</p>
        <p class="max-w-sm text-xs text-muted">{{ t('renderer.resume.sentHint') }}</p>
        <div v-if="sent.devUrl" class="flex w-full flex-col gap-1.5 rounded-md border border-dashed border-default p-2 text-start">
          <span class="text-xs text-muted">{{ t('renderer.resume.devLink') }}</span>
          <div class="flex items-center gap-2">
            <code class="min-w-0 flex-1 truncate text-xs">{{ sent.devUrl }}</code>
            <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" :aria-label="t('renderer.resume.copy')" @click="copyLink" />
          </div>
        </div>
      </div>
      <form v-else id="resume-form" class="flex flex-col gap-3" @submit.prevent="send">
        <UFormField :label="t('renderer.resume.email')" :description="t('renderer.resume.emailHint')">
          <UInput v-model="email" type="email" autocomplete="email" icon="i-lucide-mail" class="w-full" autofocus />
        </UFormField>
      </form>
    </template>
    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <template v-if="sent">
          <UButton :label="t('renderer.resume.keepGoing')" icon="i-lucide-arrow-right" color="neutral" class="justify-center" @click="open = false" />
        </template>
        <template v-else>
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" class="justify-center" :disabled="busy" @click="open = false" />
          <UButton type="submit" form="resume-form" :label="t('renderer.resume.send')" icon="i-lucide-send" color="neutral" class="justify-center" :loading="busy" :disabled="!valid" />
        </template>
      </div>
    </template>
  </AppModal>
</template>
