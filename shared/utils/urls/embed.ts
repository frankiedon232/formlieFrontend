/**
 * Embed code for a form (F10 M2): the `<iframe>` people paste into their own website.
 *   auto, the frame follows the form's height: the embed page posts `formalie:resize` messages
 *           (FormView) and a small script on the host page applies them (only messages from the
 *           form's own address, only to that frame).
 *   fixed, a fixed height in pixels; the form scrolls inside the frame.
 */
export interface EmbedOptions {
  url: string
  title: string
  /** 'auto' or a height in pixels (240–4000). */
  height: 'auto' | number
}

const escapeAttribute = (value: string) => value.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

export const clampEmbedHeight = (value: number) => Math.min(4000, Math.max(240, Math.round(Number.isFinite(value) ? value : 600)))

export function embedCode({ url, title, height }: EmbedOptions): string {
  const origin = new URL(url).origin
  const pixels = height === 'auto' ? 600 : clampEmbedHeight(height)
  const frame = `<iframe src="${escapeAttribute(url)}" title="${escapeAttribute(title)}" width="100%" height="${pixels}" style="border:0;width:100%;max-width:100%" loading="lazy"${height === 'auto' ? ' data-formalie-embed' : ''}></iframe>`
  if (height !== 'auto') return frame
  const script = `<script>window.addEventListener("message",function(e){var d=e.data;if(e.origin!=="${origin}"||!d||d.type!=="formalie:resize")return;document.querySelectorAll("iframe[data-formalie-embed]").forEach(function(f){if(f.contentWindow===e.source)f.style.height=Math.ceil(d.height)+"px"})});</script>`
  return `${frame}\n${script}`
}
