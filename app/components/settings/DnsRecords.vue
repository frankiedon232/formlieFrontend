<!--
  The DNS records a workspace adds at its domain provider (own domain, own email address): type, name, a value
  to copy and whether the last check found it. Scrolls sideways on phones instead of squeezing the values.
-->
<script setup lang="ts">
defineProps<{ records: { type: string; name: string; value: string; found: boolean; optional?: boolean }[] }>()
const { t } = useI18n()
</script>

<template>
  <div class="overflow-x-auto rounded-lg border border-default">
    <table class="w-full min-w-[34rem] text-start text-xs">
      <thead class="bg-elevated/50 text-muted">
        <tr>
          <th class="px-3 py-2 text-start font-medium">{{ t('settings.address.type') }}</th>
          <th class="px-3 py-2 text-start font-medium">{{ t('settings.address.name') }}</th>
          <th class="px-3 py-2 text-start font-medium">{{ t('settings.address.value') }}</th>
          <th class="px-3 py-2"><span class="sr-only">{{ t('settings.dns.found') }}</span></th>
        </tr>
      </thead>
      <tbody class="divide-y divide-default">
        <tr v-for="record in records" :key="`${record.type}-${record.name}`">
          <td class="px-3 py-2 align-top font-medium text-highlighted">
            {{ record.type }}
            <span v-if="record.optional" class="block text-[10px] font-normal text-muted">{{ t('settings.dns.optional') }}</span>
          </td>
          <td class="max-w-56 px-3 py-2 align-top font-mono break-all">{{ record.name }}</td>
          <td class="px-3 py-2 align-top"><AppCopyField :value="record.value" monospace /></td>
          <td class="px-3 py-2 align-top">
            <UIcon :name="record.found ? 'i-lucide-circle-check' : 'i-lucide-circle-dashed'" class="mt-2 size-4" :class="record.found ? 'text-success' : 'text-muted'" :aria-label="record.found ? t('settings.address.found') : t('settings.address.missing')" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
