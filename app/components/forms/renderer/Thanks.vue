<!--
  Renderer: the thank-you screen. Title and message from the server after sending (in the
  respondent's language) or from the form; preview says nothing was sent and offers Start again.
-->
<script setup lang="ts">
import type { RendererRespondent } from '#shared/types/public'

defineProps<{ title?: string; message?: string; icon: boolean; themed: boolean; preview?: boolean; respondent?: RendererRespondent }>()
const emit = defineEmits<{ another: []; restart: [] }>()
const { t } = useI18n()
</script>

<template>
  <div class="flex flex-col items-center gap-3 py-10 text-center">
    <UIcon v-if="icon" name="i-lucide-circle-check" class="size-10" :class="themed ? 'text-(--ui-primary)' : 'text-success'" />
    <h2 class="text-xl font-semibold text-highlighted">{{ title || t('renderer.thanks') }}</h2>
    <p v-if="message" class="max-w-md text-sm text-muted">{{ message }}</p>
    <p v-if="preview" class="text-xs text-muted">{{ t('builder.preview.nothingSent') }}</p>
    <FormsRendererAfter v-if="respondent && !preview" mode="thanks" :org="respondent.org" :embedded="respondent.embedded" class="pt-2" @another="emit('another')" />
    <UButton v-if="preview" :label="t('builder.preview.restart')" icon="i-lucide-rotate-ccw" color="neutral" variant="outline" size="sm" @click="emit('restart')" />
  </div>
</template>
