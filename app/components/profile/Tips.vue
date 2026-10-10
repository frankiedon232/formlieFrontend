<!-- My profile → Tips on new pages (F25, owner 2026-10-10): the first-visit tours on or off, and every tip shown again. -->
<script setup lang="ts">
const { t } = useI18n()
const tours = useTours()
const toast = useToast()
const { busy, run } = useBusy()
onMounted(() => void tours.load())

const enabled = computed(() => tours.mine.value?.enabled ?? true)
const seen = computed(() => tours.mine.value?.seen.length ?? 0)
const setEnabled = (value: boolean) => run(() => tours.setEnabled(value))
async function showAgain() {
  await run(() => tours.showAgain())
  toast.add({ title: t('profile.tips.reset'), icon: 'i-lucide-route', color: 'success' })
}
</script>

<template>
  <SettingsBlock :title="t('profile.tips.title')" :description="t('profile.tips.desc')" icon="i-lucide-route">
    <div class="flex flex-col gap-3">
      <USkeleton v-if="!tours.mine.value" class="h-10 w-full" />
      <template v-else>
        <USwitch :model-value="enabled" :label="t('profile.tips.enabled')" :description="t('profile.tips.enabledHint')" color="neutral" :disabled="busy" @update:model-value="value => setEnabled(!!value)" />
        <div class="flex flex-wrap items-center gap-2">
          <UButton :label="t('profile.tips.again')" icon="i-lucide-rotate-ccw" color="neutral" variant="outline" size="sm" :loading="busy" :disabled="!seen" @click="showAgain" />
          <span class="text-xs text-muted">{{ t('profile.tips.seen', { n: seen }, seen) }}</span>
        </div>
      </template>
    </div>
  </SettingsBlock>
</template>
