// Mock data for the Recruitment module front-end mockup.
// Mirrors the data model in recruitment-module-spec.md so the UI can be built
// and reviewed before the backend endpoints exist. Swap RecruitmentService
// over to real API calls once /api/recruitment/* is live.

// ── Application statuses ───────────────────────────────────────────────────
// `case_sent` / `case_submitted` are the Marketing-only detour: after review a
// case brief is sent and the candidate submits within 48h (see the `case`
// object on marketing applications). They are hidden from non-marketing views.
export const APPLICATION_STATUSES = [
  { value: 'applied', title: 'Applied', color: 'blue-grey', icon: 'mdi-inbox-arrow-down' },
  { value: 'in_review', title: 'In Review', color: 'info', icon: 'mdi-file-search-outline' },
  { value: 'case_sent', title: 'Case Sent', color: 'deep-purple', icon: 'mdi-briefcase-clock-outline', marketing_only: true },
  { value: 'case_submitted', title: 'Case Submitted', color: 'indigo', icon: 'mdi-briefcase-check-outline', marketing_only: true },
  { value: 'interview', title: 'Interview', color: 'purple', icon: 'mdi-account-voice' },
  { value: 'decision', title: 'Decision', color: 'amber-darken-2', icon: 'mdi-scale-balance' },
  { value: 'accepted', title: 'Accepted', color: 'success', icon: 'mdi-check-decagram' },
  { value: 'rejected', title: 'Rejected', color: 'error', icon: 'mdi-close-circle-outline' },
  { value: 'withdrawn', title: 'Withdrawn', color: 'grey', icon: 'mdi-account-off-outline' },
];

export const statusMeta = (value) =>
  APPLICATION_STATUSES.find((s) => s.value === value) || APPLICATION_STATUSES[0];

// Status transitions that trigger an outcome email requiring extra care.
export const HIGH_STAKES_STATUSES = ['accepted', 'rejected'];

// Esade academic context (used in the application form selects).
export const ESADE_DEGREES = [
  'BBA - Business Administration',
  'BGLM - Global Leadership & Management',
  'GLE - Global Governance, Economics & Law',
  'Double Degree BBA + Law',
  'Bachelor in Business & Data Science',
  'MSc in Management (MiM)',
  'MSc in Finance',
  'MSc in International Management',
  'Other',
];
export const ESADE_YEARS = ['1st year', '2nd year', '3rd year', '4th year', 'Master', 'Exchange'];

export const mockCycles = [
  {
    id: 1,
    name: 'Autumn 2026 Intake',
    opens_at: '2026-09-01T00:00:00Z',
    closes_at: '2026-10-15T23:59:59Z',
    is_active: true,
    // Which departments recruit in this cohort (resolved to objects below).
    cycle_departments: [
      { department_id: 1, is_open: true },
      { department_id: 2, is_open: true },
      { department_id: 3, is_open: true },
      { department_id: 4, is_open: true },
      { department_id: 5, is_open: true },
    ],
  },
  {
    id: 2,
    name: 'Spring 2026 Intake',
    opens_at: '2026-01-15T00:00:00Z',
    closes_at: '2026-02-28T23:59:59Z',
    is_active: false,
    cycle_departments: [
      { department_id: 1, is_open: false },
      { department_id: 2, is_open: false },
      { department_id: 3, is_open: false },
    ],
  },
];

