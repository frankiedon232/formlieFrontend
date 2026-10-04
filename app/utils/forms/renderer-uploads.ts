import type { InjectionKey, Ref } from 'vue'
import type { RendererUpload } from '#shared/types/public'

/**
 * What a form gives its file questions (provided by FormsRendererForm): the uploader (public page
 * only, the preview keeps files in the browser) and a count of uploads still running, so Next and
 * Submit wait for them.
 */
export interface RendererUploads {
  upload: RendererUpload | null
  pending: Ref<number>
}
export const RENDERER_UPLOADS: InjectionKey<RendererUploads> = Symbol('formalie:renderer-uploads')
