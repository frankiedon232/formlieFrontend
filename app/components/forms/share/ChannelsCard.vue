<!--
  Where people can answer (owner, 2026-10-06): the web link, an embed on a website, the API service;
  at least one. "API only" in one click: the form then has no web address at all (its link, short
  link and embed answer "not found", exactly like a form that does not exist) and is only reached
  through API endpoints. The cards for links and embeds below follow what is on.
-->
<script setup lang="ts">
import { FORM_CHANNELS, type FormChannel, type ShareDraft } from '#shared/types/forms'

const draft = defineModel<ShareDraft>('draft', { required: true })
const { t } = useI18n()
const ICONS: Record<FormChannel, string> = { link: 'i-lucide-link', embed: 'i-lucide-app-window', api: 'i-lucide-code-xml' }
const on = (channel: FormChannel) => draft.value.channels.includes(channel)
function toggle(channel: FormChannel, value: boolean) {
  const next = value ? [...draft.value.channels, channel] : draft.value.channels.filter(item => item !== channel)
  if (!next.length) return
  draft.value.channels = FORM_CHANNELS.filter(item => next.includes(item))
}
const apiOnly = computed(() => draft.value.channels.length === 1 && draft.value.channels[0] === 'api')
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div class="flex flex-col gap-0.5">
        <h3 class="text-sm font-semibold text-highlighted">{{ t('forms.channels.title') }}</h3>
        <p class="text-xs text-muted">{{ t('forms.channels.desc') }}</p>
      </div>
      <UButton
        :label="apiOnly ? t('forms.channels.allThree') : t('forms.channels.makeApiOnly')"
        :icon="apiOnly ? 'i-lucide-globe' : 'i-lucide-code-xml'"
        color="neutral"
        variant="outline"
        size="xs"
        @click="draft.channels = apiOnly ? [...FORM_CHANNELS] : ['api']"
      />
    </div>
    <div class="grid gap-2 sm:grid-cols-3" role="group" :aria-label="t('forms.channels.title')">
      <label
        v-for="channel in FORM_CHANNELS"
        :key="channel"
        class="flex h-full cursor-pointer flex-col gap-2 rounded-lg border p-3 transition-colors"
        :class="on(channel) ? 'border-(--ui-border-inverted) bg-elevated/40' : 'border-default hover:border-accented'"
      >
        <span class="flex items-center justify-between gap-2">
          <span class="flex items-center gap-2 text-sm font-medium text-highlighted"><UIcon :name="ICONS[channel]" class="size-4" />{{ t(`forms.channels.${channel}`) }}</span>
          <USwitch :model-value="on(channel)" size="sm" :disabled="on(channel) && draft.channels.length === 1" :aria-label="t(`forms.channels.${channel}`)" @update:model-value="value => toggle(channel, !!value)" />
        </span>
        <span class="text-xs text-muted">{{ t(`forms.channels.${channel}Hint`) }}</span>
      </label>
    </div>
    <UAlert v-if="apiOnly" icon="i-lucide-lock" color="neutral" variant="subtle" :title="t('forms.channels.apiOnly')" :description="t('forms.channels.apiOnlyHint')" />
  </UCard>
</template>
