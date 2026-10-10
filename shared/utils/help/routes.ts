/** Help content is tied to pages by address patterns (F25): `/forms/:id/build` matches any form's builder. */
export const routeMatches = (pattern: string, path: string) => new RegExp(`^${pattern.replace(/:[a-z]+/g, '[^/]+')}/?$`).test(path)
