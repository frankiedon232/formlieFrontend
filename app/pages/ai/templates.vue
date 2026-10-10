<!--
  AI assistant → Template ideas (F19 M2): a template for a use case, with a matching design, saved to the
  workspace's templates; or designs from a brand colour, saved to Themes. The switch is remembered in the
  address (?mode=design).
-->
<script setup lang="ts">
import type { AiUsage } from '#shared/types/ai'

definePageMeta({ breadcrumb: 'nav.aiTemplates' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const { can } = useCan()
const ai = useAi()
useHead({ title: () => t('nav.aiTemplates') })

const mode = computed({
  get: () => (route.query.mode === 'design' ? 'design' : 'template'),
  set: value => void router.replace({ query: { ...route.query, mode: value === 'design' ? 'design' : undefined } }),
})
const modes = computed(() => [
  { value: 'template', label: t('ai.templates.mode.template'), icon: 'i-lucide-layout-template' },
  { value: 'design', label: t('ai.templates.mode.design'), icon: 'i-lucide-palette' },
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
const brand = computed(() => ai.settings.value?.brand_color ?? null)
onMounted(() => {
  void ai.load()
  void loadUsage()
})
</script>

<template>
  <AppPanel id="ai-templates" :title="t('nav.aiTemplates')" :subtitle="t('ai.section.templates')" subtitle-icon="i-lucide-layout-template">
    <template #actions>
      <UButton v-if="can('ai.history')" :label="t('nav.aiHistory')" icon="i-lucide-history" color="neutral" variant="outline" :to="{ path: '/ai/history', query: { kind: mode === 'design' ? 'theme' : 'template' } }" />
    </template>

    <AiOff v-if="!ai.enabled.value" />
    <template v-else>
      <UTabs v-model="mode" :items="modes" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="self-start" />
      <AiDesignIdea v-if="mode === 'design'" :left="left" :brand="brand" @used="loadUsage" />
      <AiTemplateIdea v-else :left="left" @used="loadUsage" />
    </template>
  </AppPanel>
</template>
