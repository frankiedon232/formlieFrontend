import type { UploadTicket } from '#shared/types/onboarding'

/**
 * PUT a file straight to storage through a pre-signed ticket (SECURITY-PROTOCOL.md) with real
 * progress — XHR, because fetch has no upload progress. `onRequest` gets the request so callers
 * can cancel it.
 */
export function putFile(
  ticket: UploadTicket,
  file: File,
  options: { onProgress?: (percent: number) => void; onRequest?: (request: XMLHttpRequest) => void } = {},
): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    options.onRequest?.(request)
    request.open(ticket.method, ticket.upload_url)
    for (const [name, value] of Object.entries(ticket.headers)) request.setRequestHeader(name, value)
    request.upload.onprogress = event => {
      if (event.lengthComputable) options.onProgress?.(Math.round((event.loaded / event.total) * 100))
    }
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) return resolve()
      let message = 'The file was refused.'
      try {
        message = (JSON.parse(request.responseText) as { error?: string }).error ?? message
      } catch {
        // Storage answered without a message.
      }
      reject(new ApiError('FRM-GEN-1002', message, request.status))
    }
    request.onerror = () => reject(new ApiError(NETWORK_ERROR, "Can't reach the server."))
    request.onabort = () => reject(new ApiError(ABORTED_ERROR, 'Upload cancelled.'))
    request.send(file)
  })
}