// `scoring_criteria` (rubric used to rank/score applicants - weights sum to 100)
// and `custom_questions` (extra application questions) are admin-configurable per
// department, since what each team looks for varies a lot. Editable in the admin
// "Criteria & questions" page.
export const mockDepartments = [
  {
    id: 1,
    name: 'Data Analytics',
    description: 'Turns messy operational data into decisions. Works across SQL, Python and BI tooling to build dashboards and models for partners.',
    skills_sought: ['SQL', 'Python', 'Power BI', 'Statistics', 'Storytelling'],
    is_active: true,
    has_case_stage: false,
    calendly_link: 'https://calendly.com/ennova-data/interview',
    scoring_criteria: [
      { id: 'technical', label: 'Technical skill (SQL/Python)', weight: 40 },
      { id: 'analytical', label: 'Analytical thinking', weight: 30 },
      { id: 'communication', label: 'Communication', weight: 20 },
      { id: 'motivation', label: 'Motivation', weight: 10 },
    ],
    custom_questions: [
      { id: 'da_tools', label: 'Which tools are you most comfortable with?', type: 'text', required: false },
    ],
  },
  {
    id: 2,
    name: 'Software Engineering',
    description: 'Builds and ships the products and internal platforms. Full-stack, cloud-native, ownership-driven.',
    skills_sought: ['TypeScript', 'Python', 'React/Vue', 'AWS', 'CI/CD'],
    is_active: true,
    has_case_stage: false,
    calendly_link: 'https://calendly.com/ennova-eng/interview',
    scoring_criteria: [
      { id: 'coding', label: 'Coding ability', weight: 45 },
      { id: 'problem', label: 'Problem solving', weight: 30 },
      { id: 'collab', label: 'Collaboration', weight: 15 },
      { id: 'motivation', label: 'Motivation', weight: 10 },
    ],
    custom_questions: [
      { id: 'se_stack', label: 'What have you built that you\'re proud of?', type: 'textarea', required: false },
    ],
  },
  {
    id: 3,
    name: 'Strategy & Consulting',
    description: 'Partner-facing problem solving. Structures ambiguous problems, runs stakeholder workshops, and drives change.',
    skills_sought: ['Structured thinking', 'Communication', 'Stakeholder mgmt', 'Modelling'],
    is_active: true,
    has_case_stage: false,
    calendly_link: 'https://calendly.com/ennova-strategy/interview',
    scoring_criteria: [
      { id: 'structure', label: 'Structured thinking', weight: 40 },
      { id: 'communication', label: 'Communication', weight: 30 },
      { id: 'business', label: 'Business sense', weight: 20 },
      { id: 'motivation', label: 'Motivation', weight: 10 },
    ],
    custom_questions: [],
  },
  {
    id: 4,
    name: 'Design & Research',
    description: 'Owns the end-to-end experience - user research, service design and UI. Balances desirability with feasibility.',
    skills_sought: ['User research', 'Figma', 'Prototyping', 'Systems thinking'],
    is_active: true,
    has_case_stage: false,
    calendly_link: 'https://calendly.com/ennova-design/interview',
    scoring_criteria: [
      { id: 'craft', label: 'Craft & visual quality', weight: 40 },
      { id: 'research', label: 'Research rigour', weight: 25 },
      { id: 'systems', label: 'Systems thinking', weight: 20 },
      { id: 'motivation', label: 'Motivation', weight: 15 },
    ],
    custom_questions: [
      { id: 'ds_portfolio', label: 'Link to your portfolio', type: 'text', required: false, recommended: true },
    ],
  },
  {
    id: 5,
    name: 'Marketing',
    description: 'Owns brand, content and growth. Runs campaigns across social, events and partnerships. Creative and data-aware.',
    skills_sought: ['Copywriting', 'Social', 'Design sense', 'Campaign analytics', 'Storytelling'],
    is_active: true,
    // Marketing adds a case study stage BEFORE the interview (spec: unique stage).
    // It still runs a live interview afterwards, so it also needs a Calendly link.
    has_case_stage: true,
    calendly_link: 'https://calendly.com/ennova-marketing/interview',
    scoring_criteria: [
      { id: 'creativity', label: 'Creativity', weight: 40 },
      { id: 'copy', label: 'Copywriting', weight: 25 },
      { id: 'data', label: 'Data-awareness', weight: 20 },
      { id: 'motivation', label: 'Motivation', weight: 15 },
    ],
    custom_questions: [
      { id: 'mk_time', label: 'Are you more of a morning or an afternoon person?', type: 'select', options: ['Morning', 'Afternoon', 'No preference'], required: false },
      { id: 'mk_campaign', label: 'Share a campaign (any brand) you admire and why', type: 'textarea', required: false },
    ],
  },
];

const departmentById = (id) => mockDepartments.find((d) => d.id === id) || null;

// Resolve each cohort's department memberships to full department objects.
mockCycles.forEach((c) => {
  (c.cycle_departments || []).forEach((cd) => { cd.department = departmentById(cd.department_id); });
});

