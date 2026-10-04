<!-- Save and resume (F10 M2): "saved a moment ago" status under the form + "Save and continue later". -->
<script setup lang="ts">
import type { RendererRespondent } from '#shared/types/public'

defineProps<{ resume: NonNullable<RendererRespondent['resume']>; color: 'primary' | 'neutral' }>()
defineEmits<{ later: [] }>()
const { t } = useI18n()
const { relative } = useFormat()
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-2 border-t border-(--ui-border) pt-3 text-xs text-muted">
    <span class="flex items-center gap-1.5" role="status" aria-live="polite">
      <UIcon
        :name="resume.state === 'saving' ? 'i-lucide-loader-circle' : resume.state === 'error' ? 'i-lucide-cloud-alert' : 'i-lucide-cloud-check'"
        class="size-3.5 shrink-0"
        :class="resume.state === 'saving' ? 'animate-spin' : resume.state === 'error' ? 'text-(--ui-error)' : ''"
      />
      {{
        resume.state === 'saving'
          ? t('renderer.resume.saving')
          : resume.state === 'error'
            ? t('renderer.resume.notSaved')
            : resume.savedAt
              ? t('renderer.resume.saved', { when: relative(resume.savedAt) })
              : t('renderer.resume.auto')
      }}
    </span>
    <UButton :label="t('renderer.resume.later')" icon="i-lucide-bookmark" :color="color" variant="link" size="xs" class="px-0" @click="$emit('later')" />
  </div>
</template>
