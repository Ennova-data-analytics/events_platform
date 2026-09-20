<template>
  <v-container class="py-8">
    <v-row justify="center">
      <v-col cols="12" md="8" lg="7">

        <v-card v-if="isLoading" class="pa-8 text-center">
          <v-progress-circular indeterminate color="primary" size="64" />
        </v-card>

        <template v-else-if="application">
          <!-- Brand strip -->
          <div class="d-flex align-center mb-4">
            <v-avatar color="primary" size="34" class="mr-2">
              <span class="text-body-2 font-weight-bold">E</span>
            </v-avatar>
            <span class="text-subtitle-1 font-weight-bold">Ennova</span>
            <span class="text-caption text-medium-emphasis ml-2">Recruitment</span>
          </div>

          <!-- Header hero -->
          <v-card class="mb-4 status-hero" :style="heroStyle">
            <v-card-text class="pa-4 pa-sm-6">
              <div class="d-flex align-center justify-space-between flex-wrap ga-3">
                <div>
                  <div class="text-overline text-medium-emphasis">
                    {{ isMultiApplication ? 'Your applications' : 'Your application' }}
                  </div>
                  <h1 class="text-h6 text-sm-h5 font-weight-bold">{{ application.candidate.full_name }}</h1>
                  <div class="text-body-2 text-medium-emphasis d-flex align-center flex-wrap ga-1">
                    <v-icon size="x-small">mdi-account-tie-outline</v-icon>
                    <!-- With several applications a single department name here
                         is misleading, so name them all. -->
                    {{ isMultiApplication ? allDepartmentNames : (appliedDepartment?.name || 'Team to be confirmed') }}
                    <span class="mx-1">·</span>
                    <span>Ref {{ reference }}</span>
                  </div>
                </div>
                <v-chip v-if="!isMultiApplication" :color="meta.color" variant="flat" size="large">
                  <v-icon start :icon="meta.icon" />
                  {{ meta.title }}
                </v-chip>
              </div>
              <div class="text-caption text-medium-emphasis mt-3">
                Submitted {{ formatDate(application.created_at) }} · {{ cycleName }}
              </div>
            </v-card-text>
          </v-card>

          <!-- Current status narrative. Per-application when there are
               several, so it isn't narrating one team's stage as if it were
               the whole picture. -->
          <v-card v-if="!isMultiApplication" class="mb-4" :color="narrative.tone" variant="tonal">
            <v-card-text class="pa-4 pa-sm-5 d-flex ga-3 ga-sm-4">
              <v-icon :icon="narrative.icon" size="32" class="mt-1" />
              <div>
                <div class="text-subtitle-1 font-weight-bold mb-1">{{ narrative.title }}</div>
                <p class="text-body-2 mb-0">{{ narrative.body }}</p>
                <p v-if="narrative.hint" class="text-caption text-medium-emphasis mt-2 mb-0">{{ narrative.hint }}</p>
              </div>
            </v-card-text>
          </v-card>

          <!-- One self-contained card per department: its own stage, its own
               narrative and its own actions. The single set of action cards
               below is driven by whichever application holds the token, so a
               candidate at Interview with two teams saw one booking button and
               could only book one of them. -->
          <template v-if="isMultiApplication">
            <v-card v-for="a in application.applications" :key="a.id" class="mb-4" variant="outlined">
              <v-card-text class="pa-4 pa-sm-5">
                <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-2">
                  <div class="d-flex align-center ga-2">
                    <v-icon :icon="cardMeta(a).icon" :color="cardMeta(a).color" />
                    <span class="text-subtitle-1 font-weight-bold">{{ a.department?.name || 'Department' }}</span>
                  </div>
                  <v-chip :color="cardMeta(a).color" variant="tonal" size="small">
                    {{ cardMeta(a).title }}
                  </v-chip>
                </div>
                <p class="text-body-2 text-medium-emphasis mb-3">
                  {{ a.locked
                    ? `Closed because you accepted your offer from ${a.locked.by_department || 'another team'}. This team has been told.`
                    : narrativeFor(a.status).body }}
                </p>

                <!-- Compact per-department progress. The full timeline below is
                     hidden for multi-department applicants, since one stepper
                     can only ever describe one of their applications. -->
                <div class="d-flex align-center flex-wrap ga-1">
                  <template v-for="(st, i) in stagesFor(a)" :key="st.value">
                    <v-icon v-if="i > 0" size="x-small" color="grey-lighten-1">mdi-chevron-right</v-icon>
                    <span
                      class="text-caption"
                      :class="st.current
                        ? 'font-weight-bold text-primary'
                        : (st.reached ? 'text-medium-emphasis' : 'text-disabled')"
                    >
                      {{ st.label }}
                    </span>
                  </template>
                </div>

                <!-- Offer from this department -->
                <template v-if="a.status === 'offered' && !a.locked">
                  <v-divider class="my-3" />
                  <OfferActions
                    :offer="a.offer"
                    :department-name="a.department?.name"
                    :other-open-count="openOthers(a).length"
                    @respond="openOfferDialog(a, $event)"
                  />
                </template>

                <!-- Case study for this department -->
                <template v-if="a.case && !a.case.submitted_at && !a.locked">
                  <v-divider class="my-3" />
                  <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-2">
                    <span class="text-subtitle-2 font-weight-bold">Case study</span>
                    <v-chip :color="isOverdue(a.case) ? 'error' : 'deep-purple'" variant="tonal" size="small">
                      {{ isOverdue(a.case) ? 'Deadline passed' : countdownFor(a.case) + ' left' }}
                    </v-chip>
                  </div>
                  <p class="text-body-2 text-medium-emphasis mb-3">Due {{ formatDateTime(a.case.deadline_at) }}.</p>
                  <div class="d-flex ga-2 flex-wrap">
                    <v-btn v-if="a.case.brief_url" :href="a.case.brief_url" target="_blank" color="deep-purple" variant="flat" size="small" prepend-icon="mdi-download">
                      Download brief
                    </v-btn>
                    <v-btn variant="outlined" size="small" prepend-icon="mdi-upload" @click="openSubmitDialog(a)">
                      Submit response
                    </v-btn>
                  </div>
                </template>
                <template v-else-if="a.case?.submitted_at">
                  <v-divider class="my-3" />
                  <div class="d-flex align-center ga-2">
                    <v-icon color="success" size="small">mdi-briefcase-check-outline</v-icon>
                    <span class="text-body-2 text-medium-emphasis">
                      Case submitted {{ formatDateTime(a.case.submitted_at) }}
                    </span>
                  </div>
                </template>

                <!-- Interview for this department -->
                <template v-if="a.interview && !a.locked">
                  <v-divider class="my-3" />
                  <div class="d-flex align-center ga-2">
                    <v-icon color="purple" size="small">mdi-calendar-check</v-icon>
                    <span class="text-body-2">Interview booked for {{ formatDateTime(a.interview.starts_at) }}</span>
                  </div>
                  <v-btn v-if="a.interview.meeting_link" :href="a.interview.meeting_link" target="_blank" size="small" variant="text" color="primary" prepend-icon="mdi-video" class="mt-2">
                    Join the call
                  </v-btn>
                </template>
                <template v-else-if="a.status === 'interview' && !a.locked">
                  <v-divider class="my-3" />
                  <v-btn
                    v-if="a.department?.calendly_link"
                    :href="a.department.calendly_link"
                    target="_blank"
                    color="primary"
                    variant="flat"
                    size="small"
                    prepend-icon="mdi-calendar-account"
                  >
                    Book my {{ a.department.name }} interview
                  </v-btn>
                  <p v-else class="text-body-2 text-medium-emphasis mb-0">
                    We'll email you shortly to arrange a time for this one.
                  </p>
                </template>
              </v-card-text>
            </v-card>
          </template>

          <!-- ── Action cards ──────────────────────────────────────────── -->

          <!-- Offer awaiting an answer (single application; with several, it
               sits on that department's card above) -->
          <v-card v-if="!isMultiApplication && application.status === 'offered'" class="mb-4" variant="outlined">
            <v-card-text class="pa-4 pa-sm-5">
              <OfferActions
                :offer="application.offer"
                :department-name="appliedDepartment?.name"
                @respond="openOfferDialog(apps[0], $event)"
              />
            </v-card-text>
          </v-card>

          <!-- Marketing case: brief + deadline -->
          <v-card v-if="!isMultiApplication && application.case && !application.case.submitted_at" class="mb-4" variant="outlined">
            <v-card-text class="pa-4 pa-sm-5">
              <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-2">
                <div class="d-flex align-center">
                  <v-icon color="deep-purple" class="mr-2">mdi-briefcase-clock-outline</v-icon>
                  <span class="text-subtitle-2 font-weight-bold">Your case study</span>
                </div>
                <v-chip :color="caseOverdue ? 'error' : 'deep-purple'" variant="tonal" size="small">
                  <v-icon start size="x-small">mdi-clock-outline</v-icon>
                  {{ caseOverdue ? 'Deadline passed' : caseCountdown + ' left' }}
                </v-chip>
              </div>
              <p class="text-body-2 text-medium-emphasis mb-3">
                Download the brief and submit your response before {{ formatDateTime(application.case.deadline_at) }}.
              </p>
              <div class="d-flex ga-2 flex-wrap">
                <v-btn :href="application.case.brief_url" target="_blank" color="deep-purple" variant="flat" size="small" prepend-icon="mdi-download">
                  Download brief
                </v-btn>
                <v-btn variant="outlined" size="small" prepend-icon="mdi-upload" @click="submitDialog = true">
                  Submit response
                </v-btn>
              </div>
            </v-card-text>
          </v-card>

          <!-- Confirmation once they've submitted -->
          <v-card v-else-if="!isMultiApplication && application.case?.submitted_at" class="mb-4" variant="outlined">
            <v-card-text class="pa-4 pa-sm-5">
              <div class="d-flex align-center mb-2">
                <v-icon color="success" class="mr-2">mdi-briefcase-check-outline</v-icon>
                <span class="text-subtitle-2 font-weight-bold">Case study submitted</span>
              </div>
              <p class="text-body-2 text-medium-emphasis mb-0">
                Received {{ formatDateTime(application.case.submitted_at) }}<span
                  v-if="application.case.submission_filename"
                > · {{ application.case.submission_filename }}</span>. The team will review it and be in touch.
              </p>
            </v-card-text>
          </v-card>

          <!-- Submit response -->
          <!-- Accept / decline an offer. Accepting spells out what it closes. -->
          <v-dialog v-model="offerDialog" :max-width="$vuetify.display.mobile ? '92vw' : '520px'" :persistent="responding">
            <v-card v-if="offerTarget">
              <v-card-title class="pt-4">
                {{ offerDecision === 'accept' ? 'Accept' : 'Decline' }} {{ offerTarget.department?.name }}'s offer?
              </v-card-title>
              <v-card-text>
                <template v-if="offerDecision === 'accept'">
                  <v-alert
                    v-if="offerTargetOthers.inProgress.length"
                    type="warning"
                    variant="tonal"
                    density="compact"
                    class="mb-3"
                  >
                    <div class="font-weight-bold mb-1">
                      You still have {{ offerTargetOthers.inProgress.length }}
                      application{{ offerTargetOthers.inProgress.length === 1 ? '' : 's' }} in progress
                    </div>
                    <ul class="pl-4">
                      <li v-for="o in offerTargetOthers.inProgress" :key="o.id">
                        {{ o.department?.name }}: <em>{{ progressLabel(o) }}</em>
                      </li>
                    </ul>
                  </v-alert>
                  <v-alert
                    v-if="offerTargetOthers.offers.length"
                    type="info"
                    variant="tonal"
                    density="compact"
                    class="mb-3"
                  >
                    You also have an open offer from
                    <strong>{{ offerTargetOthers.offers.map((o) => o.department?.name).join(' and ') }}</strong>.
                    Accepting {{ offerTarget.department?.name }} closes
                    {{ offerTargetOthers.offers.length === 1 ? 'it' : 'them' }}.
                  </v-alert>
                  <p v-if="offerTargetOthers.all.length" class="text-body-2 mb-2">
                    Accepting will <strong>close these applications</strong>, and those teams will be told.
                    You can't undo this.
                  </p>
                  <p v-if="offerTargetOthers.all.length && offerTarget.offer?.expires_at && !offerTarget.offer?.overdue" class="text-body-2 text-medium-emphasis mb-0">
                    If you'd rather hear back from them first, this offer stays open until
                    <strong>{{ formatDateTime(offerTarget.offer.expires_at) }}</strong>.
                  </p>
                  <p v-if="!offerTargetOthers.all.length" class="text-body-2 mb-0">
                    You're about to join {{ offerTarget.department?.name }}. You can't undo this.
                  </p>
                </template>
                <p v-else class="text-body-2 mb-0">
                  You're turning down this offer. You can't undo this.
                  <template v-if="openOthers(offerTarget).length">Your other applications carry on as normal.</template>
                </p>
              </v-card-text>
              <v-card-actions>
                <v-spacer />
                <v-btn variant="text" :disabled="responding" @click="offerDialog = false">
                  {{ offerDecision === 'accept' && offerTargetOthers.all.length ? 'Wait for now' : 'Cancel' }}
                </v-btn>
                <v-btn
                  :color="offerDecision === 'accept' ? 'success' : 'error'"
                  variant="flat"
                  :loading="responding"
                  @click="respondToOffer"
                >
                  {{ offerConfirmLabel }}
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-dialog>

          <v-dialog v-model="submitDialog" :max-width="$vuetify.display.mobile ? '92vw' : '520px'" persistent>
            <v-card>
              <v-card-title class="text-h6 pt-4">Submit your case response</v-card-title>
              <v-card-text>
                <v-btn-toggle v-model="submitMode" mandatory density="compact" variant="outlined" class="mb-3">
                  <v-btn value="file" size="small" prepend-icon="mdi-paperclip">Upload a file</v-btn>
                  <v-btn value="link" size="small" prepend-icon="mdi-link-variant">Share a link</v-btn>
                </v-btn-toggle>

                <v-file-input
                  v-if="submitMode === 'file'"
                  v-model="submissionFile"
                  :label="`Your response (${ACCEPTED_UPLOAD_LABEL})`"
                  :accept="ACCEPTED_UPLOAD_MIME"
                  variant="outlined"
                  density="comfortable"
                  prepend-icon=""
                  prepend-inner-icon="mdi-paperclip"
                  :hint="`Max ${MAX_UPLOAD_MB} MB`"
                  persistent-hint
                />
                <v-text-field
                  v-else
                  v-model="submissionUrl"
                  label="Link to your response"
                  variant="outlined"
                  density="comfortable"
                  prepend-inner-icon="mdi-link-variant"
                  placeholder="https://…"
                  hint="Google Drive, Slides, Notion — make sure it's shared so we can open it."
                  persistent-hint
                />

                <v-alert v-if="caseOverdue" type="warning" variant="tonal" density="compact" class="mt-3">
                  The deadline has passed, but you can still submit — we'll see it came in late.
                </v-alert>
                <v-alert type="info" variant="tonal" density="compact" class="mt-3">
                  You can only submit once, so check it's the right file before sending.
                </v-alert>
              </v-card-text>
              <v-card-actions>
                <v-spacer />
                <v-btn variant="text" :disabled="submitting" @click="submitDialog = false">Cancel</v-btn>
                <v-btn
                  color="deep-purple"
                  variant="flat"
                  :disabled="!canSubmitResponse"
                  :loading="submitting"
                  @click="submitCaseResponse"
                >
                  Submit
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-dialog>

          <!-- Interview booked -->
          <v-card v-if="!isMultiApplication && application.interview" class="mb-4" variant="outlined">
            <v-card-text class="pa-4 pa-sm-5">
              <div class="d-flex align-center mb-2">
                <v-icon color="success" class="mr-2">mdi-calendar-check</v-icon>
                <span class="text-subtitle-2 font-weight-bold">Interview booked</span>
              </div>
              <div class="text-body-2 mb-1">{{ formatDateTime(application.interview.starts_at) }}</div>
              <div class="text-caption text-medium-emphasis mb-3">with {{ application.interview.interviewer }} · {{ appliedDepartment?.name }}</div>
              <div class="d-flex ga-2 flex-wrap">
                <v-btn :href="application.interview.meeting_link" target="_blank" color="primary" variant="flat" size="small" prepend-icon="mdi-video">Join call</v-btn>
                <v-btn variant="text" size="small" prepend-icon="mdi-calendar-edit">Reschedule</v-btn>
              </div>
            </v-card-text>
          </v-card>

          <!-- Interview invite (book via Calendly) -->
          <v-card v-else-if="!isMultiApplication && application.status === 'interview'" class="mb-4" variant="outlined">
            <v-card-text class="pa-4 pa-sm-5">
              <div class="d-flex align-center mb-2">
                <v-icon color="purple" class="mr-2">mdi-calendar-clock</v-icon>
                <span class="text-subtitle-2 font-weight-bold">Book your interview</span>
              </div>
              <!-- Only promise a booking link when there is one. The department's
                   Calendly link is set on the admin Scheduling page, and when it's
                   missing this card used to show encouraging copy with no button. -->
              <template v-if="calendlyLink">
                <p class="text-body-2 text-medium-emphasis mb-3">
                  Congrats on reaching the interview stage! Pick a slot that works for you - we've also emailed you this link.
                </p>
                <v-btn :href="calendlyLink" target="_blank" color="primary" variant="flat" size="small" prepend-icon="mdi-calendar-account">
                  Book my interview
                </v-btn>
              </template>
              <p v-else class="text-body-2 text-medium-emphasis mb-0">
                Congrats on reaching the interview stage! We'll be in touch by email shortly to arrange a time.
              </p>
            </v-card-text>
          </v-card>

          <!-- Accepted -->
          <!-- Driven by all applications, not the one holding the link: the
               accepted offer may be from any of them. -->
          <v-card v-if="acceptedApp" class="mb-4" color="success" variant="tonal">
            <v-card-text class="pa-4 pa-sm-5">
              <div class="d-flex align-center mb-2">
                <v-icon class="mr-2">mdi-party-popper</v-icon>
                <span class="text-subtitle-1 font-weight-bold">Welcome to {{ acceptedApp.department?.name }}!</span>
              </div>
              <p class="text-body-2 mb-0">
                You've accepted your offer. We'll be in touch with onboarding details - we can't wait to have you on the team.
              </p>
            </v-card-text>
          </v-card>

          <!-- Rejected -->
          <v-card v-if="allRejected" class="mb-4" variant="outlined">
            <v-card-text class="pa-4 pa-sm-5">
              <div class="text-subtitle-2 font-weight-bold mb-1">A note on your application</div>
              <p class="text-body-2 text-medium-emphasis mb-2">
                After careful consideration we won't be moving forward this time. It was a genuinely close call -
                please don't let it put you off applying again next cycle.
              </p>
              <p v-if="application.candidate.talent_pool_consent" class="text-caption text-medium-emphasis mb-0">
                With your permission we've kept your details in our talent pool and may reach out about future opportunities.
              </p>
            </v-card-text>
          </v-card>

          <!-- ── Progress timeline (single application only) ───────────── -->
          <v-card v-if="!isMultiApplication" class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-bold px-6 pt-5">Progress</v-card-title>
            <v-card-text class="px-4 px-sm-6 pb-6">
              <v-timeline side="end" density="comfortable" truncate-line="both" align="start">
                <v-timeline-item
                  v-for="stage in stages"
                  :key="stage.value"
                  :dot-color="stage.reached ? meta.color : 'grey-lighten-1'"
                  :icon="stage.reached && !stage.current ? 'mdi-check' : stage.icon"
                  size="small"
                  :fill-dot="stage.reached"
                >
                  <div class="d-flex align-center justify-space-between">
                    <span :class="stage.reached ? 'font-weight-medium' : 'text-medium-emphasis'">{{ stage.label }}</span>
                    <v-chip v-if="stage.current" size="x-small" :color="meta.color" variant="tonal" class="ml-2">Current</v-chip>
                  </div>
                  <div class="text-caption text-medium-emphasis">{{ stage.description }}</div>
                  <div v-if="stageDate(stage.value)" class="text-caption text-disabled mt-1">{{ formatDate(stageDate(stage.value)) }}</div>
                </v-timeline-item>
              </v-timeline>
            </v-card-text>
          </v-card>

          <!-- ── What you submitted ────────────────────────────────────── -->
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-bold px-6 pt-5">What you submitted</v-card-title>
            <v-card-text class="px-4 px-sm-6 pb-6">
              <v-row dense class="mb-2">
                <v-col cols="6" sm="4">
                  <div class="text-caption text-medium-emphasis">
                    {{ isMultiApplication ? 'Departments' : 'Department' }}
                  </div>
                  <div class="text-body-2 font-weight-medium">
                    {{ isMultiApplication ? allDepartmentNames : (appliedDepartment?.name || '-') }}
                  </div>
                </v-col>
                <v-col cols="6" sm="4">
                  <div class="text-caption text-medium-emphasis">Programme</div>
                  <div class="text-body-2">{{ application.candidate.degree || '-' }}</div>
                </v-col>
                <v-col cols="6" sm="4">
                  <div class="text-caption text-medium-emphasis">Year</div>
                  <div class="text-body-2">{{ application.candidate.year || '-' }}</div>
                </v-col>
              </v-row>

              <div class="text-caption text-medium-emphasis mb-1 mt-2">Documents</div>
              <div class="d-flex flex-wrap ga-2">
                <v-chip v-if="application.candidate.cv_s3_key" size="small" variant="outlined" prepend-icon="mdi-file-pdf-box">CV</v-chip>
                <v-chip
                  v-for="(m, i) in (application.answers.materials || [])"
                  :key="i"
                  size="small"
                  variant="outlined"
                  prepend-icon="mdi-paperclip"
                >
                  {{ m.filename || 'Attachment' }}
                </v-chip>
                <v-chip
                  v-for="(l, i) in (application.answers.links || [])"
                  :key="`l-${i}`"
                  size="small"
                  variant="tonal"
                  color="primary"
                  prepend-icon="mdi-link-variant"
                  :href="l.url"
                  target="_blank"
                >
                  {{ l.label }}
                </v-chip>
              </div>

              <!-- Only meaningful for a single application; with several, each
                   department has its own card above. -->
              <div v-if="!isMultiApplication && application.other_departments?.length" class="mt-3 text-caption text-medium-emphasis">
                Also being considered by: {{ application.other_departments.map(d => d.name).join(', ') }}.
              </div>
            </v-card-text>
          </v-card>

          <!-- ── Help / footer ─────────────────────────────────────────── -->
          <v-expansion-panels variant="accordion" class="mb-4">
            <v-expansion-panel title="What happens next?">
              <template #text>
                <p class="text-body-2 text-medium-emphasis mb-2">
                  Every application is reviewed by a real member of our team. You'll get an email at each step, and this page
                  always shows your latest status. Typical timeline from application to final decision is 1–2 weeks.
                </p>
                <p class="text-body-2 text-medium-emphasis mb-0">
                  Questions? Reply to any of our emails or reach us at
                  <a href="mailto:recruitment@ennova.com">recruitment@ennova.com</a>.
                </p>
              </template>
            </v-expansion-panel>
          </v-expansion-panels>

          <p class="text-caption text-medium-emphasis text-center">
            <v-icon size="x-small">mdi-lock-outline</v-icon>
            This page is private to you. Bookmark it - the link stays valid throughout the process.
          </p>
        </template>

        <v-card v-else class="pa-8 text-center">
          <v-icon icon="mdi-link-off" color="error" size="64" class="mb-4" />
          <h2 class="text-h6 mb-2">Link not valid</h2>
          <p class="text-body-2 text-medium-emphasis">This status link is invalid or has expired.</p>
        </v-card>

      </v-col>
    </v-row>

    <v-snackbar v-model="toast.show" :color="toast.color" :timeout="4000" location="top">{{ toast.text }}</v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { RecruitmentService } from '@/services/RecruitmentService.js';
import { statusMeta } from '@/data/recruitmentMock.js';
import OfferActions from '@/components/recruitment/OfferActions.vue';
import { ACCEPTED_UPLOAD_MIME, ACCEPTED_UPLOAD_LABEL, MAX_UPLOAD_MB } from '@/utils/uploadTypes.js';

const route = useRoute();
const isLoading = ref(true);
const application = ref(null);
const toast = reactive({ show: false, text: '', color: 'success' });

function notify(text, color = 'success') {
  toast.text = text;
  toast.color = color;
  toast.show = true;
}

// ── Multi-department applicants ───────────────────────────────────────────
// A candidate picking several departments files one application per team, each
// with its own stage and actions.
const isMultiApplication = computed(() => (application.value?.applications || []).length > 1);
const allDepartmentNames = computed(
  () => (application.value?.applications || [])
    .map((a) => a.department?.name).filter(Boolean).join(' · ')
);

function narrativeFor(status) {
  return NARRATIVES[status] || NARRATIVES.applied;
}

// ── Offers ────────────────────────────────────────────────────────────────
// A single-department candidate still gets a one-entry list, so everything
// below works for both layouts.
const apps = computed(() => application.value?.applications || []);
const CLOSED = ['accepted', 'offer_declined', 'rejected', 'withdrawn'];

// The candidate's other applications that accepting `a` would close.
function openOthers(a) {
  return apps.value.filter((o) => o.id !== a?.id && !o.locked && !CLOSED.includes(o.status));
}
const acceptedApp = computed(() => apps.value.find((a) => a.status === 'accepted') || null);
const allRejected = computed(() => apps.value.length > 0 && apps.value.every((a) => a.status === 'rejected'));

const LOCKED_META = { title: 'Closed', color: 'grey', icon: 'mdi-lock-outline' };
function cardMeta(a) {
  return a.locked ? LOCKED_META : statusMeta(a.status);
}

// Where an application stands, in words, for the accept warning.
function progressLabel(a) {
  if (a.status === 'offered') return 'Offer waiting for your answer';
  if (a.interview) return `Interview booked, ${formatDate(a.interview.starts_at)}`;
  if (a.status === 'case_submitted') return 'Case study submitted';
  if (a.status === 'case_sent') return 'Case study to complete';
  return statusMeta(a.status).title;
}

const offerDialog = ref(false);
const offerTarget = ref(null);
const offerDecision = ref('accept');
const responding = ref(false);

const offerTargetOthers = computed(() => {
  const all = openOthers(offerTarget.value);
  return {
    all,
    inProgress: all.filter((o) => o.status !== 'offered'),
    offers: all.filter((o) => o.status === 'offered'),
  };
});
const offerConfirmLabel = computed(() => {
  const name = offerTarget.value?.department?.name || 'offer';
  if (offerDecision.value === 'decline') return 'Decline offer';
  const n = offerTargetOthers.value.all.length;
  return n ? `Accept ${name} & close ${n} other${n === 1 ? '' : 's'}` : `Accept ${name}`;
});

function openOfferDialog(a, decision) {
  offerTarget.value = a;
  offerDecision.value = decision;
  offerDialog.value = true;
}

async function respondToOffer() {
  responding.value = true;
  try {
    application.value = await RecruitmentService.respondToOffer(route.params.token, {
      application_id: offerTarget.value.id,
      decision: offerDecision.value,
    });
    offerDialog.value = false;
    notify(offerDecision.value === 'accept' ? 'Offer accepted - welcome aboard!' : 'Offer declined');
  } catch (err) {
    console.error('Failed to respond to offer:', err);
    notify(err.response?.data?.detail || 'Could not record your answer. Please try again.', 'error');
  } finally {
    responding.value = false;
  }
}
function isOverdue(caseBlock) {
  return !!caseBlock?.deadline_at && new Date(caseBlock.deadline_at) < new Date();
}
function countdownFor(caseBlock) {
  if (!caseBlock?.deadline_at) return '';
  const diff = new Date(caseBlock.deadline_at).getTime() - Date.now();
  if (diff <= 0) return 'overdue';
  const hrs = Math.round(diff / 3600000);
  return hrs < 24 ? `${hrs}h` : `${Math.round(hrs / 24)}d`;
}

// ── Case response submission ──────────────────────────────────────────────
const submitDialog = ref(false);
// Which application the dialog is answering for; null means the one holding
// the token, which is all a single-department candidate needs.
const submitForApplicationId = ref(null);

function openSubmitDialog(app) {
  submitForApplicationId.value = app?.id ?? null;
  submissionFile.value = null;
  submissionUrl.value = '';
  submitMode.value = 'file';
  submitDialog.value = true;
}
const submitMode = ref('file');
const submissionFile = ref(null);
const submissionUrl = ref('');
const submitting = ref(false);

const canSubmitResponse = computed(() =>
  submitMode.value === 'file' ? !!submissionFile.value : !!submissionUrl.value.trim()
);

async function submitCaseResponse() {
  submitting.value = true;
  try {
    let payload;
    if (submitMode.value === 'file') {
      const up = await RecruitmentService.uploadDocument(submissionFile.value);
      payload = { submission_s3_key: up.s3_key, submission_filename: up.filename };
    } else {
      payload = { submission_url: submissionUrl.value.trim() };
    }
    payload.application_id = submitForApplicationId.value;
    // The endpoint returns the refreshed status, so the page reflects the new
    // stage without a reload.
    application.value = await RecruitmentService.submitCaseResponse(route.params.token, payload);
    submitDialog.value = false;
    notify('Case response submitted - thanks!');
  } catch (err) {
    console.error('Failed to submit case response:', err);
    notify(err.response?.data?.detail || 'Could not submit your response. Please try again.', 'error');
  } finally {
    submitting.value = false;
  }
}

const meta = computed(() => statusMeta(application.value?.status));
const appliedDepartment = computed(
  () => application.value?.final_department || application.value?.applied_department || null
);
const cycleName = computed(() => 'Autumn 2026 Intake');

// A friendly, human reference the candidate can quote in emails.
const reference = computed(() => {
  const id = application.value?.id ?? 0;
  return `EN26-${String(id).padStart(4, '0')}`;
});

const calendlyLink = computed(
  () => application.value?.final_department?.calendly_link || application.value?.applied_department?.calendly_link || ''
);

// Status-specific narrative shown in the banner.
const NARRATIVES = {
  applied: { tone: 'info', icon: 'mdi-inbox-arrow-down', title: 'Application received', body: 'Thanks for applying! Your application is in the queue and a member of our team will review it personally.', hint: 'No action needed right now - we\'ll email you as soon as there\'s an update.' },
  in_review: { tone: 'info', icon: 'mdi-file-search-outline', title: 'Under review', body: 'The team is reviewing your application right now. Hang tight - this usually takes a few days.', hint: '' },
  case_sent: { tone: 'deep-purple', icon: 'mdi-briefcase-clock-outline', title: 'Case study sent', body: 'You\'ve been invited to complete a short case study. Details and your deadline are below.', hint: '' },
  case_submitted: { tone: 'indigo', icon: 'mdi-briefcase-check-outline', title: 'Case received', body: 'Thanks - we\'ve got your case submission. The team is reviewing it and will be in touch about interviews.', hint: '' },
  interview: { tone: 'purple', icon: 'mdi-account-voice', title: 'You\'re through to interviews', body: 'Great news - we\'d love to meet you. Book a time using the link below.', hint: '' },
  decision: { tone: 'amber-darken-2', icon: 'mdi-scale-balance', title: 'Final decision in progress', body: 'Interviews are wrapped up and the team is making their final call. You\'ll hear from us very soon.', hint: '' },
  offered: { tone: 'teal', icon: 'mdi-email-seal-outline', title: 'You\'ve got an offer!', body: 'Congratulations - the team would love to have you. Accept or decline below.', hint: '' },
  accepted: { tone: 'success', icon: 'mdi-check-decagram', title: 'You\'re in!', body: 'You accepted this offer. Welcome to the team!', hint: '' },
  offer_declined: { tone: 'grey', icon: 'mdi-hand-back-left-outline', title: 'Offer declined', body: 'You turned down this offer. Thanks for letting the team know.', hint: '' },
  rejected: { tone: 'grey', icon: 'mdi-emoticon-sad-outline', title: 'Application closed', body: 'Thank you for taking the time to apply. See the note below.', hint: '' },
  withdrawn: { tone: 'grey', icon: 'mdi-account-off-outline', title: 'Application withdrawn', body: 'This application has been withdrawn. If that\'s a mistake, get in touch and we\'ll sort it out.', hint: '' },
};
const narrative = computed(() => NARRATIVES[application.value?.status] || NARRATIVES.applied);

const heroStyle = computed(() => ({
  borderLeft: `4px solid rgb(var(--v-theme-${meta.value.color}))`,
}));

// ── Case countdown ──────────────────────────────────────────────────────
const caseOverdue = computed(
  () => application.value?.case && new Date(application.value.case.deadline_at) < new Date()
);
const caseCountdown = computed(() => {
  if (!application.value?.case) return '';
  const diff = new Date(application.value.case.deadline_at).getTime() - Date.now();
  if (diff <= 0) return '0h';
  const hrs = Math.round(diff / 3600000);
  return hrs < 24 ? `${hrs}h` : `${Math.round(hrs / 24)}d`;
});

// ── Journey with descriptions + dates ───────────────────────────────────
const STAGE_DESC = {
  applied: 'We received your application.',
  in_review: 'A team member reviews your profile.',
  case: 'Complete and submit the case study.',
  interview: 'Meet the team.',
  decision: 'Final call and outcome email.',
};

const OUTCOME_STATUSES = ['offered', 'accepted', 'offer_declined', 'rejected'];

// Stage list for one application, used by the compact per-department strip.
function stagesFor(a) {
  const journey = [
    { value: 'applied', label: 'Applied' },
    { value: 'in_review', label: 'In review' },
    ...(a.case ? [{ value: 'case', label: 'Case study' }] : []),
    { value: 'interview', label: 'Interview' },
    { value: 'decision', label: 'Decision' },
  ];
  const order = journey.map((st) => st.value);
  let reachedIdx;
  if (OUTCOME_STATUSES.includes(a.status)) reachedIdx = order.indexOf('decision');
  else if (['case_sent', 'case_submitted'].includes(a.status)) reachedIdx = order.indexOf('case');
  else reachedIdx = order.indexOf(a.status);
  return journey.map((st, idx) => ({ ...st, reached: idx <= reachedIdx, current: idx === reachedIdx }));
}

const stages = computed(() => {
  const isMarketing = !!application.value?.case;
  const journey = [
    { value: 'applied', label: 'Application received', icon: 'mdi-inbox-arrow-down' },
    { value: 'in_review', label: 'Under review', icon: 'mdi-file-search-outline' },
    ...(isMarketing ? [{ value: 'case', label: 'Case study', icon: 'mdi-briefcase-clock-outline' }] : []),
    { value: 'interview', label: 'Interview', icon: 'mdi-account-voice' },
    { value: 'decision', label: 'Final decision', icon: 'mdi-flag-checkered' },
  ];
  const order = journey.map((s) => s.value);
  const status = application.value?.status;
  let reachedIdx;
  if (OUTCOME_STATUSES.includes(status)) reachedIdx = order.indexOf('decision');
  else if (['case_sent', 'case_submitted'].includes(status)) reachedIdx = order.indexOf('case');
  else reachedIdx = order.indexOf(status);
  return journey.map((s, idx) => ({
    ...s,
    description: STAGE_DESC[s.value] || '',
    reached: idx <= reachedIdx,
    current: idx === reachedIdx,
  }));
});

// Pull the date a stage was reached from the event timeline, when available.
function stageDate(stageValue) {
  const tl = application.value?.timeline || [];
  const targets = stageValue === 'case' ? ['case_sent', 'case_submitted'] : [stageValue];
  const ev = tl.find((e) => e.type === 'status_change' && targets.includes(e.payload?.to));
  return ev?.created_at || null;
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}
function formatDateTime(iso) {
  return new Date(iso).toLocaleString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

onMounted(async () => {
  try {
    application.value = await RecruitmentService.getStatusByToken(route.params.token);
  } catch {
    application.value = null;
  } finally {
    isLoading.value = false;
  }
});
</script>

<style scoped>
.status-hero {
  overflow: hidden;
}
a {
  color: rgb(var(--v-theme-primary));
  text-decoration: none;
}
</style>