let idSeq = 100;

// ── Candidates & applications ─────────────────────────────────────────────
export const mockApplications = [
  {
    id: 1,
    status: 'applied',
    cycle_id: 1,
    source: 'Class announcement',
    created_at: '2026-09-20T09:12:00Z',
    candidate: {
      full_name: 'Mara Ionescu',
      email: 'mara.ionescu@esade.edu',
      phone: '+40 721 000 111',
      degree: 'Bachelor in Business & Data Science',
      year: '3rd year',
      links: { linkedin: 'linkedin.com/in/maraionescu' },
      cv_s3_key: 'cv/mara-ionescu.pdf',
      gdpr_consent: true,
      gdpr_consent_at: '2026-09-20T09:12:00Z',
      talent_pool_consent: true,
    },
    answers: {
      department_applied_id: 1,
      background: 'Business & Data Science, focus on applied statistics. Two internships in market research.',
      motivation: 'I want to work where analytics actually changes a partner decision, not just produces a report.',
      other_departments: [3],
      other_associations: 'ESADE Consulting Club (member)',
      availability: 'Weekday afternoons',
      materials: [],
      links: [{ label: 'Kaggle profile', url: 'https://kaggle.com/maraionescu' }],
    },
    suggested_department_id: 1,
    match_confidence: 0.89,
    match_rationale: 'Strong statistics background and explicit interest in decision-driving analytics maps directly to Data Analytics.',
    final_department_id: null,
    interview_invite_sent: false,
  },
  {
    id: 2,
    status: 'in_review',
    cycle_id: 1,
    source: 'Referral',
    created_at: '2026-09-19T14:03:00Z',
    candidate: {
      full_name: 'David Okafor',
      email: 'david.okafor@esade.edu',
      phone: '+44 7700 900123',
      degree: 'BBA - Business Administration',
      year: '2nd year',
      links: { linkedin: 'linkedin.com/in/davidokafor', github: 'github.com/dokafor' },
      cv_s3_key: 'cv/david-okafor.pdf',
      gdpr_consent: true,
      gdpr_consent_at: '2026-09-19T14:03:00Z',
      talent_pool_consent: false,
    },
    answers: {
      department_applied_id: 2,
      background: 'BBA with a strong self-taught engineering side. Built two side projects at fintech hackathons.',
      motivation: 'Looking for more ownership and real product impact than coursework gives me.',
      other_departments: [],
      other_associations: '',
      availability: 'Flexible',
      materials: [{ filename: 'side-project-writeup.pdf', note: 'Architecture notes for my payments demo' }],
      links: [{ label: 'GitHub', url: 'https://github.com/dokafor' }],
    },
    suggested_department_id: 2,
    match_confidence: 0.94,
    match_rationale: 'Full-stack side projects and stated desire for ownership align cleanly with Software Engineering.',
    final_department_id: 2,
    interview_invite_sent: false,
  },
  {
    id: 3,
    status: 'interview',
    cycle_id: 1,
    source: 'Instagram',
    created_at: '2026-09-17T11:20:00Z',
    candidate: {
      full_name: 'Sofia Bergström',
      email: 'sofia.bergstrom@esade.edu',
      phone: '+46 70 123 45 67',
      degree: 'GLE - Global Governance, Economics & Law',
      year: '4th year',
      links: { linkedin: 'linkedin.com/in/sofiabergstrom', youtube: 'https://youtu.be/aqz-KE-bpKQ' },
      cv_s3_key: 'cv/sofia-bergstrom.pdf',
      gdpr_consent: true,
      gdpr_consent_at: '2026-09-17T11:20:00Z',
      talent_pool_consent: true,
    },
    answers: {
      department_applied_id: 4,
      background: 'Led design-system work for a student startup. Strong on research-led design.',
      motivation: 'I care about research-led design and want a team that ships.',
      other_departments: [5],
      other_associations: 'Emprèn (design lead)',
      availability: 'Mon/Wed/Fri',
      materials: [{ filename: 'portfolio-2026.pdf', note: 'Selected case studies' }],
      links: [{ label: 'Behance', url: 'https://behance.net/sofiab' }],
    },
    suggested_department_id: 4,
    match_confidence: 0.91,
    match_rationale: 'Design-system leadership and research emphasis are a direct fit for Design & Research.',
    final_department_id: 4,
    interview_invite_sent: true,
    interview: {
      starts_at: '2026-09-24T13:00:00Z',
      ends_at: '2026-09-24T13:45:00Z',
      interviewer: 'Elena Popescu',
      meeting_link: 'https://meet.ennova.com/sofia-b',
    },
  },
  {
    id: 4,
    status: 'interview',
    cycle_id: 1,
    source: 'Class announcement',
    created_at: '2026-09-16T16:45:00Z',
    candidate: {
      full_name: 'Tomasz Kowalski',
      email: 'tomasz.kowalski@esade.edu',
      phone: '+48 512 345 678',
      degree: 'BBA - Business Administration',
      year: '3rd year',
      links: { linkedin: 'linkedin.com/in/tkowalski', github: 'github.com/tkowalski' },
      cv_s3_key: null,
      gdpr_consent: true,
      gdpr_consent_at: '2026-09-16T16:45:00Z',
      talent_pool_consent: false,
    },
    answers: {
      department_applied_id: 1,
      background: 'Strong in data engineering side-projects. Comfortable across Python and SQL.',
      motivation: 'Want to grow fast in a partner-facing, data-driven environment.',
      other_departments: [2],
      other_associations: '',
      availability: 'Afternoons',
      materials: [],
      links: [],
    },
    suggested_department_id: null,
    match_confidence: null,
    match_rationale: null,
    final_department_id: 1,
    match_pending: true,
    match_flags: ['cv_unreadable'],
    interview_invite_sent: false,
  },
  {
    id: 5,
    status: 'decision',
    cycle_id: 1,
    source: 'Referral',
    created_at: '2026-09-14T08:30:00Z',
    candidate: {
      full_name: 'Amara Nwosu',
      email: 'amara.nwosu@esade.edu',
      phone: '+44 7700 900987',
      degree: 'MSc in Management (MiM)',
      year: 'Master',
      links: { linkedin: 'linkedin.com/in/amaranwosu' },
      cv_s3_key: 'cv/amara-nwosu.pdf',
      gdpr_consent: true,
      gdpr_consent_at: '2026-09-14T08:30:00Z',
      talent_pool_consent: true,
    },
    answers: {
      department_applied_id: 3,
      background: 'MiM with prior boutique consulting internship. Comfortable framing ambiguous problems.',
      motivation: 'Ennova\'s data-driven consulting is exactly the intersection I want.',
      other_departments: [1],
      other_associations: 'Net Impact Club',
      availability: 'Flexible',
      materials: [],
      links: [],
    },
    suggested_department_id: 3,
    match_confidence: 0.88,
    match_rationale: 'Consulting internship and stated fit make Strategy & Consulting the clear placement.',
    final_department_id: 3,
    interview_invite_sent: true,
  },
  {
    id: 6,
    status: 'accepted',
    cycle_id: 1,
    source: 'Instagram',
    created_at: '2026-09-10T10:00:00Z',
    candidate: {
      full_name: 'Liang Wei',
      email: 'liang.wei@esade.edu',
      phone: '+31 6 1234 5678',
      degree: 'Bachelor in Business & Data Science',
      year: '4th year',
      links: { linkedin: 'linkedin.com/in/liangwei', github: 'github.com/lwei' },
      cv_s3_key: 'cv/liang-wei.pdf',
      gdpr_consent: true,
      gdpr_consent_at: '2026-09-10T10:00:00Z',
      talent_pool_consent: true,
    },
    answers: {
      department_applied_id: 1,
      background: 'ML research plus solid engineering. Comfortable end-to-end.',
      motivation: 'I want applied impact over publications.',
      other_departments: [2],
      other_associations: '',
      availability: 'Immediately',
      materials: [],
      links: [{ label: 'GitHub', url: 'https://github.com/lwei' }],
    },
    suggested_department_id: 1,
    match_confidence: 0.82,
    match_rationale: 'ML research plus engineering leans Data Analytics, with Software Engineering as a close second.',
    final_department_id: 1,
    interview_invite_sent: true,
  },
  {
    id: 7,
    status: 'rejected',
    cycle_id: 1,
    source: 'Careers fair',
    created_at: '2026-09-08T13:15:00Z',
    candidate: {
      full_name: 'Ben Carter',
      email: 'ben.carter@esade.edu',
      phone: '+1 415 555 0142',
      degree: 'BBA - Business Administration',
      year: '1st year',
      links: { linkedin: 'linkedin.com/in/bencarter' },
      cv_s3_key: 'cv/ben-carter.pdf',
      gdpr_consent: true,
      gdpr_consent_at: '2026-09-08T13:15:00Z',
      talent_pool_consent: false,
    },
    answers: {
      department_applied_id: 1,
      background: 'First-year, exploring analytics. Limited hands-on experience so far.',
      motivation: 'Interested in learning a data career.',
      other_departments: [],
      other_associations: '',
      availability: 'Immediately',
      materials: [],
      links: [],
    },
    suggested_department_id: 1,
    match_confidence: 0.41,
    match_rationale: 'Interest is present but current skills are a weak match for the Data Analytics rubric.',
    final_department_id: null,
    interview_invite_sent: false,
  },
  // ── Marketing candidates (case-study pipeline) ──────────────────────────
  {
    id: 8,
    status: 'case_sent',
    cycle_id: 1,
    source: 'Instagram',
    created_at: '2026-09-18T18:30:00Z',
    candidate: {
      full_name: 'Núria Vidal',
      email: 'nuria.vidal@esade.edu',
      phone: '+34 600 111 222',
      degree: 'BGLM - Global Leadership & Management',
      year: '2nd year',
      links: { linkedin: 'linkedin.com/in/nuriavidal', instagram: '@nuria.creates' },
      cv_s3_key: 'cv/nuria-vidal.pdf',
      gdpr_consent: true,
      gdpr_consent_at: '2026-09-18T18:30:00Z',
      talent_pool_consent: true,
    },
    answers: {
      department_applied_id: 5,
      background: 'Runs a 12k-follower creative account. Comfortable with Reels, copy and light design.',
      motivation: 'I want to build campaigns that people actually screenshot and share.',
      other_departments: [4],
      department_ranking: [5, 4],
      other_associations: 'ESADE Media Club',
      availability: 'Evenings',
      materials: [{ filename: 'campaign-samples.pdf', note: 'Three campaigns I ran last year' }],
      links: [
        { label: 'Instagram', url: 'https://instagram.com/nuria.creates' },
        { label: 'Portfolio', url: 'https://nuria.design' },
      ],
      custom_answers: {
        mk_time: 'Afternoon',
        mk_campaign: 'Spotify Wrapped - it turns cold data into something people actually want to share.',
      },
    },
    suggested_department_id: 5,
    match_confidence: 0.9,
    match_rationale: 'Proven creative output and audience growth are a strong fit for Marketing.',
    final_department_id: 5,
    interview_invite_sent: false,
    // Marketing case study state (visuals only for now).
    case: {
      brief_url: 'https://ennova.com/cases/marketing-autumn26.pdf',
      sent_at: '2026-09-19T09:00:00Z',
      deadline_at: '2026-09-21T09:00:00Z',
      submitted_at: null,
    },
  },
  {
    id: 9,
    status: 'case_submitted',
    cycle_id: 1,
    source: 'Referral',
    created_at: '2026-09-15T12:00:00Z',
    candidate: {
      full_name: 'Marc Dubois',
      email: 'marc.dubois@esade.edu',
      phone: '+33 6 12 34 56 78',
      degree: 'BBA - Business Administration',
      year: '3rd year',
      links: { linkedin: 'linkedin.com/in/marcdubois' },
      cv_s3_key: 'cv/marc-dubois.pdf',
      gdpr_consent: true,
      gdpr_consent_at: '2026-09-15T12:00:00Z',
      talent_pool_consent: false,
    },
    answers: {
      department_applied_id: 5,
      background: 'Marketing intern at a DTC brand. Strong on campaign analytics and paid social.',
      motivation: 'I like the mix of creativity and numbers that Ennova marketing runs on.',
      other_departments: [3],
      other_associations: 'ESADE Consulting Club',
      availability: 'Flexible',
      materials: [{ filename: 'ennova-case-submission.pdf', note: 'My case response' }],
      links: [],
    },
    suggested_department_id: 5,
    match_confidence: 0.85,
    match_rationale: 'Analytics-heavy marketing background fits the Marketing rubric well.',
    final_department_id: 5,
    interview_invite_sent: false,
    case: {
      brief_url: 'https://ennova.com/cases/marketing-autumn26.pdf',
      sent_at: '2026-09-16T09:00:00Z',
      deadline_at: '2026-09-18T09:00:00Z',
      submitted_at: '2026-09-17T22:40:00Z',
      submission_url: 'https://ennova.com/submissions/marc-dubois.pdf',
    },
  },
];

