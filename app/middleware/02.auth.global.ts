/**
 * Access control (runs after the tenant middleware). Pages are signed-in only unless they say
 * `definePageMeta({ auth: 'guest' })` (login, signup …) or `auth: false` (public).
 * A reload restores the session through the refresh cookie before deciding.
 */
export default defineNuxtRouteMiddleware(async to => {
  if (import.meta.server || to.meta.auth === false) return
  const tenant = useTenant()
  if (tenant.isManage.value) return // manage.* has no signed-in area

  const session = useSession()
  await useAuth().restore()

  if (to.meta.auth === 'guest') {
    if (session.isAuthenticated.value)
      return navigateTo(typeof to.query.redirect === 'string' ? to.query.redirect : '/dashboard')
    return
  }
  if (!session.isAuthenticated.value) {
    return navigateTo({ path: '/auth/login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} })
  }
  // Roles & access (F22): a page the role doesn't open shows "No access" instead
  const needed = pagePermission(to.path)
  if (needed && !useCan().can(needed)) return navigateTo({ path: '/no-access', query: { from: to.path } })
})
