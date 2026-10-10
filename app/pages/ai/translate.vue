<!--
  AI assistant → Translations (F19 M5): Translate a form into any of the 20 languages (reviewed side by side,
  then saved into its draft) or Rewrite it in plainer words and the tone wanted. The switch is in the
  address (?mode=rewrite). In the builder, the translation screen has "Translate the rest with AI" too.
-->
<script setup lang="ts">
import type { AiUsage } from '#shared/types/ai'

definePageMeta({ breadcrumb: 'nav.aiTranslate' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const { can } = useCan()
const ai = useAi()
useHead({ title: () => t('nav.aiTranslate') })

const mode = computed({
  get: () => (route.query.mode === 'rewrite' ? 'rewrite' : 'translate'),
  set: value => void router.replace({ query: { ...route.query, mode: value === 'rewrite' ? 'rewrite' : undefined } }),
})
const modes = computed(() => [
  { value: 'translate', label: t('ai.translate.mode'), icon: 'i-lucide-languages' },
  { value: 'rewrite', label: t('ai.rewrite.mode'), icon: 'i-lucide-pen-line' },
])
const usage = ref<AiUsage | null>(null)
const left = computed(() => (usage.value ? Math.max(0, usage.value.limit - usage.value.used) : null))
const loadUsage = async () => {
  try {
    usage.value = (await api.get<AiUsage>('/ai/usage', undefined, { background: true })).data
  } catch {
    usage.value = null
  }
}
onMounted(() => {
  void ai.load()
  void loadUsage()
})
</script>

<template>
  <AppPanel id="ai-translate" :title="t('nav.aiTranslate')" :subtitle="t('ai.section.translate')" subtitle-icon="i-lucide-languages">
    <template #actions>
      <UButton v-if="can('ai.history')" :label="t('nav.aiHistory')" icon="i-lucide-history" color="neutral" variant="outline" :to="{ path: '/ai/history', query: { kind: mode === 'rewrite' ? 'rewrite' : 'translate' } }" />
    </template>

    <AiOff v-if="!ai.enabled.value" />
    <template v-else>
      <UTabs v-model="mode" :items="modes" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="self-start" />
      <AiRewriteWork v-if="mode === 'rewrite'" @used="loadUsage" />
      <AiTranslateWork v-else :left="left" @used="loadUsage" />
    </template>
  </AppPanel>
</template>
