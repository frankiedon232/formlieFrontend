/** Finance & Legal templates (F9 milestone 3). Controls only, no compliance or certification claims. */
import { opts, page, q, row, rule, type TemplateDef } from '../kit'

export const FINANCE_LEGAL_TEMPLATES: TemplateDef[] = [
  {
    key: 'loan_application',
    category: 'finance_legal',
    icon: 'i-lucide-hand-coins',
    minutes: 10,
    name: 'Loan / Credit Application',
    description: 'Applicant, employment and finances, with a debt-to-income ratio and an estimated monthly payment.',
    tags: ['loan', 'credit', 'finance'],
    pages: [
      page('Applicant', [
        q('full_name', 'Full name', { required: true }),
        row(q('date', 'Date of birth', { required: true }), q('country', 'Country of residence', { required: true })),
        row(q('email', 'Email', { required: true }), q('phone', 'Phone', { required: true })),
        q('address', 'Home address', { required: true }),
        q('radio', 'Employment', { required: true, options: opts('Employed', 'Self-employed', 'Retired', 'Student', 'Not working') }),
        q('short_text', 'Employer or business name'),
      ]),
      page('Loan and finances', [
        row(
          q('currency', 'Amount requested', { key: 'amount', required: true, validation: { min: 100 } }),
          q('number', 'Term (months)', { key: 'months', required: true, default: 24, validation: { min: 3, max: 360 } }),
          q('percentage', 'Indicative interest rate (yearly)', { key: 'rate', default: 9 }),
        ),
        q('dropdown', 'Purpose', { options: opts('Home improvement', 'Vehicle', 'Education', 'Business', 'Debt consolidation', 'Other') }),
        row(q('currency', 'Monthly income (after tax)', { key: 'income', required: true }), q('currency', 'Monthly debt payments', { key: 'debts', default: 0 })),
        row(
          q('calculated', 'Estimated monthly payment', {
            key: 'monthly_payment',
            formula: 'round({amount} * (1 + {rate} / 100 * {months} / 12) / {months}, 2)',
            help: 'Flat-rate estimate before fees. The lender confirms the real figure.',
          }),
          q('calculated', 'Debt-to-income (%)', { key: 'dti', formula: 'round(({debts} + {monthly_payment}) / {income} * 100)' }),
        ),
        q('file_upload', 'Proof of income', { props: { accept: '.pdf,.jpg,.png', max_files: 3 } }),
        q('consent', 'Credit check', { required: true, props: { text: 'I agree that my details are checked to assess this application.' } }),
        q('signature', 'Signature', { required: true }),
      ]),
    ],
  },
  {
    key: 'kyc_verification',
    category: 'finance_legal',
    icon: 'i-lucide-id-card',
    minutes: 6,
    name: 'KYC / Identity Verification',
    description: 'Identity details, ID document and proof of address, with clear purpose and consent.',
    tags: ['kyc', 'identity', 'verification'],
    pages: [
      page('Identity', [
        q('full_name', 'Full legal name', { required: true, props: { show_middle: true } }),
        row(q('date', 'Date of birth', { required: true }), q('country', 'Nationality', { required: true })),
        q('address', 'Residential address', { required: true }),
        row(q('email', 'Email', { required: true }), q('phone', 'Phone')),
      ]),
      page('Documents', [
        q('radio', 'ID document', { key: 'id_type', required: true, options: opts('Passport', 'National ID card', 'Driving licence', 'Residence permit') }),
        row(q('short_text', 'Document number', { required: true }), q('date', 'Expiry date', { required: true })),
        q('image_upload', 'Photo of the ID (front)', { required: true, props: { max_files: 1 } }),
        q('image_upload', 'Photo of the ID (back)', { key: 'id_back', props: { max_files: 1 } }),
        q('file_upload', 'Proof of address (dated in the last 3 months)', { required: true, props: { accept: '.pdf,.jpg,.png', max_files: 2 } }),
        q('radio', 'Are you a politically exposed person, or closely related to one?', { required: true, options: opts('No', 'Yes') }),
        q('consent', 'Verification', { required: true, props: { text: 'I agree that my identity is verified and my documents are stored securely for this purpose.' } }),
      ]),
    ],
    logic: [rule([['id_type', 'in', ['national_id_card', 'driving_licence', 'residence_permit']]], [['show', 'id_back'], ['require', 'id_back']])],
  },
  {
    key: 'invoice_submission',
    category: 'finance_legal',
    icon: 'i-lucide-file-text',
    minutes: 5,
    name: 'Invoice Submission',
    description: 'Suppliers submit an invoice with line items; subtotal, tax and total are worked out.',
    tags: ['invoice', 'accounts payable'],
    pages: [
      page('Invoice', [
        row(q('short_text', 'Supplier name', { required: true }), q('email', 'Contact email', { required: true })),
        row(q('short_text', 'Invoice number', { required: true }), q('date', 'Invoice date', { required: true }), q('date', 'Due date')),
        row(q('short_text', 'Purchase order number'), q('currency_code', 'Currency')),
        q('section', 'Lines'),
        ...[1, 2, 3].map(n =>
          row(
            q('short_text', 'Description', { key: `desc_${n}`, required: n === 1, width: 6 }),
            q('number', 'Qty', { key: `qty_${n}`, required: n === 1, width: 2, validation: { min: 0 } }),
            q('currency', 'Unit price', { key: `price_${n}`, required: n === 1, width: 4 }),
          ),
        ),
        q('percentage', 'Tax rate', { key: 'tax_rate', default: 0 }),
        row(
          q('calculated', 'Subtotal', { key: 'subtotal', formula: 'round(sum({qty_1} * {price_1}, {qty_2} * {price_2}, {qty_3} * {price_3}), 2)' }),
          q('calculated', 'Tax', { key: 'tax', formula: 'round({subtotal} * {tax_rate} / 100, 2)' }),
          q('calculated', 'Total', { key: 'total', formula: '{subtotal} + {tax}' }),
        ),
        q('file_upload', 'Invoice PDF', { required: true, props: { accept: '.pdf', max_files: 1 } }),
        row(q('iban', 'Pay to (IBAN / account)'), q('bic', 'SWIFT / BIC')),
      ]),
    ],
  },
  {
    key: 'insurance_claim',
    category: 'finance_legal',
    icon: 'i-lucide-shield-check',
    minutes: 8,
    name: 'Insurance Claim',
    description: 'Policy, incident, evidence and itemised losses; the claim total adds up as items are entered.',
    tags: ['insurance', 'claim'],
    pages: [
      page('Policy and incident', [
        row(q('full_name', 'Policy holder', { required: true }), q('short_text', 'Policy number', { required: true })),
        row(q('email', 'Email', { required: true }), q('phone', 'Phone')),
        q('radio', 'Type of claim', { required: true, options: opts('Property', 'Vehicle', 'Travel', 'Health', 'Liability', 'Other') }),
        row(q('datetime', 'When did it happen?', { required: true }), q('short_text', 'Where?', { required: true })),
        q('long_text', 'What happened?', { required: true, validation: { min_length: 30 } }),
        q('toggle', 'Was it reported to the police or another authority?', { key: 'reported' }),
        q('short_text', 'Report reference', { key: 'report_reference' }),
      ]),
      page('Losses', [
        ...[1, 2, 3].map(n =>
          row(
            q('short_text', 'Item or cost', { key: `loss_${n}`, required: n === 1, width: 8 }),
            q('currency', 'Amount', { key: `amount_${n}`, required: n === 1, width: 4 }),
          ),
        ),
        q('calculated', 'Claim total', { key: 'claim_total', formula: 'round(sum({amount_1}, {amount_2}, {amount_3}), 2)' }),
        q('file_upload', 'Evidence (photos, receipts, reports)', { required: true, props: { max_files: 10 } }),
        q('consent', 'Declaration', { required: true, props: { text: 'The information in this claim is true and complete.' } }),
        q('signature', 'Signature', { required: true }),
      ]),
    ],
    logic: [rule([['reported', 'true']], [['show', 'report_reference'], ['require', 'report_reference']])],
  },
  {
    key: 'nda_signoff',
    category: 'finance_legal',
    icon: 'i-lucide-file-signature',
    minutes: 3,
    name: 'NDA / Agreement Sign-off',
    description: 'Show the agreement, confirm each key point and sign, with company details when signing for one.',
    tags: ['nda', 'agreement', 'signature'],
    pages: [
      page('Agreement', [
        q('paragraph', 'Agreement summary', {
          props: { html: '<p>Please read the full agreement attached to your invitation. By signing you confirm that you will keep confidential information private and use it only for the agreed purpose.</p>' },
        }),
        q('file_upload', 'Agreement (for your records)', { props: { accept: '.pdf', max_files: 1 } }),
        q('consent', 'Confidentiality', { required: true, props: { text: 'I will keep confidential information private.' } }),
        q('consent', 'Purpose', { required: true, props: { text: 'I will use it only for the agreed purpose.' } }),
        q('consent', 'Return', { required: true, props: { text: 'I will return or delete it when asked.' } }),
        q('radio', 'Signing as', { key: 'signing_as', required: true, options: opts('An individual', 'On behalf of a company') }),
        q('short_text', 'Company name', { key: 'company' }),
        q('short_text', 'Your role', { key: 'role' }),
        row(q('full_name', 'Full name', { required: true }), q('date', 'Date', { required: true })),
        q('signature', 'Signature', { required: true }),
      ]),
    ],
    logic: [rule([['signing_as', 'eq', 'on_behalf_of_a_company']], [['show', 'company'], ['require', 'company'], ['show', 'role'], ['require', 'role']])],
  },
]
