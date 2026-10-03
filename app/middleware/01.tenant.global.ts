/**
 * Host → workspace (runs first). Unknown / reserved / suspended → /workspace-not-found.
 * manage.* only serves pages marked `manage: true` (signup, find workspace, manage login);
 * workspace hosts never serve manage-only pages.
 */
export default defineNuxtRouteMiddleware(async to => {
  // Public form pages find their workspace from the form key / host themselves (F10).
  if (import.meta.server || to.meta.public) return
  const tenant = useTenant()
  await tenant.ensure()

  const notFoundPage = '/workspace-not-found'
  if (tenant.status.value === 'not-found' || tenant.status.value === 'suspended') {
    if (to.path === notFoundPage) return
    return navigateTo({
      path: notFoundPage,
      query: tenant.status.value === 'suspended' ? { reason: 'suspended' } : {},
    })
  }
  // API down: let the page render; its own calls show the error state.
  if (tenant.status.value !== 'ready') return

  const manageOnly = to.meta.manage === 'only'
  if (tenant.isManage.value) {
    if (!to.meta.manage && to.meta.auth !== false) return navigateTo('/auth/login')
  } else if (manageOnly) {
    return navigateTo('/auth/login')
  }
})
