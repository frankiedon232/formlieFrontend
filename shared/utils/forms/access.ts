import type { FormAction, FormActions } from '#shared/types/forms'

/**
 * May the signed-in person take this action on the form (F22 R2: the role's scope, who made it, whom it
 * is shared with and its folder, worked out by the API and sent as `can`)? No answer means no.
 */
export const formCan = (form: { can?: FormActions | null } | null | undefined, action: FormAction) => !!form?.can?.[action]

/** May this person change the form's questions, logic and design (the editor)? */
export const canEditForm = (form: { can?: FormActions | null } | null | undefined) => formCan(form, 'edit')
