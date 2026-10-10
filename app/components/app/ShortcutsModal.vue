<script setup lang="ts">
const { t } = useI18n()
const { shortcutsOpen } = useAppUi()
const { general, navigation } = useShortcutList()
const sections = computed(() => [general.value, navigation.value])
</script>

<template>
  <AppModal
    v-model:open="shortcutsOpen"
    :title="t('shortcuts.title')"
    :description="t('shortcuts.description')"
  >
    <template #body>
      <div class="grid gap-6 sm:grid-cols-2">
        <section v-for="section in sections" :key="section.title">
          <h3 class="mb-2 text-xs font-medium text-dimmed uppercase">{{ section.title }}</h3>
          <ul class="divide-y divide-default">
            <li
              v-for="item in section.items"
              :key="item.label"
              class="flex items-center justify-between gap-4 py-2 text-sm"
            >
              <span class="text-default">{{ item.label }}</span>
              <span class="flex shrink-0 items-center gap-1">
                <template v-for="(key, index) in item.keys" :key="key">
                  <span v-if="index > 0 && 'chain' in item" class="text-xs text-dimmed">
                    {{ t('shortcuts.then') }}
                  </span>
                  <UKbd :value="key" />
                </template>
              </span>
            </li>
          </ul>
        </section>
      </div>
    </template>
  </AppModal>
</template>
