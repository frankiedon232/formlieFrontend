<!--
  Settings → Security (F14 M3): the IP allowlist. Off by default; when on, people can only sign in and
  use the portal from these addresses or ranges (IPv4 / IPv6, CIDR). "Your address" shows whether you
  would still get in, with one click to add it; saving without it is refused (FRM-AUTH-1017).
-->
<script setup lang="ts">
import type { SecuritySettings } from '#shared/types/settings'
import { isIpOrRange } from '#shared/utils/settings/schemas'

const model = defineModel<SecuritySettings['ip_allowlist']>({ required: true })
defineProps<{ myIp: string | null }>()
const { t } = useI18n()

const uid = useId()
/** Adds a row; a blank one gets the focus so people can type straight away. */
async function add(value = '', label: string | null = null) {
  model.value.entries.push({ value, label })
  if (value) return
  await nextTick()
  document.getElementById(`${uid}-${model.value.entries.length - 1}`)?.focus()
}
const remove = (index: number) => model.value.entries.splice(index, 1)
const valid = (value: string) => !value.trim() || isIpOrRange(value.trim())
const matches = (ip: string | null) => !!ip && model.value.entries.some(entry => isIpOrRange(entry.value.trim()) && ipInCidr(ip, entry.value.trim()))
</script>

<template>
  <div class="flex items-center gap-3 rounded-lg border border-default p-3">
    <span class="flex min-w-0 flex-1 flex-col gap-0.5">
      <span class="text-sm font-medium text-highlighted">{{ t('settings.security.allowlist') }}</span>
      <span class="text-xs text-muted">{{ t('settings.security.allowlistHint') }}</span>
    </span>
    <USwitch v-model="model.enabled" color="neutral" :aria-label="t('settings.security.allowlist')" />
  </div>

  <div v-if="myIp" class="flex flex-wrap items-center gap-2 rounded-lg bg-elevated/50 px-3 py-2 text-xs">
    <UIcon name="i-lucide-wifi" class="size-4 shrink-0 text-muted" />
    <span class="text-muted">{{ t('settings.security.myIp') }}</span>
    <span class="font-mono font-medium text-highlighted">{{ myIp }}</span>
    <template v-if="model.enabled || model.entries.length">
      <UBadge v-if="matches(myIp)" :label="t('settings.security.onList')" color="success" variant="subtle" size="xs" icon="i-lucide-check" />
      <UBadge v-else :label="t('settings.security.notOnList')" color="warning" variant="subtle" size="xs" icon="i-lucide-triangle-alert" />
    </template>
    <UButton v-if="!matches(myIp)" :label="t('settings.security.addMine')" icon="i-lucide-plus" color="neutral" variant="outline" size="xs" class="ms-auto" @click="add(myIp, t('settings.security.mine'))" />
  </div>

  <div v-if="model.entries.length" class="flex flex-col gap-2">
    <div v-for="(entry, index) in model.entries" :key="index" class="grid grid-cols-[minmax(0,1fr)_auto] gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
      <UInput :id="`${uid}-${index}`" v-model="entry.value" :placeholder="t('settings.security.ipPlaceholder')" :color="valid(entry.value) ? undefined : 'error'" :highlight="!valid(entry.value)" class="w-full font-mono" :aria-label="t('settings.security.address')" />
      <UInput :model-value="entry.label ?? ''" :placeholder="t('settings.security.labelPlaceholder')" class="order-3 col-span-2 w-full sm:order-none sm:col-span-1" :aria-label="t('settings.security.label')" @update:model-value="value => (entry.label = String(value) || null)" />
      <UButton icon="i-lucide-x" color="neutral" variant="ghost" :aria-label="t('settings.security.removeIp')" @click="remove(index)" />
    </div>
  </div>
  <AppEmpty v-else size="xs" icon="i-lucide-network" :title="t('settings.security.noIps')" :description="t('settings.security.noIpsDesc')" />
  <div class="flex flex-wrap items-center gap-2">
    <UButton :label="t('settings.security.addIp')" icon="i-lucide-plus" color="neutral" variant="outline" size="sm" :disabled="model.entries.length >= 100" @click="() => add()" />
    <span class="text-xs text-muted">{{ t('settings.security.ipExamples') }}</span>
  </div>
  <UAlert v-if="model.enabled && myIp && !matches(myIp)" color="error" variant="subtle" icon="i-lucide-shield-alert" :title="t('settings.security.lockout')" :description="t('settings.security.lockoutDesc')" />
</template>
