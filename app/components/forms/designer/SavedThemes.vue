<!--
  "Your themes" in the designer: the workspace's saved designs (apply in one click, no confirm:
  Undo is one click away, owner 2026-10-06) and "Save as theme" / "Update theme" for the current design.
-->
<script setup lang="ts">
import type { SavedTheme } from '#shared/types/forms'

const { t } = useI18n()
const d = useDesigner()
const library = useThemes()
onMounted(() => library.load())

const saveOpen = ref(false)
const current = computed(() => library.themes.value.find(item => item.id === d.themeId.value) ?? null)
// Save as a new theme (themes.create) or update the one the form uses when this person may change it (F22 R2 M3)
const canCreate = computed(() => useCan().can('themes.create'))
const updatable = computed(() => (current.value?.can?.edit ? current.value : null))

function apply(saved: SavedTheme) {
  if (d.themeId.value === saved.id) return
  d.applySaved(saved)
  d.applied(saved.name)
}
</script>

<template>
  <section class="flex flex-col gap-2">
    <div class="flex items-center justify-between gap-2">
      <p class="text-xs text-muted">{{ t('themes.yoursHint') }}</p>
      <UButton v-if="canCreate || updatable" :label="t('themes.save')" icon="i-lucide-bookmark-plus" color="neutral" variant="outline" size="xs" class="shrink-0" @click="saveOpen = true" />
    </div>

    <div v-if="library.loading.value && !library.loaded.value" class="grid grid-cols-2 gap-2" :aria-label="t('common.loading')">
      <USkeleton v-for="i in 2" :key="i" class="h-24" />
    </div>
    <AppEmpty v-else-if="!library.themes.value.length" size="xs" icon="i-lucide-palette" :title="t('themes.noneYet')" />
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

    <FormsDesignerSaveThemeModal v-model:open="saveOpen" :current="updatable" :can-create="canCreate" />
  </section>
</template>
