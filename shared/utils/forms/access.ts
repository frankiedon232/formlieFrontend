import type { FormAccessLevel } from '#shared/types/forms'

/**
 * May this person change the form? Only "Can edit" (or no level sent, i.e. full access) opens the
 * editor, logic, design, sharing, versions, templates and lifecycle actions (decision 97).
 */
export const canEditForm = (form: { my_access?: FormAccessLevel | null } | null | undefined) =>
  !!form && (!form.my_access || form.my_access === 'edit')
