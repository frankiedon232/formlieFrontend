/** Community & Other templates (F9 milestone 4). Fees and gifts are worked out; collecting payment comes with the payment field. */
import { opts, page, q, row, rule, scored, type TemplateDef } from '../kit'

export const COMMUNITY_TEMPLATES: TemplateDef[] = [
  {
    key: 'membership_application',
    category: 'community',
    icon: 'i-lucide-id-card',
    minutes: 5,
    name: 'Membership Application',
    description: 'Join a club or association: member details, membership level, extras and the yearly fee.',
    tags: ['membership', 'club', 'association'],
    pages: [
      page('About you', [
        q('full_name', 'Full name', { required: true }),
        row(q('email', 'Email', { required: true }), q('phone', 'Phone')),
        row(q('date', 'Date of birth'), q('country', 'Country')),
        q('address', 'Address'),
      ]),
      page('Membership', [
        q('radio', 'Membership level', {
          key: 'level',
          required: true,
          options: scored(['Standard: 60.00 a year', 60], ['Concession (student / senior): 30.00 a year', 30], ['Family: 100.00 a year', 100], ['Supporter: 150.00 a year', 150]),
        }),
        q('checkbox', 'Extras', { key: 'extras', options: scored(['Printed newsletter: 10.00', 10], ['Locker or storage: 25.00', 25]) }),
        q('number', 'Additional family members', { key: 'family_members', default: 0, validation: { min: 0, max: 8 } }),
        q('calculated', 'Yearly fee', { key: 'fee', formula: 'sum({level}, {extras})' }),
        q('multi_select', 'What are you interested in?', { options: opts('Events', 'Volunteering', 'Committees', 'Training', 'Newsletter') }),
        q('consent', 'Rules', { required: true, props: { text: 'I agree to follow the rules of the organisation.' } }),
        q('consent', 'Updates', { props: { text: 'Send me news and event invitations by email.' } }),
      ]),
    ],
    logic: [rule([['level', 'eq', 'family_100_00_a_year']], [['show', 'family_members']])],
  },
  {
    key: 'donation_form',
    category: 'community',
    icon: 'i-lucide-heart-handshake',
    minutes: 3,
    name: 'Donation Form',
    description: 'A gift amount (or your own), monthly or once, with an option to cover the processing fee.',
    tags: ['donation', 'fundraising', 'charity'],
    design: { colors: { primary: '#db2777' }, header: { band_bg: '#be185d', band_to: '#f97316' } },
    pages: [
      page('Your gift', [
        q('radio', 'Frequency', { required: true, options: opts('One time', 'Monthly') }),
        q('radio', 'Amount', { key: 'preset', required: true, options: scored(['10.00', 10], ['25.00', 25], ['50.00', 50], ['100.00', 100], ['Other amount', 0]) }),
        q('currency', 'Your amount', { key: 'other_amount', validation: { min: 1 } }),
        q('toggle', 'Add 3% to cover processing costs', { key: 'cover_fees', default: true }),
        row(
          q('calculated', 'Gift', { key: 'gift', formula: 'if({preset} > 0, {preset}, {other_amount})' }),
          q('calculated', 'Total', { key: 'total', formula: 'round({gift} * (1 + {cover_fees} * 0.03), 2)' }),
        ),
        q('dropdown', 'Where should it go?', { options: opts('Where it is needed most', 'Programmes', 'Emergency fund', 'Equipment') }),
        q('short_text', 'In honour or memory of (optional)'),
      ]),
      page('Your details', [
        q('full_name', 'Full name', { required: true }),
        row(q('email', 'Email', { required: true }), q('country', 'Country')),
        q('toggle', 'Keep my gift anonymous'),
        q('consent', 'Updates', { props: { text: 'Tell me how my gift is used.' } }),
      ]),
    ],
    logic: [rule([['preset', 'eq', 'other_amount']], [['show', 'other_amount'], ['require', 'other_amount']])],
    thankYou: { title: 'Thank you for your gift', message: 'A receipt is on its way to your email.' },
  },
  {
    key: 'petition',
    category: 'community',
    icon: 'i-lucide-megaphone',
    minutes: 2,
    name: 'Petition',
    description: 'State the cause, collect names and locations, and let people say why it matters to them.',
    tags: ['petition', 'campaign', 'signature'],
    pages: [
      page('Sign the petition', [
        q('paragraph', 'What we are asking for', {
          props: { html: '<p>Explain the change you want, who can make it happen and why it matters. Keep it short and specific.</p>' },
        }),
        q('full_name', 'Full name', { required: true }),
        row(q('email', 'Email', { required: true }), q('country', 'Country', { required: true })),
        q('short_text', 'Town or city'),
        q('long_text', 'Why does this matter to you? (optional)', { validation: { max_length: 500 } }),
        q('toggle', 'Show my name publicly as a supporter'),
        q('consent', 'Updates', { props: { text: 'Keep me updated about this campaign.' } }),
      ]),
    ],
    thankYou: { title: 'Thank you for signing', message: 'Share the petition to help it reach more people.' },
  },
  {
    key: 'poll_ballot',
    category: 'community',
    icon: 'i-lucide-vote',
    minutes: 2,
    name: 'Poll / Voting Ballot',
    description: 'One vote per person on a question and a ranked choice, with an optional comment.',
    tags: ['poll', 'vote', 'ballot', 'election'],
    pages: [
      page('Your vote', [
        q('paragraph', 'How to vote', { props: { html: '<p>Choose one option for the question, then rank the candidates from first to last choice.</p>' } }),
        q('radio', 'Should we adopt the proposal?', { required: true, options: opts('Yes', 'No', 'Abstain') }),
        q('ranking', 'Rank the candidates', { required: true, options: opts('Candidate A', 'Candidate B', 'Candidate C', 'Candidate D') }),
        q('short_text', 'Member or voter number', { required: true }),
        q('long_text', 'Comment (optional)'),
        q('consent', 'Declaration', { required: true, props: { text: 'I am entitled to vote and vote only once.' } }),
      ]),
    ],
    thankYou: { title: 'Your vote is in', message: 'Results are shared when voting closes.' },
  },
]