// Attach resolved department objects for convenience in the UI.
mockApplications.forEach((a) => {
  a.suggested_department = departmentById(a.suggested_department_id);
  a.final_department = departmentById(a.final_department_id);
  a.applied_department = departmentById(a.answers.department_applied_id);
  a.other_departments = (a.answers.other_departments || []).map(departmentById).filter(Boolean);
  // Candidate's ranked preference across all departments they're applying to
  // (primary first, then any others). Visible to recruiters.
  const rankingIds = a.answers.department_ranking
    || [a.answers.department_applied_id, ...(a.answers.other_departments || [])];
  a.ranked_departments = rankingIds.map(departmentById).filter(Boolean);
});

// ── Application event timelines ───────────────────────────────────────────
export const mockTimelines = {
  1: [
    { type: 'status_change', payload: { to: 'applied' }, actor: 'system', created_at: '2026-09-20T09:12:00Z' },
    { type: 'email_sent', payload: { template: 'Application received' }, actor: 'system', created_at: '2026-09-20T09:12:05Z' },
    { type: 'ai_match', payload: { department: 'Data Analytics', confidence: 0.89 }, actor: 'ai', created_at: '2026-09-20T09:13:10Z' },
  ],
  2: [
    { type: 'status_change', payload: { to: 'applied' }, actor: 'system', created_at: '2026-09-19T14:03:00Z' },
    { type: 'email_sent', payload: { template: 'Application received' }, actor: 'system', created_at: '2026-09-19T14:03:04Z' },
    { type: 'ai_match', payload: { department: 'Software Engineering', confidence: 0.94 }, actor: 'ai', created_at: '2026-09-19T14:04:00Z' },
    { type: 'override', payload: { department: 'Software Engineering' }, actor: 'Elena Popescu', created_at: '2026-09-19T15:20:00Z' },
    { type: 'status_change', payload: { to: 'in_review' }, actor: 'Elena Popescu', created_at: '2026-09-19T15:21:00Z' },
    { type: 'note', payload: { text: 'Strong side projects. Consider fast-track to interview.' }, actor: 'Elena Popescu', created_at: '2026-09-19T15:25:00Z' },
  ],
  3: [
    { type: 'status_change', payload: { to: 'applied' }, actor: 'system', created_at: '2026-09-17T11:20:00Z' },
    { type: 'ai_match', payload: { department: 'Design & Research', confidence: 0.91 }, actor: 'ai', created_at: '2026-09-17T11:21:00Z' },
    { type: 'status_change', payload: { to: 'in_review' }, actor: 'Marco Rossi', created_at: '2026-09-18T09:00:00Z' },
    { type: 'status_change', payload: { to: 'interview' }, actor: 'Marco Rossi', created_at: '2026-09-21T10:00:00Z' },
    { type: 'email_sent', payload: { template: 'Interview invitation (Calendly)' }, actor: 'Marco Rossi', created_at: '2026-09-21T10:00:05Z' },
    { type: 'email_sent', payload: { template: 'Booking confirmation (.ics)' }, actor: 'system', created_at: '2026-09-21T12:30:00Z' },
  ],
  8: [
    { type: 'status_change', payload: { to: 'applied' }, actor: 'system', created_at: '2026-09-18T18:30:00Z' },
    { type: 'ai_match', payload: { department: 'Marketing', confidence: 0.9 }, actor: 'ai', created_at: '2026-09-18T18:31:00Z' },
    { type: 'status_change', payload: { to: 'in_review' }, actor: 'Júlia Serra', created_at: '2026-09-19T08:45:00Z' },
    { type: 'status_change', payload: { to: 'case_sent' }, actor: 'Júlia Serra', created_at: '2026-09-19T09:00:00Z' },
    { type: 'email_sent', payload: { template: 'Marketing case brief (48h)' }, actor: 'Júlia Serra', created_at: '2026-09-19T09:00:05Z' },
  ],
  9: [
    { type: 'status_change', payload: { to: 'applied' }, actor: 'system', created_at: '2026-09-15T12:00:00Z' },
    { type: 'ai_match', payload: { department: 'Marketing', confidence: 0.85 }, actor: 'ai', created_at: '2026-09-15T12:01:00Z' },
    { type: 'status_change', payload: { to: 'case_sent' }, actor: 'Júlia Serra', created_at: '2026-09-16T09:00:00Z' },
    { type: 'email_sent', payload: { template: 'Marketing case brief (48h)' }, actor: 'Júlia Serra', created_at: '2026-09-16T09:00:05Z' },
    { type: 'status_change', payload: { to: 'case_submitted' }, actor: 'system', created_at: '2026-09-17T22:40:00Z' },
  ],
};

