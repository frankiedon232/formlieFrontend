<!--
  Formalie's outgoing addresses (a platform setting): what to allow in the database's firewall so
  Formalie's servers can reach it. Each one copies with a click.
-->
<script setup lang="ts">
import type { DataSourceMeta } from '#shared/types/datasources'

const { t } = useI18n()
const api = useApi()
const ips = ref<string[] | null>(null)
const { copy, copied } = useClipboard({ legacy: true, copiedDuring: 1500 })
const last = ref('')
onMounted(async () => {
  try {
    ips.value = (await api.get<DataSourceMeta>('/datasources/meta', undefined, { background: true })).data.egress_ips
  } catch {
    ips.value = []
  }
})
function copyIp(ip: string) {
  last.value = ip
  void copy(ip)
}
</script>

<template>
  <div class="flex flex-col gap-2 rounded-lg border border-default p-3">
    <div class="flex items-start gap-2">
      <UIcon name="i-lucide-shield-check" class="mt-0.5 size-4 shrink-0 text-muted" />
      <div class="flex min-w-0 flex-col">
        <p class="text-sm font-medium text-highlighted">{{ t('dataSources.egress.title') }}</p>
        <p class="text-xs text-muted">{{ t('dataSources.egress.desc') }}</p>
      </div>
    </div>
    <div v-if="!ips" class="flex gap-2"><USkeleton v-for="n in 3" :key="n" class="h-7 w-28 rounded-md" /></div>
    <div v-else class="flex flex-wrap gap-2">
      <UButton
        v-for="ip in ips"
        :key="ip"
        :label="ip"
        :icon="copied && last === ip ? 'i-lucide-check' : 'i-lucide-copy'"
        color="neutral"
        variant="outline"
        size="xs"
        class="font-mono"
        dir="ltr"
        :aria-label="t('dataSources.egress.copy', { ip })"
        @click="copyIp(ip)"
      />
    </div>
  </div>
</template>
