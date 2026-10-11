"""Records the frontend's export report (B8) into tests/vectors/report_rules.json: the exact bytes of the PDF the mock
makes for several exports (data/responseReport.ts over core/pdfDoc.ts), the workspace colour for files
(shared/utils/settings/appearance-ink.ts) and which ink reads on it (readableOn), and the CSV cell rule.

    fmly\\Scripts\\python.exe scripts\\dump_report_rules.py [path\\to\\formalieFrontend]

tests/parity/test_report_rules.py holds the port (app/modules/responses/report.py, exports.py) to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "report_rules.json"

ENTRY = r"""
import { responseReport } from '__SHARED__/../server/mock/data/responseReport.ts'
import { appearanceInk } from '__SHARED__/utils/settings/appearance-ink.ts'
import { readableOn } from '__SHARED__/utils/forms/theme.ts'
// csvCell, as in server/mock/routes/responseExports.ts (that file needs the server to import)
const csvCell = value => {
  const text = value == null ? '' : String(value)
  const safe = /^[=+\-@\t\r]/.test(text) ? `'${text}` : text
  return /[",\n\r]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe
}

const answer = (q, a) => ({ question: q, answer: a })
const long = 'This is a long answer that keeps going so that it has to wrap over several lines in the answer column of the card. '.repeat(4)
const many = Array.from({ length: 23 }, (_, i) => ({
  number: 100 - i, name: i % 4 ? `Person ${i}` : '', email: i % 3 ? `p${i}@example.org` : '', submitted: `2026-10-0${1 + (i % 9)} 10:0${i % 10} UTC`,
  status: ['new', 'reviewed', 'approved', 'rejected'][i % 4], channel: ['link', 'embed', 'api', 'other'][i % 4], tags: i % 5 ? [] : ['vip', 'follow-up'],
  answers: [answer('Full name', `Person ${i}`), answer('A rather long question that wraps onto a second line in the question column', i % 2 ? long : ''),
    answer('Café (main) \\ branch', 'Crème brûlée – “quoted” … € 12'), answer('Non-Latin', 'Привет 世界 😀'), answer('Unbroken', 'x'.repeat(140))],
}))
const inputs = [
  { org: 'Remedy Legal', form: 'Client intake', brand: '#18181b', exportedBy: 'Olu Ade', exportedAt: new Date('2026-09-03T08:05:00Z'), scope: 'All responses',
    counts: { new: 6, reviewed: 6, approved: 6, rejected: 5 }, responses: many },
  { org: 'émile & co', form: 'A very long form title that will certainly not fit on one line of the cover band at twenty-two points', brand: '#fde047',
    exportedBy: 'Zoë', exportedAt: new Date('2026-12-31T23:59:00Z'), scope: 'Selected responses', counts: { new: 1234, reviewed: 0, approved: 0, rejected: 0 }, responses: many.slice(0, 1) },
  { org: '', form: 'Empty', brand: '#2563eb', exportedBy: 'X', exportedAt: new Date('2026-01-15T00:00:00Z'), scope: 'Matching the filters', counts: { new: 0, reviewed: 0, approved: 0, rejected: 0 }, responses: [] },
]
const reports = inputs.map(input => ({ input: { ...input, exportedAt: input.exportedAt.toISOString() }, pdf: Buffer.from(responseReport(input)).toString('base64') }))
const inks = [null, { primary: 'mono' }, { primary: 'brand' }, { primary: 'teal' }, { primary: 'nope' }].flatMap(appearance =>
  [null, '#0055FF', 'red'].map(brand => ({ appearance, brand, ink: appearanceInk(appearance, brand) })))
const readable = ['#18181b', '#ffffff', '#fde047', '#2563eb', '#777777', '#767676', '#0055ff'].map(color => ({ color, on: readableOn(color) }))
const cells = [null, undefined, '', 'plain', '=SUM(A1)', '+1', '-2', '@x', '\tx', 'a,b', 'say "hi"', 'line\nbreak', 3, 0, true, 'é']
  .map(value => ({ value: value === undefined ? '__undefined__' : value, cell: csvCell(value) }))
process.stdout.write(JSON.stringify({ about: 'Recorded from the frontend by scripts/dump_report_rules.py. Do not edit.', reports, inks, readable, cells }))
"""


def main() -> None:
    result = run_in_node(ENTRY, {})
    OUT.write_text(json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(result['reports'])} reports")


if __name__ == "__main__":
    main()
