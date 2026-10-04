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
const failed = ref(false)

onMounted(async () => {
  const key = String(route.query.key ?? '')
  try {
    const { data } = await api.post<{ url: string }>('/forms/pass', { key })
    await navigateTo(data.url, { external: true, replace: true })
  } catch {
    failed.value = true
  }
})
</script>

<template>
  <AppPanel id="forms-open" :title="t('public.member.openTitle')">
    <div class="flex flex-1 items-center justify-center py-16">
      <UCard class="w-full max-w-md" :ui="{ body: 'p-6 sm:p-8' }">
        <div class="flex flex-col items-center gap-3 text-center">
          <span class="flex size-12 items-center justify-center rounded-full bg-elevated">
            <UIcon :name="failed ? 'i-lucide-building-2' : 'i-lucide-loader-circle'" class="size-6 text-muted" :class="failed ? '' : 'animate-spin'" />
          </span>
          <h1 class="text-lg font-semibold text-highlighted">{{ failed ? t('public.member.notYours') : t('public.member.opening') }}</h1>
          <p v-if="failed" class="text-sm text-muted">{{ t('public.member.notYoursDesc') }}</p>
          <UButton v-if="failed" :label="t('nav.forms')" icon="i-lucide-arrow-left" color="neutral" variant="outline" to="/forms" />
        </div>
      </UCard>
    </div>
  </AppPanel>
</template>
