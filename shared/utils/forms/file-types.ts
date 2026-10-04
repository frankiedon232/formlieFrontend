/**
 * File types for upload fields, picked from a searchable list instead of typed by hand (owner:
 * people get `accept` wrong). Empty = any file. Whole families use MIME wildcards (`image/*`);
 * single types use extensions (`.pdf`). Anything missing can still be added as `.ext`.
 * Stored on the field as the HTML `accept` string, e.g. "image/*,.pdf,.docx".
 */
export const FILE_TYPE_GROUPS = {
  images: ['image/*', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.heic', '.heif', '.bmp', '.tif', '.tiff', '.svg', '.ico', '.raw', '.cr2', '.nef', '.arw', '.dng', '.psd', '.ai', '.eps', '.xcf', '.jxl'],
  documents: ['.pdf', '.doc', '.docx', '.odt', '.rtf', '.txt', '.md', '.pages', '.tex', '.wpd', '.xps', '.oxps', '.djvu'],
  spreadsheets: ['.xls', '.xlsx', '.xlsm', '.ods', '.csv', '.tsv', '.numbers'],
  presentations: ['.ppt', '.pptx', '.odp', '.key'],
  audio: ['audio/*', '.mp3', '.wav', '.m4a', '.aac', '.ogg', '.oga', '.opus', '.flac', '.aiff', '.wma', '.amr', '.mid', '.midi'],
  video: ['video/*', '.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.flv', '.m4v', '.3gp', '.mpeg', '.mpg', '.ogv', '.mts'],
  archives: ['.zip', '.rar', '.7z', '.tar', '.gz', '.tgz', '.bz2', '.xz', '.zst', '.iso', '.dmg', '.cab'],
  ebooks: ['.epub', '.mobi', '.azw', '.azw3', '.fb2', '.cbz', '.cbr'],
  data: ['.json', '.xml', '.yaml', '.yml', '.toml', '.sql', '.sqlite', '.db', '.parquet', '.avro', '.ndjson', '.geojson', '.kml', '.kmz', '.gpx', '.shp', '.ics', '.vcf', '.eml', '.msg', '.mbox'],
  code: ['.html', '.htm', '.css', '.js', '.mjs', '.ts', '.jsx', '.tsx', '.vue', '.py', '.rb', '.php', '.java', '.kt', '.swift', '.go', '.rs', '.c', '.h', '.cpp', '.cs', '.sh', '.ps1', '.bat', '.ipynb', '.r', '.m', '.scala', '.dart', '.lua', '.pl'],
  design: ['.fig', '.sketch', '.xd', '.indd', '.afdesign', '.afphoto', '.cdr', '.dwg', '.dxf', '.step', '.stp', '.stl', '.obj', '.fbx', '.gltf', '.glb', '.blend', '.3ds', '.skp', '.ifc', '.rvt'],
  fonts: ['.ttf', '.otf', '.woff', '.woff2', '.eot'],
  security: ['.pem', '.crt', '.cer', '.p12', '.pfx', '.asc', '.gpg', '.sig', '.p7s'],
  apps: ['.apk', '.aab', '.ipa', '.exe', '.msi', '.deb', '.rpm', '.appimage', '.jar'],
} as const
export type FileTypeGroup = keyof typeof FILE_TYPE_GROUPS

export const FILE_GROUP_ICONS: Record<FileTypeGroup, string> = {
  images: 'i-lucide-image', documents: 'i-lucide-file-text', spreadsheets: 'i-lucide-sheet',
  presentations: 'i-lucide-presentation', audio: 'i-lucide-file-audio', video: 'i-lucide-file-video',
  archives: 'i-lucide-file-archive', ebooks: 'i-lucide-book-open', data: 'i-lucide-database',
  code: 'i-lucide-file-code', design: 'i-lucide-pen-tool', fonts: 'i-lucide-type',
  security: 'i-lucide-key-round', apps: 'i-lucide-package',
}

/** A typed extension → `.ext` (lower-case), or null if it isn't one. */
export function normaliseFileType(input: string): string | null {
  const value = input.trim().toLowerCase()
  if (/^[a-z0-9-]+\/(\*|[a-z0-9.+-]+)$/.test(value)) return value
  const ext = value.replace(/^\*?\./, '')
  return /^[a-z0-9][a-z0-9+_-]{0,15}$/.test(ext) ? `.${ext}` : null
}

export const parseAccept = (accept: string | undefined | null) =>
  String(accept ?? '')
    .split(',')
    .map(item => normaliseFileType(item))
    .filter((item): item is string => !!item)

/**
 * What an Image upload question can take: real pictures only (the server checks the bytes the same
 * way). Documents such as PDF belong in a File upload question (owner, 2026-10-04).
 */
export const PICTURE_TYPES = ['image/*', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.heic', '.heif', '.bmp', '.tif', '.tiff'] as const
const PICTURES = new Set<string>(PICTURE_TYPES)
/** Types in an `accept` list that an image question can't take. */
export const nonPictureTypes = (accept: string | undefined | null) => parseAccept(accept).filter(type => !PICTURES.has(type) && !(type.startsWith('image/') && type !== 'image/svg+xml'))
/** An image question's `accept`, pictures only ("image/*" when nothing is left). */
export function pictureAccept(accept: string | undefined | null): string {
  const kept = parseAccept(accept).filter(type => !nonPictureTypes(type).length)
  return kept.length ? kept.join(',') : 'image/*'
}

/** Does a file match an `accept` list? (Server checks again on upload.) */
export function acceptsFile(accept: string | undefined | null, file: { name: string; type: string }) {
  const types = parseAccept(accept)
  if (!types.length) return true
  const name = file.name.toLowerCase()
  const mime = file.type.toLowerCase()
  return types.some(type =>
    type.startsWith('.') ? name.endsWith(type) : type.endsWith('/*') ? mime.startsWith(type.slice(0, -1)) : mime === type,
  )
}
