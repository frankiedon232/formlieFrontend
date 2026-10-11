"""Records the frontend's answer rules (B8) into tests/vectors/responses_rules.json: which answers a team member may
edit, the values a question can be filtered on, answer filters, answers as plain text for titles and export files,
and keeping only the answered options of large lists (shared/utils/forms/answer-edit.ts, answer-filter.ts,
answer-text.ts and the mock's keepAnswered).

    fmly\\Scripts\\python.exe scripts\\dump_responses_rules.py [path\\to\\formalieFrontend]

tests/parity/test_responses_rules.py holds the port (app/modules/responses/answers.py) to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "responses_rules.json"

ENTRY = r"""
import { canEditAnswer } from '__SHARED__/utils/forms/answer-edit.ts'
import { filterValues, answerValues, answerMatches, isEmptyAnswer } from '__SHARED__/utils/forms/answer-filter.ts'
import { answerText } from '__SHARED__/utils/forms/answer-text.ts'
import { FIELD_TYPE_KEYS } from '__SHARED__/utils/forms/fields.ts'

const opts = [{ value: 'a', label: 'Apple' }, { value: 'b', label: 'Banana' }, { value: '3', label: 'Three' }]
const fields = [
  ...FIELD_TYPE_KEYS.map(type => ({ type, options: opts })),
  { type: 'rating', props: {} }, { type: 'rating', props: { max: 10 } }, { type: 'rating', props: { max: 12 } }, { type: 'scale', props: { min: 0, max: 10 } },
  { type: 'scale', props: { min: '1', max: '7' } }, { type: 'scale', props: { min: 5, max: 1 } }, { type: 'scale', props: { min: 'x' } }, { type: 'dropdown', options: [] },
  { type: 'checkbox' }, undefined,
]
const values = [null, undefined, '', 'a', 'z', 3, 0, 2.5, true, false, 'true', ['a', 'b'], ['b', 'zz'], [], [3, null],
  { first: 'Ana', last: 'Silva', title: 'Dr' }, { line1: '1 Main', city: 'Leeds', postal_code: 'LS1', country: 'GB' }, { from: '2026-01-01', to: '2026-01-05' },
  { hours: '2', minutes: 5 }, { hours: 'x' }, { r1: 'a', r2: 'b' }, [{ id: 'f', name: 'cv.pdf', size: 1, type: 't' }, { name: '' }, 'loose.txt', null],
  '<p>Hello <b>you</b></p>  there', { a: '', b: null }, { a: 0 }, 'yes', 1e21, -0.5]
const words = { yes: 'Oui', no: 'Non', agreed: 'Accepté' }
const enc = v => (v === undefined ? '__undefined__' : v)
const text = fields.flatMap((field, f) => values.map((value, v) => ({ f, v, text: answerText(field, value), fr: answerText(field, value, words) })))
const filters = fields.map((field, f) => ({ f, values: field ? filterValues(field) : null, edit: field ? canEditAnswer(field) : null }))
const wanted = [[], ['a'], ['3', 'true'], ['b', 'zz']]
const matches = values.flatMap((value, v) => wanted.map((w, i) => ({ v, w: i, match: answerMatches(value, w) })))
const empties = values.map((value, v) => ({ v, empty: isEmptyAnswer(value), values: answerValues(value) }))

process.stdout.write(JSON.stringify({
  about: 'Recorded from the frontend by scripts/dump_responses_rules.py. Do not edit.',
  fields: fields.map(f => f ?? '__undefined__'), values: values.map(enc), wanted, words, text, filters, matches, empties,
}))
"""


def main() -> None:
    result = run_in_node(ENTRY, {})
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(result['text'])} answers as text")


if __name__ == "__main__":
    main()
