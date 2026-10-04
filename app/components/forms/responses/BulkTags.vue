<!--
  Bulk tags for the selected responses (F11 M2): type a tag or pick one already in use on the form,
  then add it to every selected response or remove it from them. Enter adds; the panel closes
  when the change is done (the list shows a toast and refreshes).
-->
<script setup lang="ts">
const props = defineProps<{ count: number; tags: { value: string; count: number }[]; busy?: boolean }>()
const emit = defineEmits<{ apply: [action: 'tag' | 'untag', tag: string] }>()
const { t } = useI18n()
const { number } = useFormat()

const open = ref(false)
const tag = ref('')
const clean = computed(() => tag.value.trim().slice(0, 40))
const known = computed(() => props.tags.filter(item => !clean.value || item.value.toLowerCase().includes(clean.value.toLowerCase())).slice(0, 12))
watch(open, value => value && (tag.value = ''))
function apply(action: 'tag' | 'untag') {
  if (!clean.value) return
  emit('apply', action, clean.value)
  open.value = false
}
</script>

<template>
  <UPopover v-model:open="open" :content="{ align: 'start' }">
    <UButton :label="t('responses.bulkTags.button')" icon="i-lucide-tag" trailing-icon="i-lucide-chevron-down" color="neutral" variant="outline" size="sm" :loading="busy" />
    <template #content>
      <form class="flex w-72 flex-col gap-3 p-3" @submit.prevent="apply('tag')">
        <UFormField :label="t('responses.bulkTags.label')" :help="t('responses.bulkTags.help', { n: number(count) }, count)">
          <UInput v-model="tag" :placeholder="t('responses.detail.addTag')" icon="i-lucide-tag" maxlength="40" class="w-full" autofocus />
        </UFormField>
        <div v-if="known.length" class="flex flex-wrap gap-1.5" :aria-label="t('responses.bulkTags.inUse')">
          <UButton
            v-for="item in known"
            :key="item.value"
            :label="item.value"
            color="neutral"
            :variant="item.value === clean ? 'solid' : 'soft'"
            size="xs"
            class="rounded-full"
            @click="tag = item.value"
          />
        </div>
        <div class="flex gap-2">
          <UButton type="submit" :label="t('responses.bulkTags.add', { n: number(count) }, count)" icon="i-lucide-plus" color="neutral" size="sm" class="flex-1 justify-center" :disabled="!clean" />
          <UButton :label="t('responses.bulkTags.remove')" icon="i-lucide-minus" color="neutral" variant="outline" size="sm" :disabled="!clean" @click="apply('untag')" />
        </div>
      </form>
    </template>
  </UPopover>
</template>
