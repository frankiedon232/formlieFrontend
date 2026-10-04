<!--
  Opening an organisation-only form (F10 M3, decision 96): `/forms/open?key={formKey}` on the
  workspace's portal. Signed-in members (the sign-in screen comes first when needed) get a 2-minute
  pass from the API and are sent straight back to the form, which trades it for its own unlock.
  A form of another workspace (or one that doesn't exist) says so instead.
-->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.forms' })

const { t } = useI18n()
const route = useRoute()
const api = useApi()
const { handle } = useErrorHandler()
/** notYours: the form belongs to another workspace (or doesn't exist); error: anything else, retry. */
const failed = ref<'notYours' | 'error' | null>(null)
const busy = ref(false)

async function open() {
  const key = String(route.query.key ?? '')
  failed.value = null
  busy.value = true
  try {
    const { data } = await api.post<{ url: string }>('/forms/pass', { key })
    await navigateTo(data.url, { external: true, replace: true })
  } catch (error) {
    const code = handle(error, { silent: true }).code
    failed.value = code === 'FRM-PERM-1001' || code === 'FRM-GEN-1004' ? 'notYours' : 'error'
  } finally {
    busy.value = false
  }
}
onMounted(open)
</script>

<template>
  <AppPanel id="forms-open" :title="t('public.member.openTitle')">
    <div class="flex flex-1 items-center justify-center py-16">
      <UCard class="w-full max-w-md" :ui="{ body: 'p-6 sm:p-8' }">
        <div class="flex flex-col items-center gap-3 text-center">
          <span class="flex size-12 items-center justify-center rounded-full bg-elevated">
            <UIcon :name="failed === 'notYours' ? 'i-lucide-building-2' : failed ? 'i-lucide-cloud-off' : 'i-lucide-loader-circle'" class="size-6 text-muted" :class="failed ? '' : 'animate-spin'" />
          </span>
          <h1 class="text-lg font-semibold text-highlighted">
            {{ failed === 'notYours' ? t('public.member.notYours') : failed === 'error' ? t('public.error.title') : t('public.member.opening') }}
          </h1>
          <p v-if="failed" class="text-sm text-muted">{{ failed === 'notYours' ? t('public.member.notYoursDesc') : t('public.error.desc') }}</p>
          <div v-if="failed" class="flex flex-wrap justify-center gap-2">
            <UButton v-if="failed === 'error'" :label="t('common.retry')" icon="i-lucide-rotate-cw" color="neutral" :loading="busy" @click="open" />
            <UButton :label="t('nav.forms')" icon="i-lucide-arrow-left" color="neutral" variant="outline" to="/forms" />
          </div>
        </div>
      </UCard>
    </div>
  </AppPanel>
</template>
