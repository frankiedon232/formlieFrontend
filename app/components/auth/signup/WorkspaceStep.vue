<!--
  Signup step 3: company name + subdomain with live availability (reserved names blocked)
  → workspace created → hand-off URL on the new subdomain.
-->
<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import type { SubdomainAvailability } from '#shared/types/auth'

const emit = defineEmits<{ done: [url: string] }>()
const { t } = useI18n()
const config = useRuntimeConfig()
const api = useApi()
const auth = useAuth()
const { busy, run } = useBusy()

const schema = computed(() => workspaceSchema(t))
const state = reactive({ company_name: '', subdomain: '' })
const touchedSubdomain = ref(false)

watch(
  () => state.company_name,
  name => {
    if (!touchedSubdomain.value) state.subdomain = suggestSubdomain(name)
  },
)

const availability = ref<SubdomainAvailability | null>(null)
const checking = ref(false)
let controller: AbortController | null = null

const check = useDebounceFn(async (value: string) => {
  controller?.abort()
  availability.value = null
  if (value.length < 3 || !isValidSubdomain(value)) return
  controller = new AbortController()
  checking.value = true
  try {
    const { data } = await api.get<SubdomainAvailability>(
      '/tenants/subdomain-availability',
      { subdomain: value },
      { signal: controller.signal },
    )
    availability.value = data
  } catch {
    availability.value = null
  } finally {
    checking.value = false
  }
}, 400)

watch(
  () => state.subdomain,
  value => check(value.trim().toLowerCase()),
)

const hint = computed(() => {
  if (checking.value)
    return {
      icon: 'i-lucide-loader-circle',
      class: 'text-muted animate-spin',
      text: t('auth.signup.checking'),
    }
  if (!availability.value) return null
  return availability.value.available
    ? { icon: 'i-lucide-circle-check', class: 'text-success', text: t('auth.signup.available') }
    : {
        icon: 'i-lucide-circle-x',
        class: 'text-error',
        text: t(`auth.signup.unavailable.${availability.value.reason ?? 'taken'}`),
      }
})

async function onSubmit(event: FormSubmitEvent<typeof state>) {
  if (availability.value && !availability.value.available) return
  const url = await run(() => auth.completeSignup(event.data.company_name, event.data.subdomain))
  if (url) emit('done', url)
}
</script>

<template>
  <UForm :schema="schema" :state="state" class="flex flex-col gap-4" @submit="onSubmit">
    <UFormField :label="t('auth.fields.company')" name="company_name" required>
      <UInput v-model="state.company_name" autocomplete="organization" size="xl" class="w-full" autofocus />
    </UFormField>
    <UFormField
      :label="t('auth.fields.subdomain')"
      name="subdomain"
      required
      :help="t('auth.signup.subdomainHelp')"
    >
      <UFieldGroup class="w-full">
        <UInput
          v-model="state.subdomain"
          class="w-full"
          autocomplete="off"
          :aria-describedby="hint ? 'subdomain-status' : undefined"
          @input="touchedSubdomain = true"
        />
        <UBadge
          :label="`.${config.public.rootDomain}`"
          color="neutral"
          variant="outline"
          size="xl"
          class="font-mono"
        />
      </UFieldGroup>
      <p v-if="hint" id="subdomain-status" class="mt-2 flex items-center gap-1.5 text-xs" aria-live="polite">
        <UIcon :name="hint.icon" class="size-4" :class="hint.class" />
        <span :class="hint.class.replace('animate-spin', '')">{{ hint.text }}</span>
      </p>
    </UFormField>
    <UButton
      type="submit"
      :label="t('auth.signup.create')"
      color="neutral"
      size="xl"
      block
      :loading="busy"
      :disabled="checking || availability?.available === false"
    />
  </UForm>
</template>
