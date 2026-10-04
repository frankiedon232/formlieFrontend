/** Operations & IT templates (F9 milestone 3). */
import { opts, page, q, row, rule, scored, type TemplateDef } from '../kit'

const passFail = scored(['Pass', 1], ['Fail', 0])

export const OPERATIONS_IT_TEMPLATES: TemplateDef[] = [
  {
    key: 'it_support_ticket',
    category: 'operations_it',
    icon: 'i-lucide-life-buoy',
    minutes: 3,
    name: 'IT Support Ticket',
    description: 'Report an IT problem; impact × urgency sets the priority so the right tickets go first.',
    tags: ['it', 'helpdesk', 'ticket'],
    pages: [
      page('Your request', [
        row(q('full_name', 'Name', { required: true }), q('email', 'Email', { required: true })),
        q('dropdown', 'Department', { options: opts('Finance', 'Operations', 'People', 'Sales', 'Support', 'Technology', 'Other') }),
        q('dropdown', 'Category', { required: true, options: opts('Hardware', 'Software', 'Account and access', 'Network or Wi-Fi', 'Email', 'Printing', 'Other') }),
        q('short_text', 'Subject', { required: true }),
        q('long_text', 'What happened, and what did you expect?', { required: true }),
        row(
          q('radio', 'Impact', { key: 'impact', required: true, options: scored(['Just me', 1], ['My team', 2], ['Many people', 3]) }),
          q('radio', 'Urgency', { key: 'urgency', required: true, options: scored(['Can wait', 1], ['Soon', 2], ['Work has stopped', 3]) }),
        ),
        q('calculated', 'Priority', {
          key: 'priority',
          formula: 'if({impact} * {urgency} >= 6, "P1: critical", if({impact} * {urgency} >= 3, "P2: high", "P3: normal"))',
        }),
        row(q('short_text', 'Device or asset tag'), q('ip_address', 'IP address (if known)')),
        q('image_upload', 'Screenshots', { props: { max_files: 4 } }),
      ]),
    ],
  },
  {
    key: 'change_request',
    category: 'operations_it',
    icon: 'i-lucide-git-pull-request-arrow',
    minutes: 8,
    name: 'Change Request',
    description: 'Describe a planned change with a risk score from impact and likelihood, a rollback plan and approval.',
    tags: ['change', 'itil', 'approval'],
    pages: [
      page('The change', [
        row(q('short_text', 'Title', { required: true }), q('full_name', 'Requested by', { required: true })),
        q('radio', 'Type of change', { required: true, options: opts('Standard', 'Normal', 'Emergency') }),
        q('long_text', 'What will change and why?', { required: true }),
        q('checkbox', 'Systems affected', { options: opts('Website', 'Customer app', 'Internal tools', 'Database', 'Network', 'Email', 'Other') }),
        row(q('datetime', 'Planned start', { required: true }), q('duration', 'Expected duration')),
      ]),
      page('Risk and rollback', [
        row(
          q('radio', 'Impact if it goes wrong', { key: 'impact', required: true, options: scored(['Low', 1], ['Medium', 2], ['High', 3]) }),
          q('radio', 'Likelihood of problems', { key: 'likelihood', required: true, options: scored(['Unlikely', 1], ['Possible', 2], ['Likely', 3]) }),
        ),
        row(
          q('calculated', 'Risk score (1–9)', { key: 'risk_score', formula: '{impact} * {likelihood}' }),
          q('calculated', 'Approval needed', { key: 'approval', formula: 'if({risk_score} >= 6, "Change board", if({risk_score} >= 3, "Team lead", "Pre-approved"))' }),
        ),
        q('long_text', 'Test plan'),
        q('long_text', 'Rollback plan', { key: 'rollback' }),
        q('toggle', 'Customers need to be told', { key: 'notify_customers' }),
        q('long_text', 'Message to customers', { key: 'customer_message' }),
      ]),
    ],
    logic: [
      rule([['risk_score', 'gte', 3]], [['require', 'rollback']]),
      rule([['notify_customers', 'true']], [['show', 'customer_message'], ['require', 'customer_message']]),
    ],
  },
  {
    key: 'asset_checkout',
    category: 'operations_it',
    icon: 'i-lucide-laptop',
    minutes: 3,
    name: 'Asset Check-out / Inventory',
    description: 'Check equipment in or out with asset tag, condition, return date and signature.',
    tags: ['asset', 'inventory', 'equipment'],
    pages: [
      page('Asset', [
        q('radio', 'Action', { key: 'action', required: true, options: opts('Check out', 'Check in') }),
        row(q('short_text', 'Asset tag', { required: true }), q('dropdown', 'Type', { options: opts('Laptop', 'Phone', 'Tablet', 'Monitor', 'Tool', 'Vehicle', 'Other') })),
        row(q('short_text', 'Make and model'), q('short_text', 'Serial number')),
        q('mac_address', 'MAC address (network devices)'),
        q('full_name', 'Person', { required: true }),
        row(q('date', 'Date', { required: true }), q('date', 'Expected return date', { key: 'return_date' })),
        q('radio', 'Condition', { required: true, options: opts('New', 'Good', 'Fair', 'Damaged') }),
        q('long_text', 'Notes'),
        q('signature', 'Signature', { required: true }),
      ]),
    ],
    logic: [rule([['action', 'eq', 'check_out']], [['require', 'return_date']])],
  },
  {
    key: 'work_order',
    category: 'operations_it',
    icon: 'i-lucide-hammer',
    minutes: 4,
    name: 'Maintenance / Work Order',
    description: 'Request maintenance with location, priority and photos; hours and parts give the job cost.',
    tags: ['maintenance', 'work order', 'facilities'],
    pages: [
      page('Request', [
        row(q('full_name', 'Requested by', { required: true }), q('phone', 'Phone')),
        q('short_text', 'Location (building, floor, room)', { required: true }),
        q('dropdown', 'Type of work', { required: true, options: opts('Electrical', 'Plumbing', 'Heating and cooling', 'Building', 'Cleaning', 'Grounds', 'Other') }),
        q('radio', 'Priority', { required: true, options: opts('Low', 'Normal', 'High', 'Emergency') }),
        q('long_text', 'Describe the problem', { required: true }),
        q('image_upload', 'Photos', { props: { max_files: 4 } }),
      ]),
      page('Completion (team)', [
        row(q('full_name', 'Technician'), q('date', 'Completed on')),
        row(
          q('number', 'Hours worked', { key: 'hours', validation: { min: 0, max: 200 } }),
          q('currency', 'Hourly rate', { key: 'rate' }),
          q('currency', 'Parts', { key: 'parts' }),
        ),
        q('calculated', 'Job cost', { key: 'job_cost', formula: 'round(sum({hours} * {rate}, {parts}), 2)' }),
        q('long_text', 'Work done'),
      ]),
    ],
  },
  {
    key: 'purchase_requisition',
    category: 'operations_it',
    icon: 'i-lucide-shopping-bag',
    minutes: 5,
    name: 'Purchase Requisition',
    description: 'Request up to four items with quantity and price; the total decides which approval is needed.',
    tags: ['purchase', 'requisition', 'approval'],
    pages: [
      page('Requisition', [
        row(q('full_name', 'Requested by', { required: true }), q('dropdown', 'Department', { required: true, options: opts('Finance', 'Operations', 'People', 'Sales', 'Support', 'Technology') })),
        row(q('short_text', 'Cost centre'), q('date', 'Needed by')),
        q('section', 'Items'),
        ...[1, 2, 3, 4].map(n =>
          row(
            q('short_text', 'Item', { key: `item_${n}`, required: n === 1, width: 5 }),
            q('number', 'Qty', { key: `qty_${n}`, required: n === 1, width: 2, validation: { min: 0 } }),
            q('currency', 'Unit price', { key: `price_${n}`, required: n === 1, width: 2 }),
            q('calculated', 'Line total', { key: `line_${n}`, width: 3, formula: `{qty_${n}} * {price_${n}}` }),
          ),
        ),
        row(
          q('calculated', 'Total', { key: 'total', formula: 'round(sum({line_1}, {line_2}, {line_3}, {line_4}), 2)' }),
          q('calculated', 'Approval', { key: 'approval', formula: 'if({total} > 10000, "Finance director", if({total} > 1000, "Department head", "Team lead"))' }),
        ),
        q('short_text', 'Preferred supplier'),
        q('long_text', 'Why is this needed?', { required: true }),
        q('file_upload', 'Quotes', { props: { max_files: 3 } }),
      ]),
    ],
  },
  {
    key: 'vendor_registration',
    category: 'operations_it',
    icon: 'i-lucide-building',
    minutes: 8,
    name: 'Vendor / Supplier Registration',
    description: 'Company, contacts, tax and bank details (IBAN / SWIFT) and documents for supplier onboarding.',
    tags: ['vendor', 'supplier', 'onboarding'],
    pages: [
      page('Company', [
        q('short_text', 'Registered company name', { required: true }),
        row(q('short_text', 'Company registration number', { required: true }), q('short_text', 'Tax / VAT number')),
        q('address', 'Registered address', { required: true }),
        row(q('url', 'Website'), q('domain', 'Email domain')),
        q('multi_select', 'What do you supply?', { options: opts('Goods', 'Services', 'Software', 'Consulting', 'Logistics', 'Facilities') }),
      ]),
      page('Contacts and payment', [
        row(q('full_name', 'Main contact', { required: true }), q('email', 'Contact email', { required: true })),
        q('phone', 'Contact phone'),
        row(q('iban', 'IBAN / account number'), q('bic', 'SWIFT / BIC')),
        q('currency_code', 'Invoice currency'),
        q('dropdown', 'Payment terms', { options: opts('Immediate', '14 days', '30 days', '60 days') }),
        q('file_upload', 'Company documents (registration, insurance)', { props: { max_files: 5 } }),
        q('consent', 'Code of conduct', { required: true, props: { text: 'We agree to the supplier code of conduct.' } }),
      ]),
    ],
  },
  {
    key: 'site_inspection',
    category: 'operations_it',
    icon: 'i-lucide-hard-hat',
    minutes: 10,
    name: 'Site / Field Inspection Report',
    description: 'On-site pass / fail checks with a pass rate, an outcome, findings and photos.',
    tags: ['inspection', 'field', 'site'],
    pages: [
      page('Site', [
        row(q('short_text', 'Site name', { required: true }), q('datetime', 'Inspection date and time', { required: true })),
        q('address', 'Site address'),
        row(q('full_name', 'Inspector', { required: true }), q('dropdown', 'Weather', { options: opts('Clear', 'Rain', 'Wind', 'Snow', 'Heat') })),
      ]),
      page('Checks', [
        ...['Access and signage', 'Work area tidy', 'Equipment in good order', 'Permits on site', 'Protective equipment worn', 'Environmental controls in place'].map((label, i) =>
          q('radio', label, { key: `check_${i + 1}`, required: true, options: passFail }),
        ),
        row(
          q('calculated', 'Pass rate (%)', { key: 'pass_rate', formula: 'round(sum({check_1}, {check_2}, {check_3}, {check_4}, {check_5}, {check_6}) / 6 * 100)' }),
          q('calculated', 'Outcome', { key: 'outcome', formula: 'if({pass_rate} = 100, "Satisfactory", if({pass_rate} >= 70, "Minor issues", "Action required"))' }),
        ),
        q('long_text', 'Findings and actions', { key: 'findings' }),
        q('image_upload', 'Photos', { props: { max_files: 10 } }),
        q('signature', 'Inspector signature', { required: true }),
      ]),
    ],
    logic: [rule([['pass_rate', 'lt', 100]], [['require', 'findings']])],
  },
  {
    key: 'proof_of_delivery',
    category: 'operations_it',
    icon: 'i-lucide-truck',
    minutes: 2,
    name: 'Delivery Confirmation / Proof of Delivery',
    description: 'Confirm what arrived, its condition, a photo and the receiver’s signature. Damage asks for details.',
    tags: ['delivery', 'logistics', 'pod'],
    pages: [
      page('Delivery', [
        row(q('short_text', 'Delivery or order number', { required: true }), q('datetime', 'Delivered at', { required: true })),
        q('address', 'Delivery address'),
        row(q('number', 'Packages delivered', { required: true, validation: { min: 0 } }), q('number', 'Packages expected', { validation: { min: 0 } })),
        q('radio', 'Condition', { key: 'condition', required: true, options: opts('All good', 'Damaged', 'Missing items') }),
        q('long_text', 'What was damaged or missing?', { key: 'issue' }),
        q('image_upload', 'Photo of the delivery', { props: { max_files: 4 } }),
        q('full_name', 'Received by', { required: true }),
        q('signature', 'Receiver signature', { required: true }),
      ]),
    ],
    logic: [rule([['condition', 'in', ['damaged', 'missing_items']]], [['show', 'issue'], ['require', 'issue']])],
  },
  {
    key: 'quality_control',
    category: 'operations_it',
    icon: 'i-lucide-badge-check',
    minutes: 6,
    name: 'Quality Control Checklist',
    description: 'Batch details, pass / fail criteria and measurements; the pass rate gives a release decision.',
    tags: ['quality', 'qc', 'checklist'],
    pages: [
      page('Batch', [
        row(q('short_text', 'Product', { required: true }), q('short_text', 'Batch or lot number', { required: true })),
        row(q('date', 'Inspection date', { required: true }), q('full_name', 'Inspector', { required: true })),
        q('number', 'Sample size', { validation: { min: 1 } }),
      ]),
      page('Checks', [
        ...['Dimensions within tolerance', 'Visual finish', 'Labelling correct', 'Packaging intact', 'Function test'].map((label, i) =>
          q('radio', label, { key: `qc_${i + 1}`, required: true, options: passFail }),
        ),
        row(
          q('calculated', 'Pass rate (%)', { key: 'qc_rate', formula: 'round(sum({qc_1}, {qc_2}, {qc_3}, {qc_4}, {qc_5}) / 5 * 100)' }),
          q('calculated', 'Decision', { key: 'decision', formula: 'if({qc_rate} = 100, "Release", if({qc_rate} >= 80, "Release with note", "Hold"))' }),
        ),
        q('long_text', 'Defects found', { key: 'defects' }),
        q('image_upload', 'Photos of defects', { props: { max_files: 6 } }),
        q('signature', 'Signature', { required: true }),
      ]),
    ],
    logic: [rule([['qc_rate', 'lt', 100]], [['require', 'defects']])],
  },
]
