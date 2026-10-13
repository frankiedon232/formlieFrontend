// Copies the cropped, watermarked app screenshots (docs/screenshots/*.jpg) to public/screenshots/ as WebP, at their
// real size and crop (docs/DESIGN.md, docs/SECURITY.md). Needs ffmpeg with libwebp on the PATH.
// Run again whenever docs/screenshots changes: `pnpm screenshots`.
import { execFileSync } from 'node:child_process'
import { mkdirSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

const root = join(import.meta.dirname, '..')
const source = join(root, 'docs/screenshots')
const target = join(root, 'public/screenshots')
mkdirSync(target, { recursive: true })

const files = readdirSync(source).filter(file => file.endsWith('.jpg'))
for (const file of files) {
  const out = join(target, file.replace(/\.jpg$/, '.webp'))
  execFileSync('ffmpeg', [
    '-v',
    'error',
    '-y',
    '-i',
    join(source, file),
    '-c:v',
    'libwebp',
    '-quality',
    '85',
    out,
  ])
  console.log(`${file} → public/screenshots/${file.replace(/\.jpg$/, '.webp')}`)
}
console.log(`${files.length} screenshots converted.`)
