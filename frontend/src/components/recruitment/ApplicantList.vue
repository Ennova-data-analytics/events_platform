<template>
  <div>
    <v-card v-for="app in applications" :key="app.id" variant="outlined" class="mb-3">
      <v-card-text class="pa-4">
        <div class="d-flex flex-wrap align-center ga-3">
          <v-avatar size="40" color="primary" variant="tonal">
            <span class="text-body-2">{{ initials(app.candidate.full_name) }}</span>
          </v-avatar>
          <div class="flex-grow-1" style="min-width: 200px">
            <div class="d-flex align-center ga-2 flex-wrap">
              <span class="text-subtitle-1 font-weight-bold">{{ app.candidate.full_name }}</span>
              <v-chip :color="statusMeta(app.status).color" size="x-small" variant="tonal">
                <v-icon start :icon="statusMeta(app.status).icon" size="x-small" />
                {{ statusMeta(app.status).title }}
              </v-chip>
            </div>
            <div class="text-caption text-medium-emphasis">
              <a :href="`mailto:${app.candidate.email}`">{{ app.candidate.email }}</a>
              <span v-if="app.candidate.phone"> · {{ app.candidate.phone }}</span>
            </div>
          </div>
          <v-btn size="small" variant="tonal" color="primary" append-icon="mdi-arrow-right" @click="$emit('open', app.id)">
            Open
          </v-btn>
        </div>

        <!-- Key facts grid -->
        <v-row class="mt-1" dense>
          <v-col cols="6" sm="3">
            <div class="text-caption text-medium-emphasis">Applying for</div>
            <div class="text-body-2 font-weight-medium">{{ (app.final_department || app.applied_department)?.name || '-' }}</div>
          </v-col>
          <v-col cols="6" sm="3">
            <div class="text-caption text-medium-emphasis">Programme</div>
            <div class="text-body-2">{{ app.candidate.degree || '-' }}</div>
          </v-col>
          <v-col cols="6" sm="2">
            <div class="text-caption text-medium-emphasis">Year</div>
            <div class="text-body-2">{{ app.candidate.year || '-' }}</div>
          </v-col>
          <v-col cols="6" sm="2">
            <div class="text-caption text-medium-emphasis">AI match</div>
            <div class="text-body-2">
              <span v-if="app.match_pending" class="text-medium-emphasis">pending</span>
              <span v-else-if="app.match_confidence">{{ Math.round(app.match_confidence * 100) }}%</span>
              <span v-else>-</span>
            </div>
          </v-col>
          <v-col cols="6" sm="2">
            <div class="text-caption text-medium-emphasis">Source</div>
            <div class="text-body-2">{{ app.source }}</div>
          </v-col>
        </v-row>

        <div v-if="app.other_departments?.length || app.answers.other_associations" class="mt-2 text-caption text-medium-emphasis">
          <span v-if="app.other_departments?.length">
            Also applied: {{ app.other_departments.map(d => d.name).join(', ') }}.
          </span>
          <span v-if="app.answers.other_associations">Other associations: {{ app.answers.other_associations }}.</span>
        </div>

        <p class="text-body-2 mt-2 mb-0 text-truncate-2">{{ app.answers.background }}</p>

        <!-- Inline documents - open without leaving the list -->
        <div class="d-flex align-center flex-wrap ga-2 mt-3">
          <v-btn
            v-if="app.candidate.cv_s3_key"
            size="x-small"
            variant="outlined"
            prepend-icon="mdi-file-pdf-box"
            href="#mock-cv"
            target="_blank"
          >
            CV
          </v-btn>
          <v-chip v-else size="x-small" color="warning" variant="tonal">No CV</v-chip>

          <v-btn
            v-for="(m, i) in (app.answers.materials || [])"
            :key="`m-${i}`"
            size="x-small"
            variant="outlined"
            prepend-icon="mdi-paperclip"
            href="#mock-material"
            target="_blank"
          >
            {{ shortName(m.filename) }}
          </v-btn>

          <v-btn
            v-for="(l, i) in (app.answers.links || [])"
            :key="`l-${i}`"
            size="x-small"
            variant="text"
            color="primary"
            prepend-icon="mdi-link-variant"
            :href="l.url"
            target="_blank"
          >
            {{ l.label }}
          </v-btn>

          <v-btn
            v-if="app.candidate.links?.linkedin"
            size="x-small"
            variant="text"
            prepend-icon="mdi-linkedin"
            :href="`https://${app.candidate.links.linkedin}`"
            target="_blank"
          >
            LinkedIn
          </v-btn>

          <v-btn
            v-if="app.case && !app.case.submitted_at"
            size="x-small"
            variant="text"
            color="deep-purple"
            :href="app.case.brief_url"
            target="_blank"
            prepend-icon="mdi-briefcase-clock-outline"
          >
            Case due {{ caseCountdown(app) }}
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <v-alert v-if="applications.length === 0" type="info" variant="tonal" density="compact">
      No applicants match these filters.
    </v-alert>
  </div>
</template>

<script setup>
import { statusMeta } from '@/data/recruitmentMock.js';

defineProps({
  applications: { type: Array, default: () => [] },
});
defineEmits(['open']);

function initials(name) {
  return name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase();
}
function shortName(name) {
  if (!name) return 'File';
  return name.length > 18 ? `${name.slice(0, 15)}…` : name;
}
function caseCountdown(app) {
  const diff = new Date(app.case.deadline_at).getTime() - Date.now();
  if (diff <= 0) return 'overdue';
  const hrs = Math.round(diff / 3600000);
  return hrs < 24 ? `in ${hrs}h` : `in ${Math.round(hrs / 24)}d`;
}
</script>

<style scoped>
.text-truncate-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: rgba(var(--v-theme-on-surface), 0.7);
}
a {
  color: rgb(var(--v-theme-primary));
  text-decoration: none;
}
</style>
