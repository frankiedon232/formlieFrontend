<!-- "Was this helpful?" under an article (F25): yes / no, and on "no" what was missing (optional); kept for the Formalie team. -->
<script setup lang="ts">
const props = defineProps<{ articleId: string; initial: boolean | null }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const answer = ref<boolean | null>(props.initial)
const comment = ref('')
const asking = ref(false)
const thanked = ref(props.initial !== null)
const busy = ref(false)
watch(
  () => props.articleId,
  () => ((answer.value = props.initial), (thanked.value = props.initial !== null), (asking.value = false), (comment.value = '')),
)
async function send(helpful: boolean, withComment = false) {
  busy.value = true
  try {
    await api.post(`/help/articles/${props.articleId}/feedback`, { helpful, comment: withComment ? comment.value : null }, { background: true })
    answer.value = helpful
    asking.value = !helpful && !withComment
    thanked.value = helpful || withComment
  } catch (error) {
    handle(error)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-3 rounded-lg border border-default p-4">
    <div v-if="!thanked && !asking" class="flex flex-wrap items-center justify-between gap-3">
      <span class="text-sm font-medium text-highlighted">{{ t('help.feedback.question') }}</span>
      <div class="flex gap-2">
        <UButton :label="t('help.feedback.yes')" icon="i-lucide-thumbs-up" color="neutral" variant="outline" size="sm" :loading="busy && answer === null" @click="send(true)" />
        <UButton :label="t('help.feedback.no')" icon="i-lucide-thumbs-down" color="neutral" variant="outline" size="sm" :disabled="busy" @click="send(false)" />
      </div>
    </div>
    <form v-else-if="asking" class="flex flex-col gap-2" @submit.prevent="send(false, true)">
      <UFormField :label="t('help.feedback.missing')">
        <UTextarea v-model="comment" :rows="2" autoresize :maxlength="1000" class="w-full" />
      </UFormField>
      <div class="flex justify-end gap-2">
        <UButton :label="t('help.feedback.skip')" color="neutral" variant="ghost" size="sm" @click="(asking = false), (thanked = true)" />
        <UButton type="submit" :label="t('help.feedback.send')" color="neutral" size="sm" :loading="busy" :disabled="!comment.trim()" />
      </div>
    </form>
    <p v-else class="flex items-center gap-2 text-sm text-muted"><UIcon name="i-lucide-heart" class="size-4" />{{ t('help.feedback.thanks') }}</p>
  </div>
</template>
