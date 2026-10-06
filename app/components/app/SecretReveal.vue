<!--
  A secret that can be seen again (owner, 2026-10-06: tokens, API keys, webhook secrets). Masked by
  default; Show asks for the person's password right here (no second dialog), the server checks it
  and records the view in the audit trail, then each value shows with Copy for 60 seconds before it
  is masked again. Wrong passwords say how many tries are left; five lock it for 15 minutes.
  `endpoint` answers `{ <key>: value }`; `labels` names the keys to show, in order.
-->
<script setup lang="ts">
const props = defineProps<{ preview: string; endpoint: string; labels: Record<string, string>; viewable?: boolean; title?: string }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const asking = ref(false)
const password = ref('')
const error = ref<string>()
const busy = ref(false)
const shown = ref<{ key: string; label: string; value: string }[] | null>(null)
const left = ref(0)
let timer: ReturnType<typeof setInterval> | null = null
function hide() {
  shown.value = null
  if (timer) clearInterval(timer)
  timer = null
}
onBeforeUnmount(hide)
watch(() => props.endpoint, () => {
  hide()
  asking.value = false
})

async function confirm() {
  if (busy.value || !password.value) return
  busy.value = true
  error.value = undefined
  try {
    const { data } = await api.post<Record<string, string>>(props.endpoint, { password: password.value })
    shown.value = Object.entries(props.labels)
      .filter(([key]) => data[key])
      .map(([key, label]) => ({ key, label, value: data[key]! }))
    asking.value = false
    password.value = ''
    left.value = 60
    timer = setInterval(() => (--left.value <= 0 ? hide() : undefined), 1000)
  } catch (caught) {
    const normalised = handle(caught, { silent: true })
    if (normalised.code === 'FRM-AUTH-1013') error.value = t('secrets.wrong', { n: Number(normalised.details?.[0]?.message ?? 0) })
    else if (normalised.code === 'FRM-AUTH-1004') error.value = t('secrets.locked')
    else handle(caught)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="flex flex-col gap-2 rounded-lg border border-default p-3" :aria-label="title ?? t('secrets.title')">
    <div class="flex items-center justify-between gap-2">
      <div class="flex min-w-0 items-center gap-2">
        <UIcon :name="shown ? 'i-lucide-eye' : 'i-lucide-lock-keyhole'" class="size-4 shrink-0 text-muted" />
        <div class="flex min-w-0 flex-col">
          <span class="text-[11px] text-muted">{{ title ?? t('secrets.title') }}</span>
          <span v-if="!shown" class="truncate font-mono text-sm text-highlighted" dir="ltr">{{ preview.replace('…', '••••••••••••') }}</span>
        </div>
      </div>
      <UButton v-if="shown" :label="t('secrets.hide', { n: left })" icon="i-lucide-eye-off" color="neutral" variant="ghost" size="xs" @click="hide" />
      <UButton v-else-if="viewable !== false && !asking" :label="t('secrets.show')" icon="i-lucide-eye" color="neutral" variant="outline" size="xs" @click="asking = true" />
    </div>

    <p v-if="viewable === false" class="text-xs text-muted">{{ t('secrets.notViewable') }}</p>

    <form v-if="asking" class="flex flex-col gap-2" @submit.prevent="confirm">
      <p class="text-xs text-muted">{{ t('secrets.ask') }}</p>
      <UFormField :error="error">
        <UFieldGroup class="w-full">
          <UInput v-model="password" type="password" autocomplete="current-password" :placeholder="t('secrets.password')" class="min-w-0 flex-1" autofocus />
          <UButton type="submit" :label="t('secrets.confirm')" color="neutral" :loading="busy" :disabled="!password" />
        </UFieldGroup>
      </UFormField>
      <UButton :label="t('common.cancel')" color="neutral" variant="link" size="xs" class="self-start px-0" @click="asking = false; password = ''; error = undefined" />
    </form>

    <div v-if="shown" class="flex flex-col gap-2">
      <AppCopyField v-for="item in shown" :key="item.key" :value="item.value" :label="item.label" monospace />
      <p class="text-xs text-muted">{{ t('secrets.shownNote') }}</p>
    </div>
  </section>
</template>
