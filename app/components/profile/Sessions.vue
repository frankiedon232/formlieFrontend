<!--
  My profile → Where you're signed in (F16 M5): this person's devices (browser, system, address, last
  activity); sign out one, or every other one. This device is marked and stays signed in.
-->
<script setup lang="ts">
import type { MySession } from '#shared/types/profile'

const { t } = useI18n()
const api = useApi()
const toast = useToast()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const { relative, dateTime } = useFormat()

const list = ref<MySession[] | null>(null)
const busy = ref<string | null>(null)
async function load() {
  try {
    list.value = (await api.get<MySession[]>('/me/sessions', undefined, { background: !!list.value })).data
  } catch (error) {
    handle(error, { silent: true })
    list.value ??= []
  }
}
onMounted(load)
async function end(id: string | 'others') {
  if (id === 'others' && !(await confirm({ title: t('profile.sessions.othersTitle'), description: t('profile.sessions.othersDesc'), confirmLabel: t('profile.sessions.others') }))) return
  busy.value = id
  try {
    list.value = (id === 'others' ? await api.post<MySession[]>('/me/sessions/sign-out-others') : await api.del<MySession[]>(`/me/sessions/${id}`)).data
    toast.add({ title: t('profile.sessions.ended'), color: 'success', icon: 'i-lucide-log-out' })
  } catch (error) {
    handle(error)
  } finally {
    busy.value = null
  }
}
const icon = (type: string) => (type === 'mobile' ? 'i-lucide-smartphone' : type === 'tablet' ? 'i-lucide-tablet' : 'i-lucide-monitor')
defineExpose({ reload: load })
</script>

<template>
  <SettingsBlock :title="t('profile.sessions.title')" :description="t('profile.sessions.desc')" icon="i-lucide-monitor-smartphone">
    <div v-if="!list" class="flex flex-col gap-2"><USkeleton v-for="n in 2" :key="n" class="h-14 rounded-lg" /></div>
    <ul v-else class="flex flex-col divide-y divide-default rounded-lg border border-default">
      <li v-for="item in list" :key="item.id" class="flex items-center gap-3 p-3" :class="busy === item.id ? 'opacity-60' : ''">
        <UIcon :name="icon(item.device.type)" class="size-5 shrink-0 text-muted" />
        <div class="flex min-w-0 flex-1 flex-col">
          <span class="flex items-center gap-2 text-sm font-medium text-highlighted">
            {{ [item.device.browser, item.device.os].filter(Boolean).join(' · ') || t('profile.sessions.unknown') }}
            <UBadge v-if="item.current" :label="t('profile.sessions.this')" color="success" variant="subtle" size="sm" />
          </span>
          <UTooltip :text="dateTime(item.last_active_at)"><span class="truncate text-xs text-muted" dir="auto">{{ item.ip }} · {{ t('profile.sessions.active', { when: relative(item.last_active_at) }) }}</span></UTooltip>
        </div>
        <UButton v-if="!item.current" :label="t('profile.sessions.signOut')" icon="i-lucide-log-out" color="neutral" variant="outline" size="xs" :loading="busy === item.id" :disabled="!!busy" @click="end(item.id)" />
      </li>
    </ul>
    <div v-if="list && list.some(item => !item.current)"><UButton :label="t('profile.sessions.others')" icon="i-lucide-log-out" color="neutral" variant="outline" size="sm" :loading="busy === 'others'" @click="end('others')" /></div>
  </SettingsBlock>
</template>
