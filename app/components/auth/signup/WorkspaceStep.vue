<!--
  Signup step 3: company name + subdomain with live availability (reserved names blocked)
  → workspace created → hand-off URL on the new subdomain. When the verified email already has workspaces,
  they are listed first with a way in, so nobody makes a second one by mistake (owner, 2026-10-12).
-->
<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import type { SubdomainAvailability, WorkspaceLink } from '#shared/types/auth'

const emit = defineEmits<{ done: [url: string] }>()
const { t } = useI18n()
const config = useRuntimeConfig()
const api = useApi()
const auth = useAuth()
const { busy, run } = useBusy()

const schema = computed(() => workspaceSchema(t))

// The workspaces this email already has (most people: none). Not finding them never blocks sign-up.
const existing = ref<WorkspaceLink[]>([])
const loadingExisting = ref(true)
onMounted(async () => {
  try {
    existing.value = await auth.signupWorkspaces()
  } catch {
    existing.value = []
  } finally {
    loadingExisting.value = false
  }
})
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
  <div>
    <USkeleton v-if="loadingExisting" class="mb-4 h-16 w-full rounded-lg" />
    <div
      v-else-if="existing.length"
      class="mb-5 flex flex-col gap-3 rounded-lg border border-default bg-elevated/40 p-3"
      aria-live="polite"
    >
      <p class="flex items-start gap-2 text-sm text-default">
        <UIcon name="i-lucide-info" class="mt-0.5 size-4 shrink-0 text-muted" />
        {{ t('auth.signup.existingTitle', existing.length) }}
      </p>
      <ul class="flex flex-col gap-2">
        <li
          v-for="item in existing"
          :key="item.subdomain"
          class="flex items-center gap-3 rounded-md bg-default px-3 py-2 ring-1 ring-default"
        >
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="truncate text-sm font-medium text-highlighted">{{ item.name }}</span>
            <span class="truncate font-mono text-xs text-muted"
              >{{ item.subdomain }}.{{ config.public.rootDomain }}</span
            >
          </span>
          <UButton
            :label="t('auth.signup.existingOpen')"
            :to="item.url"
            external
            color="neutral"
            variant="outline"
            size="sm"
            trailing-icon="i-lucide-arrow-right"
            :ui="{ trailingIcon: 'rtl:rotate-180' }"
          />
        </li>
      </ul>
      <p class="text-xs text-muted">{{ t('auth.signup.existingOr') }}</p>
    </div>
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
        <p
          v-if="hint"
          id="subdomain-status"
          class="mt-2 flex items-center gap-1.5 text-xs"
          aria-live="polite"
        >
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
  </div>
</template>
