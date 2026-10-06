<!--
  Endpoint wizard, step 2 (F13 M1): the service it belongs to (or a new one), the address part
  (lower-case words and hyphens, shown after the organisation's fixed address), what it is for,
  and which form version it uses (always the latest published one by default, or pinned).
-->
<script setup lang="ts">
import type { ApiService } from '#shared/types/apiService'

const props = defineProps<{ base: string; versions: number[]; errors: Record<string, string> }>()
const serviceId = defineModel<string | null>('serviceId', { required: true })
const name = defineModel<string>('name', { required: true })
const description = defineModel<string>('description', { required: true })
const version = defineModel<number | null>('version', { required: true })
const { t } = useI18n()
const api = useApi()

const services = ref<ApiService[] | null>(null)
async function loadServices() {
  try {
    services.value = (await api.list<ApiService>('/api-services', { page_size: 100, sort: 'name' })).data
    if (!serviceId.value && services.value[0]) serviceId.value = services.value[0].id
  } catch {
    services.value = []
  }
}
onMounted(loadServices)
const serviceValue = computed({ get: () => serviceId.value ?? undefined, set: (value?: string) => (serviceId.value = value ?? null) })
const serviceItems = computed(() => (services.value ?? []).map(service => ({ label: service.name, value: service.id, description: service.status === 'active' ? undefined : t('apiService.serviceOff') })))
const versionItems = computed(() => [{ label: t('apiService.latestVersion'), value: 'latest' }, ...props.versions.map(n => ({ label: t('apiService.versionN', { n }), value: String(n) }))])
const versionValue = computed({ get: () => (version.value == null ? 'latest' : String(version.value)), set: value => (version.value = value === 'latest' ? null : Number(value)) })
// Lower-case words and hyphens as people type
const typed = computed({ get: () => name.value, set: value => (name.value = value.toLowerCase().replace(/[\s_]+/g, '-').replace(/[^a-z0-9-]/g, '').slice(0, 64)) })

const newOpen = ref(false)
async function created(service: ApiService) {
  await loadServices()
  serviceId.value = service.id
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <UFormField :label="t('apiService.col.service')" :error="errors.service_id" :help="t('apiService.wizard.serviceHelp')" required>
      <div class="flex gap-2">
        <USelectMenu v-model="serviceValue" :items="serviceItems" value-key="value" :loading="!services" :placeholder="t('apiService.wizard.pickService')" class="min-w-0 flex-1" />
        <UButton :label="t('apiService.wizard.newService')" icon="i-lucide-plus" color="neutral" variant="outline" class="shrink-0" @click="newOpen = true" />
      </div>
    </UFormField>

    <UFormField :label="t('apiService.wizard.name')" :error="errors.name" :help="t('apiService.wizard.nameHelp')" required>
      <UFieldGroup class="w-full">
        <UBadge :label="`${base}/`" color="neutral" variant="outline" size="lg" class="max-w-[55%] shrink truncate font-mono text-xs" dir="ltr" />
        <UInput v-model="typed" placeholder="register-account" class="min-w-0 flex-1" :ui="{ base: 'font-mono' }" dir="ltr" maxlength="64" />
      </UFieldGroup>
    </UFormField>

    <UFormField :label="t('apiService.service.description')" :hint="t('apiService.optional')">
      <UTextarea v-model="description" :rows="2" autoresize maxlength="300" class="w-full" :placeholder="t('apiService.wizard.descriptionPlaceholder')" />
    </UFormField>

    <UFormField :label="t('apiService.col.version')" :help="t('apiService.wizard.versionHelp')">
      <USelect v-model="versionValue" :items="versionItems" class="w-full sm:w-72" />
    </UFormField>

    <ApiServicesEditModal v-model:open="newOpen" @saved="created" />
  </div>
</template>