export const timelineFor = (id) => mockTimelines[id] || [
  { type: 'status_change', payload: { to: 'applied' }, actor: 'system', created_at: '2026-09-15T09:00:00Z' },
];

// ── Availability slots ────────────────────────────────────────────────────
export const mockSlots = [
  { id: 1, interviewer: 'Elena Popescu', department_id: 1, starts_at: '2026-09-24T09:00:00Z', ends_at: '2026-09-24T09:45:00Z', booked_application_id: null },
  { id: 2, interviewer: 'Elena Popescu', department_id: 1, starts_at: '2026-09-24T10:00:00Z', ends_at: '2026-09-24T10:45:00Z', booked_application_id: null },
  { id: 3, interviewer: 'Marco Rossi', department_id: 4, starts_at: '2026-09-24T13:00:00Z', ends_at: '2026-09-24T13:45:00Z', booked_application_id: 3 },
  { id: 4, interviewer: 'Marco Rossi', department_id: null, starts_at: '2026-09-25T11:00:00Z', ends_at: '2026-09-25T11:45:00Z', booked_application_id: null },
  { id: 5, interviewer: 'Priya Sharma', department_id: 2, starts_at: '2026-09-25T14:00:00Z', ends_at: '2026-09-25T14:45:00Z', booked_application_id: null },
];

