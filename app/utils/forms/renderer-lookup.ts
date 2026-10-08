import type { InjectionKey } from 'vue'
import type { RendererLookup } from '#shared/types/public'

/**
 * Long lists on the public page (F15 M3, provided by FormsRendererForm from the page's respondent): a
 * choice field whose options stayed on the server (`options_remote`) asks for matches as people type.
 * The builder and previews have every option and no lookup.
 */
export const RENDERER_LOOKUP: InjectionKey<RendererLookup | null> = Symbol('formalie:renderer-lookup')
