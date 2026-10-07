<!--
  Settings → Workspace address (F14 M7): change the subdomain with a live availability check; asks
  first, and the old one keeps leading here for 90 days. Own domains are not offered (owner, 2026-10-07).
-->
<script setup lang="ts">
import type { SubdomainAvailability } from '#shared/types/auth'
import type { WorkspaceAddress } from '#shared/types/address'

definePageMeta({ breadcrumb: 'settings.nav.address' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.address') })
const api = useApi()
const tenant = useTenant()
const toast = useToast()
const { dateTime } = useFormat()
const { handle } = useErrorHandler()
const config = useRuntimeConfig()

const address = ref<WorkspaceAddress | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    address.value = (await api.get<WorkspaceAddress>('/settings/address')).data
  } catch {
    failed.value = true
  }
}
onMounted(load)

// The new subdomain, checked as people type
const wanted = ref('')
const availability = ref<SubdomainAvailability | null>(null)
const checking = ref(false)
const cleaned = computed(() => wanted.value.trim().toLowerCase())
watchDebounced(cleaned, async value => {
  availability.value = null
  if (!value || value === address.value?.subdomain) return
  checking.value = true
  try {
    availability.value = (await api.get<SubdomainAvailability>('/tenants/subdomain-availability', { subdomain: value }, { background: true })).data
  } finally {
    checking.value = false
  }
}, { debounce: 300 })
const ownOld = computed(() => !!address.value?.previous.some(item => item.subdomain === cleaned.value))
const canChange = computed(() => !!cleaned.value && cleaned.value !== address.value?.subdomain && (availability.value?.available || (ownOld.value && availability.value?.reason === 'taken')))

const changeOpen = ref(false)
const typed = ref('')
const changing = ref(false)
async function change() {
  if (changing.value || typed.value.trim().toLowerCase() !== cleaned.value) return
  changing.value = true
  try {
    const { data } = await api.post<WorkspaceAddress>('/settings/address/subdomain', { subdomain: cleaned.value, confirm: typed.value })
    toast.add({ title: t('settings.address.changed', { url: data.url }), color: 'success', icon: 'i-lucide-circle-check' })
    // Move to the new address (same page); in development the workspace comes from ?tenant=
    window.location.href = tenant.devTenant.value ? `${window.location.pathname}?tenant=${data.subdomain}` : tenant.hostUrl(data.subdomain, window.location.pathname)
  } catch (error) {
    handle(error)
    changing.value = false
  }
}

const formsHost = computed(() => `${address.value?.subdomain}.${config.public.rootDomain}`)
</script>

<template>
  <SettingsPage id="settings-address" :title="t('settings.nav.address')" :subtitle="t('settings.desc.address')" icon="i-lucide-globe">
    <AppEmpty v-if="failed && !address" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
    <div v-else-if="!address" class="flex flex-col gap-6"><USkeleton v-for="n in 3" :key="n" class="h-36 rounded-lg" /></div>
    <div v-else class="flex flex-col gap-6">
      <SettingsBlock :title="t('settings.address.workspace')" :description="t('settings.address.workspaceHint')" icon="i-lucide-link">
        <AppCopyField :value="address.url" :label="t('settings.address.current')" monospace />
        <UFormField :label="t('settings.address.newLabel')" :help="t('settings.address.rules')">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
            <UInput v-model="wanted" :placeholder="address.subdomain" class="w-full sm:max-w-sm" :ui="{ trailing: 'pe-2' }">
              <template #trailing><span class="text-xs text-muted">.{{ config.public.rootDomain }}</span></template>
            </UInput>
            <UButton :label="t('settings.address.change')" icon="i-lucide-arrow-right-left" color="neutral" :disabled="!canChange" @click="(typed = ''), (changeOpen = true)" />
          </div>
        </UFormField>
        <p v-if="checking" class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-loader-circle" class="size-3.5 animate-spin" />{{ t('settings.address.checking') }}</p>
        <p v-else-if="canChange" class="flex items-center gap-1.5 text-xs text-success"><UIcon name="i-lucide-circle-check" class="size-3.5" />{{ t('settings.address.free', { url: `${cleaned}.${config.public.rootDomain}` }) }}</p>
        <p v-else-if="availability && !availability.available" class="flex items-center gap-1.5 text-xs text-error"><UIcon name="i-lucide-circle-x" class="size-3.5" />{{ t(`settings.address.reason.${availability.reason}`) }}</p>
        <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-file-text" class="mt-0.5 size-3.5 shrink-0" />{{ t('settings.address.formsAt', { host: formsHost }) }}</p>
        <div v-if="address.previous.length" class="flex flex-col gap-1.5 rounded-lg border border-default p-3">
          <span class="text-xs font-medium text-highlighted">{{ t('settings.address.previous') }}</span>
          <span v-for="item in address.previous" :key="item.subdomain" class="flex flex-wrap items-center gap-2 text-xs text-muted">
            <span class="font-mono text-default">{{ item.subdomain }}.{{ config.public.rootDomain }}</span><UIcon name="i-lucide-arrow-right" class="size-3 rtl:rotate-180" />{{ t('settings.address.until', { when: dateTime(item.until) }) }}
          </span>
        </div>
      </SettingsBlock>

    </div>

    <AppModal v-model:open="changeOpen" :title="t('settings.address.confirmTitle')" :description="t('settings.address.confirmDesc', { old: address?.url ?? '', url: `https://${cleaned}.${config.public.rootDomain}` })" keep-open>
      <template #body>
        <UFormField :label="t('settings.address.typeNew', { name: cleaned })">
          <UInput v-model="typed" autocomplete="off" autofocus class="w-full" @keydown.enter="change" />
        </UFormField>
      </template>
      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="changeOpen = false" />
          <UButton :label="t('settings.address.change')" icon="i-lucide-arrow-right-left" color="neutral" :loading="changing" :disabled="typed.trim().toLowerCase() !== cleaned" @click="change" />
        </div>
      </template>
    </AppModal>
  </SettingsPage>
</template>
