/** Real Estate templates (F9 milestone 4). */
import { opts, page, q, row, rule, scored, type TemplateDef } from '../kit'

/** Monthly income ÷ monthly rent, and a plain-language affordability band (3× rent is a common guide). */
const affordability = () =>
  row(
    q('calculated', 'Income-to-rent ratio', { key: 'income_ratio', formula: 'round({income} / {rent}, 1)' }),
    q('calculated', 'Affordability', {
      key: 'affordability',
      formula: 'if({income_ratio} >= 3, "Comfortable", if({income_ratio} >= 2.5, "Borderline", "Below guide"))',
      props: { internal: true },
      help: 'Monthly income is compared with 3× the rent — a guide for the landlord, not a decision.',
    }),
  )

const condition = () => scored(['Good', 3], ['Fair', 2], ['Poor', 1])

export const REAL_ESTATE_TEMPLATES: TemplateDef[] = [
  {
    key: 'property_viewing',
    category: 'real_estate',
    icon: 'i-lucide-key-round',
    minutes: 2,
    name: 'Property Viewing Request',
    description: 'Book a viewing: the property, two preferred times, who is coming and how to reach them.',
    tags: ['viewing', 'property', 'appointment'],
    pages: [
      page('Viewing request', [
        q('short_text', 'Property reference or address', { required: true }),
        row(q('datetime', 'Preferred time', { required: true }), q('datetime', 'Second choice')),
        q('radio', 'Viewing type', { options: opts('In person', 'Video call') }),
        row(q('full_name', 'Your name', { required: true }), q('number', 'People attending', { default: 1, validation: { min: 1, max: 10 } })),
        row(q('email', 'Email', { required: true }), q('phone', 'Phone', { required: true })),
        q('radio', 'Are you looking to', { options: opts('Rent', 'Buy') }),
        q('long_text', 'Questions for the agent'),
      ]),
    ],
  },
  {
    key: 'tenant_application',
    category: 'real_estate',
    icon: 'i-lucide-house',
    minutes: 10,
    name: 'Tenant Application',
    description: 'Applicant, employment, income and references, with an income-to-rent ratio for the landlord.',
    tags: ['tenant', 'application', 'screening'],
    pages: [
      page('Applicant', [
        q('full_name', 'Full name', { required: true }),
        row(q('date', 'Date of birth', { required: true }), q('phone', 'Phone', { required: true })),
        q('email', 'Email', { required: true }),
        q('address', 'Current address', { required: true }),
        row(q('number', 'Years at this address', { validation: { min: 0 } }), q('number', 'Number of occupants', { default: 1, validation: { min: 1 } })),
        q('radio', 'Pets', { key: 'pets', options: opts('None', 'Cat', 'Dog', 'Other') }),
        q('short_text', 'Tell us about your pets', { key: 'pet_details' }),
      ]),
      page('Income and references', [
        q('short_text', 'Property applied for', { required: true }),
        row(q('currency', 'Monthly rent', { key: 'rent', required: true }), q('currency', 'Monthly income (before tax)', { key: 'income', required: true })),
        affordability(),
        q('radio', 'Employment', { required: true, options: opts('Employed', 'Self-employed', 'Student', 'Retired', 'Other') }),
        q('short_text', 'Employer'),
        row(q('short_text', 'Previous landlord or agent'), q('phone', 'Their phone')),
        q('file_upload', 'Proof of income and ID', { props: { accept: '.pdf,.jpg,.png', max_files: 5 } }),
        q('consent', 'Checks', { required: true, props: { text: 'I agree to reference and background checks for this application.' } }),
        q('signature', 'Signature', { required: true }),
      ]),
    ],
    logic: [rule([['pets', 'in', ['cat', 'dog', 'other']]], [['show', 'pet_details']])],
  },
  {
    key: 'rental_application',
    category: 'real_estate',
    icon: 'i-lucide-building',
    minutes: 6,
    name: 'Rental Application',
    description: 'A shorter application for a specific listing — move-in date, term, household and affordability.',
    tags: ['rental', 'application', 'lease'],
    pages: [
      page('Rental application', [
        q('short_text', 'Listing', { required: true }),
        row(q('date', 'Move-in date', { required: true }), q('dropdown', 'Lease term', { options: opts('6 months', '12 months', '24 months', 'Flexible') })),
        q('full_name', 'Lead applicant', { required: true }),
        row(q('email', 'Email', { required: true }), q('phone', 'Phone', { required: true })),
        row(q('number', 'Adults', { default: 1, validation: { min: 1 } }), q('number', 'Children', { default: 0, validation: { min: 0 } })),
        row(q('currency', 'Monthly rent', { key: 'rent', required: true }), q('currency', 'Household monthly income', { key: 'income', required: true })),
        affordability(),
        q('toggle', 'Someone will guarantee the rent', { key: 'guarantor' }),
        row(q('full_name', 'Guarantor name', { key: 'guarantor_name' }), q('email', 'Guarantor email', { key: 'guarantor_email' })),
        q('consent', 'Declaration', { required: true, props: { text: 'The information I have given is true and complete.' } }),
      ]),
    ],
    logic: [rule([['guarantor', 'true']], [['show', 'guarantor_name'], ['require', 'guarantor_name'], ['show', 'guarantor_email'], ['require', 'guarantor_email']])],
  },
  {
    key: 'property_inspection',
    category: 'real_estate',
    icon: 'i-lucide-clipboard-check',
    minutes: 8,
    name: 'Property Inspection',
    description: 'Room-by-room condition (good / fair / poor), meter readings and photos, with a condition score.',
    tags: ['inspection', 'check-in', 'inventory'],
    pages: [
      page('Inspection', [
        row(q('short_text', 'Property', { required: true }), q('date', 'Inspection date', { required: true })),
        q('radio', 'Type', { options: opts('Move-in', 'Routine', 'Move-out') }),
        q('section', 'Condition'),
        ...['Entrance and hallway', 'Living area', 'Kitchen', 'Bathroom', 'Bedrooms', 'Outside areas'].map((label, i) =>
          row(
            q('dropdown', label, { key: `room_${i + 1}`, required: i < 5, width: 5, options: condition() }),
            q('short_text', 'Notes', { key: `room_${i + 1}_notes`, width: 7 }),
          ),
        ),
        q('calculated', 'Condition score (%)', {
          key: 'condition_score',
          formula: 'round(sum({room_1}, {room_2}, {room_3}, {room_4}, {room_5}, {room_6}) / (3 * count({room_1}, {room_2}, {room_3}, {room_4}, {room_5}, {room_6})) * 100)',
          help: 'Good = 3, fair = 2, poor = 1 — out of the best possible for the rooms rated.',
        }),
        row(q('number', 'Electricity meter'), q('number', 'Water meter'), q('number', 'Gas meter')),
        q('image_upload', 'Photos', { props: { max_files: 20 } }),
        row(q('full_name', 'Inspector', { required: true }), q('signature', 'Signature', { required: true })),
      ]),
    ],
  },
  {
    key: 'property_maintenance',
    category: 'real_estate',
    icon: 'i-lucide-wrench',
    minutes: 3,
    name: 'Maintenance Request',
    description: 'Tenants report a repair with the area, urgency, photos and when someone can come in.',
    tags: ['maintenance', 'repair', 'tenant'],
    pages: [
      page('Repair request', [
        row(q('full_name', 'Your name', { required: true }), q('short_text', 'Property or unit', { required: true })),
        row(q('email', 'Email', { required: true }), q('phone', 'Phone')),
        q('dropdown', 'Area', { required: true, options: opts('Plumbing', 'Electrical', 'Heating or cooling', 'Appliance', 'Doors, windows or locks', 'Damp or mould', 'Other') }),
        q('radio', 'How urgent is it?', { key: 'urgency', required: true, options: opts('Emergency (danger, flooding, no heating)', 'Urgent (within 48 hours)', 'Routine') }),
        q('paragraph', 'Emergency', { key: 'emergency_note', props: { html: '<p><strong>For emergencies, also call the emergency maintenance number</strong> so someone can come out straight away.</p>' } }),
        q('long_text', 'Describe the problem', { required: true }),
        q('image_upload', 'Photos', { props: { max_files: 5 } }),
        q('toggle', 'Maintenance may enter when I am not home', { key: 'access' }),
        q('long_text', 'Best times to visit', { key: 'times' }),
      ]),
    ],
    logic: [
      rule([['urgency', 'eq', 'emergency_danger_flooding_no_heating']], [['show', 'emergency_note']]),
      rule([['access', 'false']], [['show', 'times'], ['require', 'times']]),
    ],
  },
  {
    key: 'property_information',
    category: 'real_estate',
    icon: 'i-lucide-house-plus',
    minutes: 7,
    name: 'Property Information',
    description: 'Owners describe a property for listing: type, size, rooms, features, price and photos.',
    tags: ['listing', 'property', 'owner'],
    pages: [
      page('Property', [
        q('address', 'Address', { required: true }),
        row(q('dropdown', 'Type', { required: true, options: opts('Apartment', 'House', 'Townhouse', 'Studio', 'Commercial', 'Land') }), q('radio', 'For', { options: opts('Rent', 'Sale') })),
        row(q('number', 'Bedrooms', { validation: { min: 0 } }), q('number', 'Bathrooms', { validation: { min: 0 } }), q('number', 'Floor area (m²)', { validation: { min: 0 } })),
        q('multi_select', 'Features', { options: opts('Parking', 'Garden', 'Balcony', 'Lift', 'Air conditioning', 'Furnished', 'Pets allowed', 'Step-free access') }),
        row(q('currency', 'Asking price or monthly rent', { required: true }), q('date', 'Available from')),
        q('long_text', 'Description', { validation: { max_length: 2000 } }),
        q('image_upload', 'Photos', { props: { max_files: 20 } }),
        q('file_upload', 'Floor plan', { props: { accept: '.pdf,.jpg,.png', max_files: 1 } }),
      ]),
    ],
  },
  {
    key: 'landlord_information',
    category: 'real_estate',
    icon: 'i-lucide-user-round-cog',
    minutes: 5,
    name: 'Landlord Information',
    description: 'Landlord contact, payment details, preferences for tenants and who handles repairs.',
    tags: ['landlord', 'owner', 'management'],
    pages: [
      page('Landlord', [
        q('full_name', 'Full name or company', { required: true }),
        row(q('email', 'Email', { required: true }), q('phone', 'Phone', { required: true })),
        q('address', 'Correspondence address'),
        q('short_text', 'Properties covered', { required: true }),
        row(q('iban', 'Rent paid to (IBAN / account)'), q('bic', 'SWIFT / BIC')),
        q('multi_select', 'Tenant preferences', { options: opts('Pets allowed', 'Smoking allowed', 'Students welcome', 'Families welcome', 'Short lets') }),
        q('radio', 'Who handles repairs?', { key: 'repairs', options: opts('Our management team', 'The landlord', 'Agreed case by case') }),
        q('currency', 'Repairs we may approve without asking (up to)', { key: 'repair_limit' }),
        q('consent', 'Authority', { required: true, props: { text: 'I am the owner, or authorised to act for the owner, of these properties.' } }),
      ]),
    ],
    logic: [rule([['repairs', 'eq', 'our_management_team']], [['show', 'repair_limit']])],
  },
  {
    key: 'tenant_feedback',
    category: 'real_estate',
    icon: 'i-lucide-message-square-heart',
    minutes: 3,
    name: 'Tenant Feedback',
    description: 'Tenants rate the home, repairs, communication and value; an average shows overall satisfaction.',
    tags: ['tenant', 'feedback', 'satisfaction'],
    pages: [
      page('Your feedback', [
        q('short_text', 'Property or unit'),
        row(q('rating', 'Condition of the home', { key: 't1', required: true }), q('rating', 'Speed of repairs', { key: 't2', required: true })),
        row(q('rating', 'Communication', { key: 't3', required: true }), q('rating', 'Value for money', { key: 't4', required: true })),
        q('calculated', 'Average (out of 5)', { key: 'tenant_score', formula: 'round(avg({t1}, {t2}, {t3}, {t4}), 1)' }),
        q('radio', 'Do you plan to renew?', { options: opts('Yes', 'Not sure', 'No') }),
        q('long_text', 'What should we improve?'),
      ]),
    ],
  },
]
