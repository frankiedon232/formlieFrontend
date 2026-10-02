<!-- Shown when the subdomain has no workspace (tenant middleware, F3). Links back to the manage entry. -->
<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const { t } = useI18n()
const config = useRuntimeConfig()
const requestUrl = useRequestURL()

const manageUrl = computed(() => {
  const port = requestUrl.port ? `:${requestUrl.port}` : ''
  return `${requestUrl.protocol}//${config.public.manageSubdomain}.${config.public.rootDomain}${port}/`
})

useHead({ title: () => t('error.workspaceTitle') })
</script>

<template>
  <UCard>
    <UEmpty
      icon="i-lucide-building-2"
      :title="t('error.workspaceTitle')"
      :description="t('error.workspaceDesc', { host: requestUrl.hostname })"
      :actions="[{ label: t('error.findWorkspace'), icon: 'i-lucide-search', to: manageUrl, external: true }]"
      variant="naked"
    />
  </UCard>
</template>
