/** HR & Workplace templates (F9 milestone 1). */
import { agreeScale, opts, page, q, row, rule, scored, type TemplateDef } from '../kit'

const DEPARTMENTS = opts('Finance', 'Operations', 'People', 'Sales', 'Support', 'Technology', 'Other')
const performance = scored(['Needs improvement', 1], ['Developing', 2], ['Meets expectations', 3], ['Strong', 4], ['Outstanding', 5])

export const HR_TEMPLATES: TemplateDef[] = [
  {
    key: 'job_application',
    category: 'hr',
    icon: 'i-lucide-briefcase',
    minutes: 8,
    name: 'Job Application',
    description: 'A complete application: personal details, the role, CV upload, salary expectation and consent.',
    tags: ['recruiting', 'application', 'cv'],
    pages: [
      page('About you', [
        q('full_name', 'Full name', { required: true }),
        row(q('email', 'Email', { required: true }), q('phone', 'Phone', { required: true })),
        row(q('country', 'Country of residence'), q('url', 'LinkedIn or portfolio')),
      ]),
      page('The role', [
        q('dropdown', 'Position', { required: true, options: opts('Operations', 'Engineering', 'Design', 'Sales', 'Customer success', 'Finance') }),
        row(q('date', 'Earliest start date'), q('radio', 'Work arrangement', { options: opts('On-site', 'Hybrid', 'Remote') })),
        q('currency', 'Expected yearly salary'),
        q('toggle', 'Do you need sponsorship to work in this country?', { key: 'sponsorship' }),
        q('file_upload', 'CV / résumé', { required: true, props: { accept: '.pdf,.doc,.docx', max_mb: 10 } }),
        q('file_upload', 'Cover letter (optional)', { props: { accept: '.pdf,.doc,.docx' } }),
        q('long_text', 'Why would you like to join us?', { validation: { max_length: 2000 } }),
      ]),
      page('Consent', [
        q('consent', 'Data processing', { required: true, props: { text: 'I agree that my data is processed for this application and kept for up to 12 months.' } }),
      ]),
    ],
    thankYou: { title: 'Application received', message: 'Thank you for applying. We will be in touch within two weeks.' },
  },
  {
    key: 'employee_onboarding',
    category: 'hr',
    icon: 'i-lucide-user-round-plus',
    minutes: 10,
    name: 'Employee Onboarding',
    description: 'Everything a new starter shares before day one: details, emergency contact, equipment and payment.',
    tags: ['onboarding', 'new starter'],
    pages: [
      page('Personal details', [
        row(q('short_text', 'Legal first name', { required: true }), q('short_text', 'Legal last name', { required: true })),
        row(q('short_text', 'Preferred name'), q('date', 'Date of birth')),
        row(q('phone', 'Mobile number', { required: true }), q('email', 'Personal email')),
        q('address', 'Home address', { required: true }),
      ]),
      page('Work set-up', [
        row(q('date', 'Start date', { required: true }), q('dropdown', 'Team', { options: DEPARTMENTS })),
        q('radio', 'Laptop', { options: opts('Windows', 'macOS', 'No preference') }),
        q('checkbox', 'Accessibility or equipment needs', { options: opts('Standing desk', 'Second monitor', 'Screen reader', 'Ergonomic chair', 'None') }),
        q('image_upload', 'Photo for your ID badge'),
      ]),
      page('Emergency contact and payment', [
        row(q('short_text', 'Emergency contact name', { required: true }), q('phone', 'Emergency contact phone', { required: true })),
        q('short_text', 'Relationship'),
        row(q('iban', 'Bank account (IBAN, where used)'), q('bic', 'SWIFT / BIC')),
        q('signature', 'Signature', { required: true }),
      ]),
    ],
  },
  {
    key: 'exit_interview',
    category: 'hr',
    icon: 'i-lucide-door-open',
    minutes: 6,
    name: 'Exit Interview',
    description: 'Learn why people leave and what would make them stay, with ratings across the employee experience.',
    tags: ['exit', 'offboarding', 'retention'],
    pages: [
      page('Leaving', [
        row(q('short_text', 'Name'), q('dropdown', 'Department', { options: DEPARTMENTS })),
        q('date', 'Last working day', { required: true }),
        q('radio', 'Main reason for leaving', {
          key: 'reason',
          required: true,
          options: opts('Career growth', 'Pay and benefits', 'Manager', 'Work-life balance', 'Relocation', 'Other'),
        }),
        q('short_text', 'Please tell us more', { key: 'reason_other' }),
        q('matrix', 'How would you rate…', {
          options: opts('Poor', 'Fair', 'Good', 'Excellent'),
          props: { rows: ['Management', 'Pay and benefits', 'Work environment', 'Training', 'Career growth'] },
        }),
        q('scale', 'How likely are you to recommend us as an employer?', { props: { min: 0, max: 10, min_label: 'Not likely', max_label: 'Very likely' } }),
        q('radio', 'Would you consider coming back?', { options: opts('Yes', 'Maybe', 'No') }),
        q('long_text', 'What could we have done to keep you?'),
      ]),
    ],
    logic: [rule([['reason', 'eq', 'other']], [['show', 'reason_other'], ['require', 'reason_other']])],
  },
  {
    key: 'leave_request',
    category: 'hr',
    icon: 'i-lucide-plane',
    minutes: 3,
    name: 'Leave / Time-Off Request',
    description: 'Request leave with the number of days worked out from the dates, cover and supporting documents.',
    tags: ['leave', 'holiday', 'absence'],
    design: { colors: { primary: '#0891b2' }, header: { band_bg: '#155e75' } },
    pages: [
      page('Leave request', [
        q('full_name', 'Employee name', { required: true }),
        row(q('short_text', 'Employee ID'), q('dropdown', 'Department', { options: DEPARTMENTS })),
        q('radio', 'Type of leave', {
          key: 'leave_type',
          required: true,
          options: opts('Annual', 'Sick', 'Parental', 'Compassionate', 'Unpaid', 'Other'),
        }),
        row(q('date', 'First day', { key: 'first_day', required: true }), q('date', 'Last day', { key: 'last_day', required: true })),
        q('calculated', 'Days requested (calendar days)', { key: 'days_requested', formula: 'days({first_day}, {last_day}) + 1' }),
        q('long_text', 'Reason or notes'),
        q('short_text', 'Who covers your work?'),
        q('file_upload', 'Supporting document (e.g. medical note)', { key: 'document' }),
      ]),
    ],
    logic: [rule([['leave_type', 'in', ['sick', 'parental']]], [['show', 'document']])],
  },
  {
    key: 'performance_review',
    category: 'hr',
    icon: 'i-lucide-chart-no-axes-combined',
    minutes: 15,
    name: 'Performance Review / Appraisal',
    description: 'Rate six competencies; the average score and rating band are calculated for you.',
    tags: ['appraisal', 'review', 'goals'],
    pages: [
      page('Review details', [
        row(q('short_text', 'Employee', { required: true }), q('short_text', 'Reviewer', { required: true })),
        q('date_range', 'Review period', { required: true }),
      ]),
      page('Ratings', [
        ...(['Quality of work', 'Productivity', 'Communication', 'Teamwork', 'Initiative', 'Reliability'] as const).map((label, i) =>
          q('radio', label, { key: `c${i + 1}`, required: true, options: performance }),
        ),
        row(
          q('calculated', 'Average score', { key: 'average', formula: 'round(avg({c1}, {c2}, {c3}, {c4}, {c5}, {c6}), 1)' }),
          q('calculated', 'Rating band', {
            key: 'band',
            formula: 'if({average} >= 4.5, "Outstanding", if({average} >= 3.5, "Strong", if({average} >= 2.5, "Meets expectations", "Needs improvement")))',
          }),
        ),
      ]),
      page('Goals and sign-off', [
        q('long_text', 'Strengths'),
        q('long_text', 'Areas to develop'),
        q('long_text', 'Goals for the next period'),
        row(q('signature', 'Employee signature'), q('signature', 'Reviewer signature', { required: true })),
      ]),
    ],
  },
  {
    key: 'engagement_survey',
    category: 'hr',
    icon: 'i-lucide-heart-handshake',
    minutes: 6,
    name: 'Employee Engagement Survey',
    description: 'An anonymous pulse on pride, purpose, growth and support, with an engagement index from 0 to 100.',
    tags: ['engagement', 'survey', 'anonymous'],
    design: { colors: { primary: '#0d9488' }, header: { band: 'gradient', band_bg: '#0f766e', band_to: '#14b8a6' } },
    pages: [
      page('About you', [
        q('paragraph', 'Intro', { props: { html: '<p>This survey is anonymous. Please answer honestly. It helps us make this a better place to work.</p>' } }),
        row(q('dropdown', 'Department', { options: DEPARTMENTS }), q('radio', 'Time with us', { options: opts('Under 1 year', '1–3 years', '3–5 years', 'Over 5 years') })),
      ]),
      page('Your views', [
        ...[
          'I am proud to work here',
          'I understand how my work contributes to our goals',
          'I have the tools I need to do my job well',
          'My manager supports my development',
          'I feel recognised for good work',
          'I see myself working here in two years',
        ].map((label, i) => q('radio', label, { key: `e${i + 1}`, required: true, options: agreeScale() })),
        q('calculated', 'Engagement index (0–100)', {
          key: 'engagement_index',
          formula: 'round((avg({e1}, {e2}, {e3}, {e4}, {e5}, {e6}) - 1) / 4 * 100)',
          props: { internal: true },
        }),
        q('long_text', 'If you could change one thing, what would it be?'),
      ]),
    ],
  },
  {
    key: 'expense_reimbursement',
    category: 'hr',
    icon: 'i-lucide-receipt',
    minutes: 5,
    name: 'Expense Reimbursement',
    description: 'Claim up to three expenses with receipts; the claim total adds itself up.',
    tags: ['expenses', 'claim', 'receipts'],
    design: { colors: { primary: '#047857' }, header: { band_bg: '#065f46' } },
    pages: [
      page('Claim', [
        row(q('full_name', 'Employee name', { required: true }), q('email', 'Email', { required: true })),
        row(q('dropdown', 'Department', { options: DEPARTMENTS }), q('short_text', 'Cost centre')),
        q('currency_code', 'Currency of the claim'),
        q('section', 'Expenses', { props: { description: 'One line per expense.' } }),
        ...[1, 2, 3].map(n =>
          row(
            q('date', 'Date', { key: `date_${n}`, required: n === 1, width: 3 }),
            q('dropdown', 'Category', { key: `category_${n}`, required: n === 1, width: 3, options: opts('Travel', 'Accommodation', 'Meals', 'Supplies', 'Training', 'Other') }),
            q('short_text', 'Description', { key: `description_${n}`, width: 3 }),
            q('currency', 'Amount', { key: `amount_${n}`, required: n === 1, width: 3 }),
          ),
        ),
        q('calculated', 'Claim total', { key: 'claim_total', formula: 'round(sum({amount_1}, {amount_2}, {amount_3}), 2)' }),
        q('file_upload', 'Receipts', { required: true, props: { max_files: 10 } }),
        q('consent', 'Declaration', { required: true, props: { text: 'I confirm these expenses were incurred for work and have not been claimed before.' } }),
        q('signature', 'Signature', { required: true }),
      ]),
    ],
  },
  {
    key: 'timesheet',
    category: 'hr',
    icon: 'i-lucide-clock-4',
    minutes: 3,
    name: 'Timesheet',
    description: 'Weekly hours per day with total and overtime against contracted hours.',
    tags: ['hours', 'overtime', 'weekly'],
    design: { colors: { primary: '#4338ca' }, header: { band_bg: '#3730a3' } },
    pages: [
      page('Weekly timesheet', [
        row(q('full_name', 'Employee name', { required: true }), q('short_text', 'Employee ID')),
        row(q('date', 'Week starting', { required: true }), q('number', 'Contracted hours per week', { key: 'contracted', default: 40, validation: { min: 0, max: 80 } })),
        q('section', 'Hours worked'),
        row(
          ...(['Mon', 'Tue', 'Wed', 'Thu'] as const).map(day =>
            q('number', day, { key: `h_${day.toLowerCase()}`, width: 3, validation: { min: 0, max: 24 } }),
          ),
        ),
        row(
          ...(['Fri', 'Sat', 'Sun'] as const).map(day =>
            q('number', day, { key: `h_${day.toLowerCase()}`, width: 4, validation: { min: 0, max: 24 } }),
          ),
        ),
        row(
          q('calculated', 'Total hours', { key: 'total_hours', formula: 'sum({h_mon}, {h_tue}, {h_wed}, {h_thu}, {h_fri}, {h_sat}, {h_sun})' }),
          q('calculated', 'Overtime', { key: 'overtime', formula: 'max(0, {total_hours} - {contracted})' }),
        ),
        q('long_text', 'Notes (projects, absences)'),
        q('signature', 'Signature', { required: true }),
      ]),
    ],
  },
  {
    key: 'training_feedback',
    category: 'hr',
    icon: 'i-lucide-presentation',
    minutes: 3,
    name: 'Training Feedback',
    description: 'Rate the content, trainer, materials and relevance of a course, with an average score.',
    tags: ['training', 'course', 'feedback'],
    pages: [
      page('Training feedback', [
        row(q('short_text', 'Course', { required: true }), q('short_text', 'Trainer'), q('date', 'Date')),
        row(q('rating', 'Content', { key: 'r_content', required: true }), q('rating', 'Trainer', { key: 'r_trainer', required: true })),
        row(q('rating', 'Materials', { key: 'r_materials' }), q('rating', 'Relevance to my work', { key: 'r_relevance' })),
        q('calculated', 'Average rating', { key: 'average', formula: 'round(avg({r_content}, {r_trainer}, {r_materials}, {r_relevance}), 1)' }),
        q('radio', 'Did the training meet its objectives?', { options: opts('Fully', 'Partly', 'Not at all') }),
        q('scale', 'How likely are you to recommend this training?', { props: { min: 0, max: 10, min_label: 'Not likely', max_label: 'Very likely' } }),
        q('long_text', 'What was most useful?'),
        q('long_text', 'What should we improve?'),
      ]),
    ],
  },
  {
    key: 'reference_check',
    category: 'hr',
    icon: 'i-lucide-user-check',
    minutes: 6,
    name: 'Reference Check',
    description: 'Structured questions for referees, rated skills with an average and a clear hire-again answer.',
    tags: ['reference', 'recruiting'],
    pages: [
      page('Candidate and referee', [
        row(q('short_text', 'Candidate name', { required: true }), q('short_text', 'Position applied for')),
        q('full_name', 'Your name (referee)', { required: true }),
        row(q('email', 'Your email', { required: true }), q('phone', 'Your phone')),
        row(q('short_text', 'Your relationship to the candidate', { required: true }), q('date_range', 'Worked together')),
      ]),
      page('Assessment', [
        ...['Reliability', 'Skills for the role', 'Teamwork', 'Communication'].map((label, i) =>
          q('rating', label, { key: `s${i + 1}`, required: true }),
        ),
        q('calculated', 'Average rating', { key: 'average', formula: 'round(avg({s1}, {s2}, {s3}, {s4}), 1)', props: { internal: true } }),
        q('radio', 'Would you hire or work with them again?', { required: true, options: opts('Yes', 'Maybe', 'No') }),
        q('long_text', 'Main strengths'),
        q('long_text', 'Areas for development'),
        q('consent', 'Sharing', { required: true, props: { text: 'I agree that my answers are shared with the hiring team.' } }),
        q('signature', 'Signature'),
      ]),
    ],
  },
]
