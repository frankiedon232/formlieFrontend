/** Education templates (F9 milestone 3). */
import { agreeScale, opts, page, q, row, rule, scored, type TemplateDef } from '../kit'

export const EDUCATION_TEMPLATES: TemplateDef[] = [
  {
    key: 'student_enrolment',
    category: 'education',
    icon: 'i-lucide-school',
    minutes: 10,
    name: 'Student Enrolment / Admission',
    description: 'Student and guardian details, programme choice, previous education, documents and consent.',
    tags: ['enrolment', 'admission', 'school'],
    pages: [
      page('Student', [
        q('full_name', 'Student name', { required: true }),
        row(q('date', 'Date of birth', { key: 'dob', required: true }), q('country', 'Nationality')),
        row(q('email', 'Email'), q('phone', 'Phone')),
        q('address', 'Home address', { required: true }),
        q('language', 'Main language at home'),
      ]),
      page('Programme', [
        q('dropdown', 'Programme or year group', { required: true, options: opts('Early years', 'Primary', 'Lower secondary', 'Upper secondary', 'Foundation course', 'Diploma') }),
        q('date', 'Preferred start date', { required: true }),
        q('radio', 'Study mode', { options: opts('Full-time', 'Part-time', 'Online') }),
        q('short_text', 'Previous school or institution'),
        q('file_upload', 'Latest report or transcript', { props: { accept: '.pdf,.jpg,.png', max_files: 3 } }),
        q('long_text', 'Learning support or medical needs'),
      ]),
      page('Parent or guardian', [
        q('toggle', 'The student is under 18', { key: 'minor', default: true }),
        q('full_name', 'Parent or guardian name', { key: 'guardian_name' }),
        row(q('email', 'Guardian email', { key: 'guardian_email' }), q('phone', 'Guardian phone', { key: 'guardian_phone' })),
        q('short_text', 'Relationship to the student', { key: 'guardian_relationship' }),
        q('consent', 'Consent', { required: true, props: { text: 'I confirm the information is correct and agree that it is used for admission.' } }),
        q('signature', 'Signature', { required: true }),
      ]),
    ],
    logic: [
      rule([['minor', 'true']], [['show', 'guardian_name'], ['require', 'guardian_name'], ['show', 'guardian_email'], ['require', 'guardian_email'], ['show', 'guardian_phone'], ['show', 'guardian_relationship']]),
    ],
  },
  {
    key: 'course_evaluation',
    category: 'education',
    icon: 'i-lucide-book-open-check',
    minutes: 4,
    name: 'Course Evaluation',
    description: 'Students rate the course on six statements; an overall score shows how the course is landing.',
    tags: ['course', 'evaluation', 'feedback'],
    pages: [
      page('Course evaluation', [
        row(q('short_text', 'Course', { required: true }), q('short_text', 'Teacher or lecturer')),
        ...[
          'The course objectives were clear',
          'The materials helped me learn',
          'The teaching was engaging',
          'The workload was reasonable',
          'Assessments matched what was taught',
          'I would recommend this course',
        ].map((label, i) => q('radio', label, { key: `c${i + 1}`, required: true, options: agreeScale() })),
        q('calculated', 'Course score (out of 5)', { key: 'course_score', formula: 'round(avg({c1}, {c2}, {c3}, {c4}, {c5}, {c6}), 1)' }),
        q('long_text', 'What worked best?'),
        q('long_text', 'What should change?'),
      ]),
    ],
  },
  {
    key: 'quiz_assessment',
    category: 'education',
    icon: 'i-lucide-list-checks',
    minutes: 6,
    name: 'Quiz / Assessment',
    description: 'Multiple-choice questions scored automatically, with a percentage and a pass mark.',
    tags: ['quiz', 'test', 'assessment'],
    design: { colors: { primary: '#7c3aed' }, header: { band_bg: '#6d28d9', band_to: '#2563eb' } },
    pages: [
      page('About you', [row(q('full_name', 'Name', { required: true }), q('short_text', 'Class or group'))]),
      page('Questions', [
        q('radio', '1. Which of these is a renewable source of energy?', { key: 'q1', required: true, options: scored(['Coal', 0], ['Wind', 1], ['Natural gas', 0], ['Oil', 0]) }),
        q('radio', '2. What is 15% of 200?', { key: 'q2', required: true, options: scored(['15', 0], ['20', 0], ['30', 1], ['35', 0]) }),
        q('radio', '3. Which planet is closest to the Sun?', { key: 'q3', required: true, options: scored(['Venus', 0], ['Mercury', 1], ['Mars', 0], ['Earth', 0]) }),
        q('radio', '4. How many sides does a hexagon have?', { key: 'q4', required: true, options: scored(['5', 0], ['6', 1], ['7', 0], ['8', 0]) }),
        q('radio', '5. Water boils at sea level at…', { key: 'q5', required: true, options: scored(['90 °C', 0], ['100 °C', 1], ['110 °C', 0], ['120 °C', 0]) }),
        row(
          q('calculated', 'Score (out of 5)', { key: 'score', formula: 'sum({q1}, {q2}, {q3}, {q4}, {q5})' }),
          q('calculated', 'Percentage', { key: 'percentage', formula: 'round({score} / 5 * 100)' }),
          q('calculated', 'Result', { key: 'result', formula: 'if({percentage} >= 60, "Pass", "Not yet")' }),
        ),
      ]),
    ],
    thankYou: { title: 'Quiz submitted', message: 'Thank you — your teacher will share the results.' },
  },
  {
    key: 'scholarship_application',
    category: 'education',
    icon: 'i-lucide-award',
    minutes: 12,
    name: 'Scholarship Application',
    description: 'Academic record, financial need and a personal statement — with an eligibility score for the panel.',
    tags: ['scholarship', 'bursary', 'grant'],
    pages: [
      page('Applicant', [
        q('full_name', 'Full name', { required: true }),
        row(q('email', 'Email', { required: true }), q('phone', 'Phone')),
        row(q('date', 'Date of birth'), q('country', 'Country of residence')),
        q('short_text', 'School, college or university', { required: true }),
      ]),
      page('Eligibility', [
        q('radio', 'Latest overall grade', { key: 'grade', required: true, options: scored(['Excellent (top 10%)', 4], ['Very good', 3], ['Good', 2], ['Satisfactory', 1]) }),
        q('radio', 'Household income compared with your area', { key: 'need', required: true, options: scored(['Well below average', 4], ['Below average', 3], ['Around average', 1], ['Above average', 0]) }),
        q('checkbox', 'Activities and achievements', { key: 'activities', options: scored(['Community service', 1], ['Sports', 1], ['Arts or music', 1], ['Leadership role', 1], ['Awards or competitions', 1]) }),
        q('calculated', 'Eligibility score', {
          key: 'eligibility',
          formula: '{grade} + {need} + if(count({activities}) > 0, {activities}, 0)',
          props: { internal: true },
          help: 'Grade (up to 4) + need (up to 4) + one point per activity — for the panel only.',
        }),
      ]),
      page('Statement', [
        q('long_text', 'Personal statement: why should you receive this scholarship?', { required: true, validation: { min_length: 200, max_length: 3000 } }),
        q('file_upload', 'Transcript', { required: true, props: { accept: '.pdf', max_files: 1 } }),
        q('file_upload', 'Reference letter', { props: { accept: '.pdf', max_files: 2 } }),
        q('consent', 'Declaration', { required: true, props: { text: 'The information I have provided is true and complete.' } }),
      ]),
    ],
  },
  {
    key: 'permission_slip',
    category: 'education',
    icon: 'i-lucide-file-check',
    minutes: 3,
    name: 'Parent Consent / Permission Slip',
    description: 'Permission for a trip or activity with medical notes, emergency contact and a guardian signature.',
    tags: ['permission', 'consent', 'trip'],
    pages: [
      page('Permission', [
        q('paragraph', 'Activity details', { props: { html: '<p>Please read the activity details sent by the school and complete this form by the deadline.</p>' } }),
        row(q('short_text', 'Student name', { required: true }), q('short_text', 'Class')),
        q('short_text', 'Activity or trip', { required: true }),
        q('radio', 'Do you give permission?', { key: 'permission', required: true, options: opts('Yes', 'No') }),
        q('long_text', 'Medical needs, allergies or medicines', { key: 'medical' }),
        row(q('short_text', 'Emergency contact', { key: 'emergency_name' }), q('phone', 'Emergency phone', { key: 'emergency_phone' })),
        q('full_name', 'Parent or guardian name', { required: true }),
        q('signature', 'Signature', { required: true }),
      ]),
    ],
    logic: [rule([['permission', 'eq', 'yes']], [['require', 'emergency_name'], ['require', 'emergency_phone']])],
  },
  {
    key: 'attendance_register',
    category: 'education',
    icon: 'i-lucide-calendar-check-2',
    minutes: 3,
    name: 'Attendance Register',
    description: 'Mark up to eight learners present, late or absent; the present count and rate add up automatically.',
    tags: ['attendance', 'register', 'class'],
    pages: [
      page('Register', [
        row(q('short_text', 'Class or group', { required: true }), q('date', 'Date', { required: true })),
        q('short_text', 'Session or lesson'),
        ...[1, 2, 3, 4, 5, 6, 7, 8].map(n =>
          row(
            q('short_text', `Learner ${n}`, { key: `learner_${n}`, width: 7 }),
            q('dropdown', 'Status', { key: `status_${n}`, width: 5, options: scored(['Present', 1], ['Late', 1], ['Absent', 0]) }),
          ),
        ),
        row(
          q('calculated', 'Present', { key: 'present', formula: 'sum({status_1}, {status_2}, {status_3}, {status_4}, {status_5}, {status_6}, {status_7}, {status_8})' }),
          q('calculated', 'Attendance (%)', {
            key: 'attendance_rate',
            formula: 'round({present} / count({status_1}, {status_2}, {status_3}, {status_4}, {status_5}, {status_6}, {status_7}, {status_8}) * 100)',
          }),
        ),
        q('long_text', 'Notes'),
      ]),
    ],
  },
  {
    key: 'academic_survey',
    category: 'education',
    icon: 'i-lucide-clipboard-list',
    minutes: 5,
    name: 'Academic Survey',
    description: 'A short survey on study experience, support and wellbeing for students of any level.',
    tags: ['survey', 'students', 'wellbeing'],
    pages: [
      page('Your studies', [
        row(q('dropdown', 'Level', { options: opts('Secondary', 'Undergraduate', 'Postgraduate', 'Vocational', 'Other') }), q('short_text', 'Subject or programme')),
        q('matrix', 'How satisfied are you with…', {
          options: opts('Very unsatisfied', 'Unsatisfied', 'Satisfied', 'Very satisfied'),
          props: { rows: ['Teaching', 'Feedback on work', 'Library and resources', 'Online learning', 'Student support'] },
        }),
        q('scale', 'How manageable is your workload?', { props: { min: 1, max: 10, min_label: 'Too much', max_label: 'Very manageable' } }),
        q('radio', 'How would you describe your wellbeing this term?', { options: opts('Very good', 'Good', 'OK', 'Not good', 'Prefer not to say') }),
        q('long_text', 'One thing that would improve your experience'),
      ]),
    ],
  },
]
