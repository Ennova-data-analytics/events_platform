import ApiClient from './ApiClient';
import {
  mockApplications,
  mockDepartments,
  mockCycles,
  mockSlots,
  mockFunnel,
  timelineFor,
  nextId,
} from '@/data/recruitmentMock.js';

// ---------------------------------------------------------------------------
// Recruitment module service.
//
// This is the FRONT-END MOCKUP wiring. Every method is shaped like the real
// endpoint it will call (see recruitment-module-spec.md §6: public routes under
// /api/recruitment/*, protected under /api/hr/recruitment/*), but resolves
// against local mock data so the UI can be reviewed before the backend lands.
//
// To go live: set VITE_RECRUITMENT_LIVE=true in the frontend .env (the ApiClient
// calls are already written). Defaults to mock so the app runs standalone.
// ---------------------------------------------------------------------------
const USE_MOCK = import.meta.env.VITE_RECRUITMENT_LIVE !== 'true';

const delay = (ms = 350) => new Promise((r) => setTimeout(r, ms));
const clone = (v) => JSON.parse(JSON.stringify(v));

// Normalise backend field names (cycle_id / department_id) onto the frontend's
// `id` convention so flipping USE_MOCK doesn't ripple through the components.
const deptFromApi = (d) => (d ? { ...d, id: d.department_id ?? d.id } : d);
const cycleFromApi = (c) => ({
  ...c,
  id: c.cycle_id ?? c.id,
  cycle_departments: (c.cycle_departments || []).map((cd) => ({
    department_id: cd.department_id,
    is_open: cd.is_open,
    department: cd.department ? deptFromApi(cd.department) : null,
  })),
});

