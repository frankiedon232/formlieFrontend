<!--
  Sign-up links (F16 rework): the workspace's shared link (on / off, which email domains it accepts,
  copy, QR code, a new link that stops the old one) and personal links to chosen addresses. Everyone who
  signs up with a link waits for approval on People.
-->
<script setup lang="ts">
import type { SignupLinkView } from '#shared/types/people'

const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ personal: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const { relative, number } = useFormat()
const { can } = useCan()

const view = ref<SignupLinkView | null>(null)
const domains = ref<string[]>([])
const busy = ref<string | null>(null)
watch(open, async value => {
  if (!value) return
  try {
    view.value = (await api.get<SignupLinkView>('/people/signup-link')).data
    domains.value = [...view.value.domains]
  } catch (error) {
    handle(error)
  }
})
async function update(part: string, body: Record<string, unknown>, message: string) {
  busy.value = part
  try {
    view.value = (await api.put<SignupLinkView>('/people/signup-link', body)).data
    domains.value = [...view.value.domains]
    toast.add({ title: message, color: 'success', icon: 'i-lucide-circle-check' })
  } catch (error) {
    handle(error)
  } finally {
    busy.value = null
  }
}
async function renew() {
  if (!(await confirm({ title: t('people.links.renewTitle'), description: t('people.links.renewDesc'), confirmLabel: t('people.links.renew') }))) return
  busy.value = 'renew'
  try {
    view.value = (await api.post<SignupLinkView>('/people/signup-link/new')).data
    toast.add({ title: t('people.links.renewed'), color: 'success', icon: 'i-lucide-refresh-cw' })
  } catch (error) {
    handle(error)
  } finally {
    busy.value = null
  }
}
const domainsChanged = computed(() => !!view.value && domains.value.join(',') !== view.value.domains.join(','))
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="t('people.links.title')" :description="t('people.links.desc')" :ui="{ content: 'sm:max-w-2xl' }">
    <template #body>
      <div v-if="!view" class="flex flex-col gap-3"><USkeleton class="h-10" /><USkeleton class="h-40" /></div>
      <div v-else class="flex flex-col gap-5">
        <section class="flex flex-col gap-3 rounded-lg border border-default p-4">
          <USwitch :model-value="view.enabled" :label="t('people.links.shared')" :description="view.enabled ? t('people.links.sharedOn') : t('people.links.sharedOff')" color="neutral" :loading="busy === 'enabled'" :disabled="!can('people.manage') || !!busy" @update:model-value="value => update('enabled', { enabled: !!value }, value ? t('people.links.turnedOn') : t('people.links.turnedOff'))" />
          <template v-if="view.enabled">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-start">
              <div class="flex min-w-0 flex-1 flex-col gap-3">
                <AppCopyField :value="view.link" :label="t('people.links.link')" />
                <p class="text-xs text-muted">{{ t('people.links.changed', { when: relative(view.updated_at) }) }}<template v-if="view.pending"> · {{ t('people.links.waiting', { n: number(view.pending) }, view.pending) }}</template></p>
                <UFormField :label="t('people.links.domains')" :description="t('people.links.domainsHint')">
                  <UInputTags v-model="domains" placeholder="example.org" icon="i-lucide-at-sign" :add-on-blur="true" :add-on-paste="true" :disabled="!can('people.manage')" class="w-full" />
                </UFormField>
                <div class="flex flex-wrap gap-2">
                  <UButton v-if="domainsChanged" :label="t('common.save')" icon="i-lucide-check" color="neutral" size="sm" :loading="busy === 'domains'" @click="update('domains', { domains }, t('people.links.saved'))" />
                  <UButton v-if="can('people.manage')" :label="t('people.links.renew')" icon="i-lucide-refresh-cw" color="neutral" variant="outline" size="sm" :loading="busy === 'renew'" @click="renew" />
                </div>
              </div>
              <div class="shrink-0 self-center rounded-xl bg-white p-3"><FormsShareQrCode :value="view.link" :label="t('people.links.qr')" :branded="false" class="size-36" /></div>
            </div>
          </template>
        </section>
        <section class="flex flex-wrap items-center gap-3 rounded-lg border border-default p-4">
          <div class="flex min-w-0 flex-1 flex-col">
            <span class="text-sm font-medium text-highlighted">{{ t('people.links.personal') }}</span>
            <span class="text-xs text-muted">{{ t('people.links.personalHint') }}</span>
          </div>
          <UButton :label="t('people.links.sendPersonal')" icon="i-lucide-send" color="neutral" variant="outline" size="sm" :disabled="!can('people.manage')" @click="emit('personal')" />
        </section>
      </div>
    </template>
  </AppModal>
</template>
