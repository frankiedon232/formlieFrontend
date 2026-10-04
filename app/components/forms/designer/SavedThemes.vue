<!--
  "Your themes" in the designer: the workspace's saved designs (apply in one click, confirm when
  it replaces a custom design) and "Save as theme" / "Update theme" for the current design.
-->
<script setup lang="ts">
import type { SavedTheme } from '#shared/types/forms'

const { t } = useI18n()
const d = useDesigner()
const library = useThemes()
const confirm = useConfirm()
onMounted(() => library.load())

const saveOpen = ref(false)
const current = computed(() => library.themes.value.find(item => item.id === d.themeId.value) ?? null)

async function apply(saved: SavedTheme) {
  if (d.customised.value && d.themeId.value !== saved.id && !(await confirm({ title: t('designer.replaceTitle'), description: t('designer.replaceDesc'), confirmLabel: t('designer.replace') })))
    return
  d.applySaved(saved)
}
</script>

<template>
  <section class="flex flex-col gap-2">
    <div class="flex items-center justify-between gap-2">
      <p class="text-xs text-muted">{{ t('themes.yoursHint') }}</p>
      <UButton :label="t('themes.save')" icon="i-lucide-bookmark-plus" color="neutral" variant="outline" size="xs" class="shrink-0" @click="saveOpen = true" />
    </div>

    <div v-if="library.loading.value && !library.loaded.value" class="grid grid-cols-2 gap-2" :aria-label="t('common.loading')">
      <USkeleton v-for="i in 2" :key="i" class="h-24" />
    </div>
    <p v-else-if="!library.themes.value.length" class="text-xs text-muted">{{ t('themes.noneYet') }}</p>
    <div v-else class="grid max-h-64 grid-cols-2 gap-2 overflow-y-auto">
      <button
        v-for="saved in library.themes.value"
        :key="saved.id"
        type="button"
        class="flex flex-col gap-1.5 rounded-lg border p-1.5 text-start transition-colors hover:border-accented focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        :class="saved.id === d.themeId.value ? 'border-(--ui-border-inverted)' : 'border-default'"
        :aria-pressed="saved.id === d.themeId.value"
        :aria-label="t('themes.apply', { name: saved.name })"
        @click="apply(saved)"
      >
        <FormsDesignerSwatch :theme="saved.tokens" />
        <span class="truncate px-0.5 text-xs font-medium text-highlighted">{{ saved.name }}</span>
      </button>
    </div>

    <FormsDesignerSaveThemeModal v-model:open="saveOpen" :current="current" />
  </section>
</template>