export const RecruitmentService = {
  // ── Public (candidate-facing) ───────────────────────────────────────────
  getOpenPositions() {
    if (USE_MOCK) return delay().then(() => clone(mockDepartments.filter((d) => d.is_active)));
    return ApiClient.get('/recruitment/positions').then((r) => r.data);
  },

  getActiveCycle() {
    if (USE_MOCK) return delay().then(() => clone(mockCycles.find((c) => c.is_active)));
    return ApiClient.get('/recruitment/cycles/active').then((r) => (r.data ? cycleFromApi(r.data) : null));
  },

  // Upload a document (CV / cover letter / material) — server proxies to S3.
  uploadDocument(file) {
    if (USE_MOCK) return delay(200).then(() => ({ s3_key: `recruitment/${file?.name || 'mock.pdf'}`, filename: file?.name }));
    const fd = new FormData();
    fd.append('file', file);
    return ApiClient.post('/recruitment/uploads', fd, { headers: { 'Content-Type': 'multipart/form-data' } }).then((r) => r.data);
  },

  // Best-effort CV parse to prefill the form (spec §3.7). No server endpoint in
  // v1 — prefill is optional, so this is a graceful no-op when live.
  parseCv() {
    return delay(USE_MOCK ? 900 : 0).then(() => ({ full_name: '', email: '', links: {}, flags: [] }));
  },

  // In-flow AI recommendation shown to the candidate during the application
  // (a lightweight preview of the same matching model HR sees on submit).
  // Returns the fit for the chosen department plus a ranked list; the UI only
  // surfaces a second recommendation when its score clears 60%.
  previewMatch(answers) {
    if (USE_MOCK) {
      return delay(1100).then(() => {
        const chosen = mockDepartments.find((d) => d.id === answers.department_applied_id) || mockDepartments[0];
        const text = `${answers.background || ''} ${answers.motivation || ''} ${answers.degree || ''}`.toLowerCase();
        // Pseudo-random-but-stable per department so the demo shows variety.
        const scored = mockDepartments
          .filter((d) => d.is_active)
          .map((d) => {
            const hits = d.skills_sought.filter((s) => text.includes(s.toLowerCase().split(' ')[0])).length;
            const base = 0.55 + ((d.id * 7) % 40) / 100; // 0.55–0.94 spread
            const score = Math.min(0.96, base + hits * 0.05 + (d.id === chosen.id ? 0.06 : 0));
            return { department_id: d.id, department: clone(d), score: Number(score.toFixed(2)) };
          })
          .sort((a, b) => b.score - a.score);

        const chosenEntry = scored.find((s) => s.department_id === chosen.id);
        const top = scored[0];
        const second = scored[1] && scored[1].score > 0.6 ? scored[1] : null;
        return {
          chosen_department_id: chosen.id,
          chosen_score: chosenEntry.score,
          ranked: scored,
          top,
          second, // null unless it clears 60%
          agrees_with_choice: top.department_id === chosen.id,
        };
      });
    }
    return ApiClient.post('/recruitment/match/preview', answers).then((r) => r.data);
  },

  // `form` is the stepper's form value plus `cv_file` (the File objects live on
  // it: cv_file, cover_letter, materials[].file). In live mode we upload the
  // files first, then submit the application with the returned S3 keys.
  async submitApplication(form) {
    if (USE_MOCK) {
      return delay(700).then(() => {
        const existing = mockApplications.find((a) => a.candidate.email === form.email);
        if (existing) return { already_applied: true, status_token: `mock-token-${existing.id}` };
        const id = nextId();
        return { already_applied: false, application_id: id, status_token: `mock-token-${id}` };
      });
    }

    // Upload documents (best-effort ordering; all before submit).
    const cvUpload = form.cv_file ? await this.uploadDocument(form.cv_file) : null;
    const coverUpload = form.cover_letter ? await this.uploadDocument(form.cover_letter) : null;
    const materials = [];
    for (const m of form.materials || []) {
      if (m.file) {
        const up = await this.uploadDocument(m.file);
        materials.push({ s3_key: up.s3_key, filename: up.filename, note: m.note || '' });
      }
    }

    const payload = {
      full_name: form.full_name,
      email: form.email,
      phone: form.phone || null,
      degree: form.degree || null,
      year: form.year || null,
      links: form.links || {},
      department_applied_id: form.department_applied_id,
      department_ranking: form.department_ranking?.length ? form.department_ranking : [form.department_applied_id],
      answers: {
        custom_answers: form.custom_answers || {},
        other_associations: form.other_associations || '',
        other_departments: form.applying_other_departments ? (form.other_departments || []) : [],
        links: form.links_list || [],
      },
      source: form.source || null,
      cv_s3_key: cvUpload?.s3_key || null,
      cover_letter_s3_key: coverUpload?.s3_key || null,
      materials,
      gdpr_consent: !!form.gdpr_consent,
      talent_pool_consent: !!form.talent_pool_consent,
    };
    return ApiClient.post('/recruitment/applications', payload).then((r) => r.data);
  },

  // Magic-link candidate status page (spec §3.6).
  getStatusByToken(token) {
    if (USE_MOCK) {
      return delay().then(() => {
        const id = Number(String(token).replace('mock-token-', '')) || 3;
        return clone({ ...(mockApplications.find((a) => a.id === id) || mockApplications[2]), timeline: timelineFor(id) });
      });
    }
    return ApiClient.get(`/recruitment/status/${token}`).then((r) => r.data);
  },

  // Magic-link slot booking (spec §3.5).
  getBookableSlotsByToken(token) {
    if (USE_MOCK) return delay().then(() => clone(mockSlots.filter((s) => !s.booked_application_id)));
    return ApiClient.get(`/recruitment/book/${token}/slots`).then((r) => r.data);
  },

  bookSlot(token, slotId) {
    if (USE_MOCK) {
      return delay(500).then(() => {
        const slot = mockSlots.find((s) => s.id === slotId);
        if (!slot || slot.booked_application_id) {
          const err = new Error('slot_taken');
          err.code = 'slot_taken';
          throw err;
        }
        return { booked: true, slot: clone(slot) };
      });
    }
    return ApiClient.post(`/recruitment/book/${token}`, { slot_id: slotId }).then((r) => r.data);
  },

  // ── HR (protected) ──────────────────────────────────────────────────────
  getApplications(params = {}) {
    if (USE_MOCK) {
      return delay().then(() => {
        let items = clone(mockApplications);
        if (params.cycle_id) items = items.filter((a) => a.cycle_id === params.cycle_id);
        if (params.department_id) {
          items = items.filter(
            (a) => a.final_department_id === params.department_id || a.suggested_department_id === params.department_id
          );
        }
        if (params.search) {
          const q = params.search.toLowerCase();
          items = items.filter(
            (a) => a.candidate.full_name.toLowerCase().includes(q) || a.candidate.email.toLowerCase().includes(q)
          );
        }
        return items;
      });
    }
    return ApiClient.get('/hr/recruitment/applications', { params }).then((r) => r.data);
  },

  getApplication(id) {
    if (USE_MOCK) {
      return delay().then(() => {
        const app = mockApplications.find((a) => a.id === Number(id));
        return clone({ ...app, timeline: timelineFor(Number(id)) });
      });
    }
    return ApiClient.get(`/hr/recruitment/applications/${id}`).then((r) => r.data);
  },

  updateStatus(id, status) {
    if (USE_MOCK) {
      return delay(200).then(() => {
        const app = mockApplications.find((a) => a.id === Number(id));
        if (app) app.status = status;
        return { id: Number(id), status };
      });
    }
    return ApiClient.patch(`/hr/recruitment/applications/${id}/status`, { status }).then((r) => r.data);
  },

  // Confirm or override the AI-suggested department (spec §3.2).
  setFinalDepartment(id, departmentId) {
    if (USE_MOCK) {
      return delay(200).then(() => {
        const app = mockApplications.find((a) => a.id === Number(id));
        if (app) {
          app.final_department_id = departmentId;
          app.final_department = mockDepartments.find((d) => d.id === departmentId) || null;
        }
        return { id: Number(id), final_department_id: departmentId };
      });
    }
    return ApiClient.patch(`/hr/recruitment/applications/${id}/department`, { department_id: departmentId }).then((r) => r.data);
  },

  addNote(id, text) {
    if (USE_MOCK) return delay(200).then(() => ({ id: Number(id), text }));
    return ApiClient.post(`/hr/recruitment/applications/${id}/notes`, { text }).then((r) => r.data);
  },

  // Per-department Calendly link. This is the booking URL that gets embedded in
  // the interview invitation email when a candidate is moved to Interview.
  updateDepartmentCalendly(departmentId, url) {
    if (USE_MOCK) {
      return delay(200).then(() => {
        const d = mockDepartments.find((x) => x.id === departmentId);
        if (d) d.calendly_link = url;
        return { id: departmentId, calendly_link: url };
      });
    }
    return ApiClient.put(`/hr/recruitment/departments/${departmentId}/calendly`, { calendly_link: url }).then((r) => r.data);
  },

  // Admin-configurable scoring rubric used to rank/score applicants. Varies a
  // lot per department, so it's owned by each department's reviewers.
  updateDepartmentCriteria(departmentId, criteria) {
    if (USE_MOCK) {
      return delay(200).then(() => {
        const d = mockDepartments.find((x) => x.id === departmentId);
        if (d) d.scoring_criteria = criteria;
        return { id: departmentId, scoring_criteria: criteria };
      });
    }
    return ApiClient.put(`/hr/recruitment/departments/${departmentId}/criteria`, { scoring_criteria: criteria }).then((r) => r.data);
  },

  // Admin-configurable extra application questions for a department.
  updateDepartmentQuestions(departmentId, questions) {
    if (USE_MOCK) {
      return delay(200).then(() => {
        const d = mockDepartments.find((x) => x.id === departmentId);
        if (d) d.custom_questions = questions;
        return { id: departmentId, custom_questions: questions };
      });
    }
    return ApiClient.put(`/hr/recruitment/departments/${departmentId}/questions`, { custom_questions: questions }).then((r) => r.data);
  },

  // Selective interview email: HR decides WHEN the interview invite (with the
  // department's Calendly link) is sent, rather than it firing automatically on
  // the status change. Returns the updated flag.
  sendInterviewInvite(id, { calendly_link } = {}) {
    if (USE_MOCK) {
      return delay(300).then(() => {
        const app = mockApplications.find((a) => a.id === Number(id));
        if (app) app.interview_invite_sent = true;
        return { id: Number(id), interview_invite_sent: true, calendly_link };
      });
    }
    return ApiClient.post(`/hr/recruitment/applications/${id}/send-interview-invite`, { calendly_link }).then((r) => r.data);
  },

  // Marketing detour: send the case brief with a 48h deadline instead of an
  // interview link. Moves the application into `case_sent`.
  sendMarketingCase(id, { brief_url, hours = 48 } = {}) {
    if (USE_MOCK) {
      return delay(300).then(() => {
        const app = mockApplications.find((a) => a.id === Number(id));
        const now = new Date();
        const deadline = new Date(now.getTime() + hours * 3600 * 1000);
        if (app) {
          app.status = 'case_sent';
          app.case = { brief_url, sent_at: now.toISOString(), deadline_at: deadline.toISOString(), submitted_at: null };
        }
        return { id: Number(id), status: 'case_sent', case: app?.case };
      });
    }
    return ApiClient.post(`/hr/recruitment/applications/${id}/send-case`, { brief_url, hours }).then((r) => r.data);
  },

  getCvPreviewUrl(id) {
    if (USE_MOCK) return delay(150).then(() => '#mock-cv');
    return ApiClient.get(`/hr/recruitment/applications/${id}/cv`).then((r) => r.data.url);
  },

  // Availability slots (spec §3.5).
  getSlots() {
    if (USE_MOCK) return delay().then(() => clone(mockSlots));
    return ApiClient.get('/hr/recruitment/slots').then((r) => r.data);
  },

  createSlot(payload) {
    if (USE_MOCK) {
      return delay(250).then(() => {
        const dep = mockDepartments.find((d) => d.id === payload.department_id) || null;
        const slot = { id: nextId(), booked_application_id: null, department: dep, ...payload };
        mockSlots.push(slot);
        return clone(slot);
      });
    }
    return ApiClient.post('/hr/recruitment/slots', payload).then((r) => r.data);
  },

  deleteSlot(id) {
    if (USE_MOCK) {
      return delay(150).then(() => {
        const i = mockSlots.findIndex((s) => s.id === id);
        if (i >= 0) mockSlots.splice(i, 1);
        return { deleted: true };
      });
    }
    return ApiClient.delete(`/hr/recruitment/slots/${id}`).then((r) => r.data);
  },

  getFunnel(cycleId) {
    if (USE_MOCK) return delay().then(() => clone(mockFunnel[cycleId] || mockFunnel[1]));
    return ApiClient.get('/hr/recruitment/analytics/funnel', { params: { cycle_id: cycleId } }).then((r) => r.data);
  },

  getCycles() {
    if (USE_MOCK) return delay(150).then(() => clone(mockCycles));
    return ApiClient.get('/hr/recruitment/cycles').then((r) => r.data.map(cycleFromApi));
  },

  // ── Cohort setup (super-admin) ──────────────────────────────────────────
  createCycle(payload) {
    if (USE_MOCK) {
      return delay(300).then(() => {
        const cycle = {
          id: nextId(),
          name: payload.name,
          opens_at: payload.opens_at || null,
          closes_at: payload.closes_at || null,
          is_active: false,
          cycle_departments: (payload.departments || []).map((d) => ({
            department_id: d.department_id,
            is_open: d.is_open,
            department: mockDepartments.find((x) => x.id === d.department_id) || null,
          })),
        };
        mockCycles.push(cycle);
        return clone(cycle);
      });
    }
    return ApiClient.post('/hr/recruitment/cycles', payload).then((r) => cycleFromApi(r.data));
  },

  updateCycle(id, payload) {
    if (USE_MOCK) {
      return delay(250).then(() => {
        const cycle = mockCycles.find((c) => c.id === id);
        if (!cycle) return null;
        if (payload.name != null) cycle.name = payload.name;
        if (payload.opens_at !== undefined) cycle.opens_at = payload.opens_at;
        if (payload.closes_at !== undefined) cycle.closes_at = payload.closes_at;
        if (payload.is_active != null) {
          if (payload.is_active) mockCycles.forEach((c) => { c.is_active = false; });
          cycle.is_active = payload.is_active;
        }
        if (payload.departments) {
          cycle.cycle_departments = payload.departments.map((d) => ({
            department_id: d.department_id,
            is_open: d.is_open,
            department: mockDepartments.find((x) => x.id === d.department_id) || null,
          }));
        }
        return clone(cycle);
      });
    }
    return ApiClient.patch(`/hr/recruitment/cycles/${id}`, payload).then((r) => cycleFromApi(r.data));
  },

  activateCycle(id) {
    if (USE_MOCK) {
      return delay(200).then(() => {
        mockCycles.forEach((c) => { c.is_active = c.id === id; });
        return clone(mockCycles.find((c) => c.id === id));
      });
    }
    return ApiClient.post(`/hr/recruitment/cycles/${id}/activate`).then((r) => cycleFromApi(r.data));
  },

  deleteCycle(id) {
    if (USE_MOCK) {
      return delay(150).then(() => {
        const i = mockCycles.findIndex((c) => c.id === id);
        if (i >= 0) mockCycles.splice(i, 1);
        return { deleted: true };
      });
    }
    return ApiClient.delete(`/hr/recruitment/cycles/${id}`).then((r) => r.data);
  },

  // ── Department catalog (HR) ─────────────────────────────────────────────
  getHrDepartments() {
    if (USE_MOCK) return delay(150).then(() => clone(mockDepartments));
    return ApiClient.get('/hr/recruitment/departments').then((r) => r.data.map(deptFromApi));
  },

  createDepartment(payload) {
    if (USE_MOCK) {
      return delay(250).then(() => {
        const dep = {
          id: nextId(),
          is_active: true,
          has_case_stage: false,
          skills_sought: [],
          scoring_criteria: [],
          custom_questions: [],
          calendly_link: '',
          ...payload,
        };
        mockDepartments.push(dep);
        return clone(dep);
      });
    }
    return ApiClient.post('/hr/recruitment/departments', payload).then((r) => deptFromApi(r.data));
  },

  updateDepartment(id, payload) {
    if (USE_MOCK) {
      return delay(200).then(() => {
        const dep = mockDepartments.find((d) => d.id === id);
        if (dep) Object.assign(dep, payload);
        return clone(dep);
      });
    }
    return ApiClient.patch(`/hr/recruitment/departments/${id}`, payload).then((r) => deptFromApi(r.data));
  },

  // ── Recruiter → department assignment (super-admin) ─────────────────────
  getRecruiterDepartments(userId) {
    if (USE_MOCK) return delay(120).then(() => []);
    return ApiClient.get(`/hr/recruitment/recruiters/${userId}/departments`).then((r) => r.data);
  },

  setRecruiterDepartments(userId, departmentIds) {
    if (USE_MOCK) return delay(150).then(() => departmentIds);
    return ApiClient.put(`/hr/recruitment/recruiters/${userId}/departments`, { department_ids: departmentIds }).then((r) => r.data);
  },
};

export default RecruitmentService;