mockSlots.forEach((s) => { s.department = departmentById(s.department_id); });

// ── Analytics (per cycle) ─────────────────────────────────────────────────
export const mockFunnel = {
  1: {
    overall: { applied: 58, in_review: 37, interview: 18, offered: 11, accepted: 7 },
    // Median days a candidate spends in each stage before moving on.
    time_in_stage_days: { applied: 1.4, in_review: 2.8, interview: 3.1, decision: 1.9 },
    avg_days_to_decision: 9.2,
    by_department: [
      { department: 'Data Analytics', applied: 16, interview: 6, offered: 3, accepted: 2 },
      { department: 'Software Engineering', applied: 13, interview: 5, offered: 3, accepted: 2 },
      { department: 'Strategy & Consulting', applied: 10, interview: 3, offered: 2, accepted: 1 },
      { department: 'Design & Research', applied: 7, interview: 2, offered: 1, accepted: 1 },
      { department: 'Marketing', applied: 12, interview: 2, offered: 2, accepted: 1 },
    ],
    sources: [
      { source: 'Class announcement', count: 18 },
      { source: 'Instagram', count: 15 },
      { source: 'Referral', count: 12 },
      { source: 'Careers fair', count: 8 },
      { source: 'Other', count: 5 },
    ],
    by_year: [
      { year: '1st year', count: 9 },
      { year: '2nd year', count: 17 },
      { year: '3rd year', count: 19 },
      { year: '4th year', count: 8 },
      { year: 'Master', count: 5 },
    ],
    // How often HR overrode the AI department suggestion - matching quality signal.
    ai_match: { confirmed: 41, overridden: 9, pending: 8 },
  },
};

export const nextId = () => ++idSeq;
