import type { TenantPublicProfile } from '#shared/types/auth'
import type { HostContext } from '#shared/utils/tenant/host'

export type TenantStatus = 'idle' | 'ready' | 'not-found' | 'suspended' | 'unreachable'

const DEV_TENANT_KEY = 'formalie:dev-tenant'
const LAST_WORKSPACE_COOKIE = 'formalie_ws'

let pending: Promise<void> | null = null

/**
 * Which workspace this host is (docs/01-ARCHITECTURE.md → Subdomain flow), resolved once per
 * page load with the shared `resolveHostContext()`, plus the workspace's public profile
 * (branding, enabled sign-in methods). Dev only: `?tenant=acme` on localhost / an IP opens a
 * tenant without a subdomain (remembered for the tab).
 */
export function useTenant() {
  const config = useRuntimeConfig()
  const context = useState<HostContext | null>('tenant:context', () => null)
  const profile = useState<TenantPublicProfile | null>('tenant:profile', () => null)
  const status = useState<TenantStatus>('tenant:status', () => 'idle')
  const devTenant = useState<string | null>('tenant:dev', () => null)

  const lastWorkspace = useCookie<{ name: string; subdomain: string } | null>(LAST_WORKSPACE_COOKIE, {
    // Shared across subdomains so manage.* can offer "Continue to …"; not sensitive.
    domain:
      import.meta.client && location.hostname.endsWith(config.public.rootDomain)
        ? `.${config.public.rootDomain}`
        : undefined,
    maxAge: 60 * 60 * 24 * 365,
    sameSite: 'lax',
    secure: true,
    default: () => null,
  })

  function readDevOverride(): string | null {
    if (!import.meta.dev || import.meta.server) return null
    const fromQuery = new URLSearchParams(location.search).get('tenant')
    try {
      if (fromQuery !== null) {
        if (fromQuery) sessionStorage.setItem(DEV_TENANT_KEY, fromQuery)
        else sessionStorage.removeItem(DEV_TENANT_KEY)
      }
      return fromQuery || sessionStorage.getItem(DEV_TENANT_KEY)
    } catch {
      return fromQuery || null
    }
  }

  async function load() {
    devTenant.value = readDevOverride()
    context.value = resolveHostContext(location.host, {
      rootDomain: config.public.rootDomain,
      manageSubdomain: config.public.manageSubdomain,
      tenantOverride: devTenant.value,
    })
    if (context.value.kind === 'invalid') {
      status.value = 'not-found'
      return
    }
    try {
      profile.value = (await useApi().get<TenantPublicProfile>('/tenants/public')).data
      status.value = profile.value.status === 'suspended' ? 'suspended' : 'ready'
    } catch (error) {
      const code = isApiError(error) ? error.code : ''
      status.value =
        code === 'FRM-TEN-1001' ? 'not-found' : code === 'FRM-TEN-1002' ? 'suspended' : 'unreachable'
    }
  }

  /** Resolve once; later calls reuse the result. */
  function ensure(): Promise<void> {
    if (status.value !== 'idle' && status.value !== 'unreachable') return Promise.resolve()
    pending ??= load().finally(() => {
      pending = null
    })
    return pending
  }

  const isManage = computed(() => profile.value?.mode === 'manage')

  function hostUrl(subdomain: string, path = '/') {
    const port = location.port ? `:${location.port}` : ''
    return `${location.protocol}//${subdomain}.${config.public.rootDomain}${port}${path}`
  }

  const manageUrl = (path = '/') => hostUrl(config.public.manageSubdomain, path)

  function rememberWorkspace() {
    if (profile.value?.mode === 'tenant')
      lastWorkspace.value = { name: profile.value.name, subdomain: profile.value.subdomain }
  }

  return {
    context: readonly(context),
    profile: readonly(profile),
    status: readonly(status),
    devTenant: readonly(devTenant),
    isManage,
    lastWorkspace,
    ensure,
    hostUrl,
    manageUrl,
    rememberWorkspace,
  }
}
