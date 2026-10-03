/**
 * Sales templates (F9 milestone 4) — business-to-business versions; Business & customer has the
 * consumer-facing quote, order and newsletter forms.
 */
import { opts, page, q, row, rule, scored, type TemplateDef } from '../kit'

const companySize = () => opts('1–10', '11–50', '51–200', '201–1,000', 'More than 1,000')

export const SALES_TEMPLATES: TemplateDef[] = [
  {
    key: 'sales_lead_capture',
    category: 'sales',
    icon: 'i-lucide-magnet',
    minutes: 2,
    name: 'Lead Capture',
    description: 'Name, company, size and interest — short enough for a landing page, with the source tracked.',
    tags: ['lead', 'b2b', 'landing page'],
    pages: [
      page('Get in touch', [
        row(q('full_name', 'Name', { required: true }), q('email', 'Work email', { required: true })),
        row(q('short_text', 'Company', { required: true }), q('dropdown', 'Company size', { options: companySize() })),
        q('multi_select', 'Interested in', { required: true, options: opts('Product A', 'Product B', 'Services', 'Partnership') }),
        q('phone', 'Phone (optional)'),
        q('hidden', 'Source', { key: 'utm_source' }),
        q('hidden', 'Campaign', { key: 'utm_campaign' }),
        q('consent', 'Contact', { required: true, props: { text: 'I agree to be contacted about my enquiry.' } }),
      ]),
    ],
  },
  {
    key: 'sales_quote_request',
    category: 'sales',
    icon: 'i-lucide-receipt-text',
    minutes: 4,
    name: 'Quote Request',
    description: 'Pick a plan, seats and services; an indicative yearly total is worked out for the sales team.',
    tags: ['quote', 'pricing', 'b2b'],
    pages: [
      page('Your requirements', [
        row(q('short_text', 'Company', { required: true }), q('email', 'Work email', { required: true })),
        q('radio', 'Plan', { key: 'plan', required: true, options: scored(['Team — 8.00 per seat / month', 8], ['Business — 15.00 per seat / month', 15], ['Enterprise — 25.00 per seat / month', 25]) }),
        q('number', 'Seats', { key: 'seats', required: true, default: 10, validation: { min: 1 } }),
        q('checkbox', 'Services', { key: 'services', options: scored(['Onboarding — 500.00', 500], ['Data migration — 1,200.00', 1200], ['Training day — 800.00', 800]) }),
        row(
          q('calculated', 'Subscription per year', { key: 'subscription', formula: '{plan} * {seats} * 12' }),
          q('calculated', 'Indicative total (first year)', { key: 'quote_total', formula: '{subscription} + sum({services})' }),
        ),
        q('date', 'When do you need it?'),
        q('long_text', 'Anything else we should know?'),
      ]),
    ],
    thankYou: { title: 'Quote requested', message: 'We will send a formal quote within one working day.' },
  },
  {
    key: 'sales_qualification',
    category: 'sales',
    icon: 'i-lucide-target',
    minutes: 4,
    name: 'Sales Qualification',
    description: 'Budget, authority, need and timing scored for the team, with a hot / warm / cold result.',
    tags: ['qualification', 'bant', 'pipeline'],
    pages: [
      page('Qualification', [
        row(q('short_text', 'Company', { required: true }), q('short_text', 'Contact', { required: true })),
        q('radio', 'Budget', { key: 'budget', required: true, options: scored(['Approved', 3], ['Being planned', 2], ['Not yet', 0]) }),
        q('radio', 'Authority', { key: 'authority', required: true, options: scored(['Decision maker', 3], ['Influences the decision', 2], ['Researching only', 0]) }),
        q('radio', 'Need', { key: 'need', required: true, options: scored(['Urgent problem', 3], ['Clear need', 2], ['Exploring', 1]) }),
        q('radio', 'Timing', { key: 'timing', required: true, options: scored(['Within a month', 3], ['This quarter', 2], ['Later this year', 1], ['No timeline', 0]) }),
        row(
          q('calculated', 'Qualification score (out of 12)', { key: 'qual_score', formula: 'sum({budget}, {authority}, {need}, {timing})', props: { internal: true } }),
          q('calculated', 'Lead temperature', { key: 'temperature', formula: 'if({qual_score} >= 9, "Hot", if({qual_score} >= 5, "Warm", "Cold"))', props: { internal: true } }),
        ),
        q('long_text', 'Notes'),
      ]),
    ],
  },
  {
    key: 'demo_request',
    category: 'sales',
    icon: 'i-lucide-presentation',
    minutes: 2,
    name: 'Product Demo Request',
    description: 'Book a live demo: who is attending, what to focus on, time zone and preferred times.',
    tags: ['demo', 'trial', 'b2b'],
    pages: [
      page('Book a demo', [
        row(q('full_name', 'Name', { required: true }), q('email', 'Work email', { required: true })),
        row(q('short_text', 'Company', { required: true }), q('short_text', 'Job title')),
        q('multi_select', 'What should we focus on?', { options: opts('Getting started', 'Integrations', 'Security and permissions', 'Reporting', 'Pricing') }),
        row(q('timezone', 'Time zone', { required: true }), q('number', 'People attending', { default: 1, validation: { min: 1, max: 50 } })),
        row(q('datetime', 'Preferred time', { required: true }), q('datetime', 'Second choice')),
        q('radio', 'Format', { options: opts('Video call', 'In person') }),
      ]),
    ],
    thankYou: { title: 'Demo requested', message: 'We will confirm a time by email shortly.' },
  },
  {
    key: 'customer_discovery',
    category: 'sales',
    icon: 'i-lucide-search-check',
    minutes: 6,
    name: 'Customer Discovery',
    description: 'Understand goals, current tools, pain points and what success looks like before proposing.',
    tags: ['discovery', 'needs', 'research'],
    pages: [
      page('Your business', [
        row(q('short_text', 'Company', { required: true }), q('dropdown', 'Company size', { options: companySize() })),
        q('short_text', 'Industry'),
        q('long_text', 'What are you trying to achieve this year?', { required: true }),
        q('short_text', 'Which tools do you use today?'),
      ]),
      page('Challenges', [
        q('ranking', 'Rank your biggest challenges', { options: opts('Too much manual work', 'Poor data quality', 'Slow approvals', 'Lack of reporting', 'High costs') }),
        q('scale', 'How painful is this today?', { props: { min: 1, max: 10, min_label: 'Minor', max_label: 'Critical' } }),
        q('long_text', 'What would success look like in six months?'),
        q('currency', 'Budget range (optional)'),
      ]),
    ],
  },
  {
    key: 'proposal_request',
    category: 'sales',
    icon: 'i-lucide-file-pen-line',
    minutes: 5,
    name: 'Proposal Request',
    description: 'Scope, deliverables, budget, deadline and decision process for a tailored proposal.',
    tags: ['proposal', 'rfp', 'scope'],
    pages: [
      page('Proposal request', [
        row(q('short_text', 'Organisation', { required: true }), q('full_name', 'Contact', { required: true })),
        q('email', 'Email', { required: true }),
        q('long_text', 'Project scope', { required: true, validation: { min_length: 50 } }),
        q('multi_select', 'Deliverables', { options: opts('Strategy', 'Design', 'Implementation', 'Training', 'Ongoing support') }),
        row(q('currency', 'Budget'), q('date', 'Proposal needed by', { required: true })),
        q('radio', 'Is this a formal tender?', { key: 'tender', options: opts('No', 'Yes') }),
        q('file_upload', 'Tender documents', { key: 'tender_docs', props: { accept: '.pdf,.docx,.xlsx', max_files: 5 } }),
        q('long_text', 'Who decides, and how?'),
      ]),
    ],
    logic: [rule([['tender', 'eq', 'yes']], [['show', 'tender_docs'], ['require', 'tender_docs']])],
  },
  {
    key: 'order_request',
    category: 'sales',
    icon: 'i-lucide-package-check',
    minutes: 5,
    name: 'Order Request',
    description: 'Trade customers order by product code and quantity, with a volume discount and order total.',
    tags: ['order', 'wholesale', 'b2b'],
    pages: [
      page('Order', [
        row(q('short_text', 'Company', { required: true }), q('short_text', 'Customer account number'), q('short_text', 'Your PO number')),
        ...[1, 2, 3, 4].map(n =>
          row(
            q('short_text', 'Product code', { key: `code_${n}`, required: n === 1, width: 4 }),
            q('number', 'Qty', { key: `qty_${n}`, required: n === 1, width: 3, validation: { min: 0 } }),
            q('currency', 'Unit price', { key: `price_${n}`, required: n === 1, width: 5 }),
          ),
        ),
        row(
          q('calculated', 'Subtotal', { key: 'subtotal', formula: 'round(sum({qty_1} * {price_1}, {qty_2} * {price_2}, {qty_3} * {price_3}, {qty_4} * {price_4}), 2)' }),
          q('calculated', 'Volume discount', { key: 'discount', formula: 'round(if({subtotal} >= 5000, {subtotal} * 0.05, 0), 2)', help: '5% off orders of 5,000 or more.' }),
          q('calculated', 'Order total', { key: 'order_total', formula: '{subtotal} - {discount}' }),
        ),
        q('address', 'Delivery address', { required: true }),
        q('date', 'Requested delivery date'),
      ]),
    ],
  },
  {
    key: 'sales_follow_up',
    category: 'sales',
    icon: 'i-lucide-calendar-sync',
    minutes: 2,
    name: 'Sales Follow-up',
    description: 'Log a call or meeting: outcome, deal stage, next step and its date — quick enough for phones.',
    tags: ['follow-up', 'crm', 'activity'],
    pages: [
      page('Follow-up', [
        row(q('short_text', 'Account', { required: true }), q('short_text', 'Contact')),
        row(q('radio', 'Activity', { options: opts('Call', 'Meeting', 'Email', 'Demo') }), q('date', 'Date', { required: true })),
        q('dropdown', 'Deal stage', { required: true, options: opts('New', 'Qualified', 'Proposal sent', 'Negotiation', 'Won', 'Lost') }),
        q('currency', 'Deal value'),
        q('long_text', 'Summary', { required: true }),
        row(q('short_text', 'Next step'), q('date', 'Next step date')),
      ]),
    ],
  },
]
