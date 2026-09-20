<template>
  <div class="kanban-scroll">
    <div class="kanban-row">
      <div
        v-for="col in columns"
        :key="col.value"
        class="kanban-col"
        :class="{ 'kanban-col--over': dragOverCol === col.value }"
        @dragover.prevent="dragOverCol = col.value"
        @dragleave="dragOverCol = null"
        @drop="onDrop(col.value)"
      >
        <div class="d-flex align-center mb-3 px-1">
          <v-icon :icon="col.icon" :color="col.color" size="small" class="mr-2" />
          <span class="text-subtitle-2 font-weight-bold">{{ col.title }}</span>
          <v-chip size="x-small" variant="tonal" class="ml-2">{{ itemsFor(col.value).length }}</v-chip>
        </div>

        <div class="kanban-col-body">
          <v-card
            v-for="app in itemsFor(col.value)"
            :key="app.id"
            variant="outlined"
            class="mb-2 kanban-card"
            :class="{ 'kanban-card--locked': isFrozen(app) }"
            :draggable="!isFrozen(app)"
            @dragstart="onDragStart(app)"
            @dragend="dragging = null"
            @click="$emit('open', app.id)"
          >
            <v-card-text class="pa-3">
              <div class="d-flex align-center mb-1">
                <v-avatar size="28" color="primary" variant="tonal" class="mr-2">
                  <span class="text-caption">{{ initials(app.candidate.full_name) }}</span>
                </v-avatar>
                <span class="text-body-2 font-weight-medium text-truncate">{{ app.candidate.full_name }}</span>
              </div>

              <div class="d-flex align-center flex-wrap ga-1 mt-2">
                <!-- Where this candidate ranked the department in view. -->
                <v-chip
                  v-if="choiceMeta(app)"
                  size="x-small"
                  :color="choiceMeta(app).color"
                  :variant="choiceMeta(app).first ? 'flat' : 'tonal'"
                  :title="choiceMeta(app).title"
                >
                  <v-icon start size="x-small">{{ choiceMeta(app).icon }}</v-icon>
                  {{ choiceMeta(app).text }}
                </v-chip>
                <v-chip
                  v-if="app.final_department"
                  size="x-small"
                  color="primary"
                  variant="flat"
                >
                  {{ app.final_department.name }}
                </v-chip>
                <v-chip
                  v-else-if="app.match_pending"
                  size="x-small"
                  color="grey"
                  variant="tonal"
                >
                  <v-icon start size="x-small">mdi-timer-sand</v-icon>
                  Matching pending
                </v-chip>
                <v-chip
                  v-else-if="app.suggested_department"
                  size="x-small"
                  color="info"
                  variant="tonal"
                >
                  <v-icon start size="x-small">mdi-robot-outline</v-icon>
                  {{ app.suggested_department.name }} · {{ Math.round(app.match_confidence * 100) }}%
                </v-chip>
              </div>

              <!-- Locked: the candidate accepted another department's offer -->
              <div v-if="app.locked" class="mt-2">
                <v-chip size="x-small" color="grey-darken-1" variant="flat">
                  <v-icon start size="x-small">mdi-lock-outline</v-icon>
                  Accepted by {{ app.locked.by_department || 'another department' }}
                </v-chip>
              </div>

              <!-- Offer awaiting the candidate's answer -->
              <div v-else-if="app.status === 'offered' && app.offer" class="mt-2">
                <v-chip size="x-small" :color="app.offer.overdue ? 'error' : 'teal'" variant="tonal">
                  <v-icon start size="x-small">mdi-timer-sand</v-icon>
                  {{ app.offer.overdue ? 'Offer overdue' : `Answer due ${offerCountdown(app)}` }}
                </v-chip>
              </div>

              <!-- Marketing case deadline badge -->
              <div v-if="app.case && !app.case.submitted_at" class="mt-2">
                <v-chip size="x-small" :color="caseOverdue(app) ? 'error' : 'deep-purple'" variant="tonal">
                  <v-icon start size="x-small">mdi-clock-alert-outline</v-icon>
                  Case due {{ caseCountdown(app) }}
                </v-chip>
              </div>

              <div class="text-caption text-medium-emphasis mt-2">
                {{ app.candidate.year }} · {{ timeAgo(app.created_at) }}
              </div>
            </v-card-text>
          </v-card>

          <div v-if="itemsFor(col.value).length === 0" class="kanban-empty text-caption text-medium-emphasis">
            Drop here
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { APPLICATION_STATUSES, choiceMeta } from '@/data/recruitmentMock.js';

import { computed } from 'vue';

const props = defineProps({
  applications: { type: Array, default: () => [] },
  // Show the case columns (case_sent / case_submitted) because the department
  // in view runs a case stage.
  showCaseStages: { type: Boolean, default: false },
});
const emit = defineEmits(['open', 'status-change']);

// A card whose status has no column would simply not render, so any case status
// present in the current set forces its column open. Without this a candidate
// mid-case vanished from the board whenever the case columns were hidden -
// on the unfiltered board, or when filtered to another department they ranked.
const hasApplicationInCaseStage = computed(() =>
  props.applications.some((a) => a.status === 'case_sent' || a.status === 'case_submitted')
);

// Kanban columns exclude "withdrawn" (a terminal side-state, not a column).
// Case columns stay hidden otherwise, so boards without a case stage stay compact.
const columns = computed(() => {
  const showCases = props.showCaseStages || hasApplicationInCaseStage.value;
  return APPLICATION_STATUSES.filter(
    (s) => s.value !== 'withdrawn' && (!s.marketing_only || showCases)
  );
});

const dragging = ref(null);
const dragOverCol = ref(null);

function itemsFor(status) {
  return props.applications.filter((a) => a.status === status);
}

// Locked cards and accepted offers can't be moved: a locked application is
// closed, and moving an accepted one would strand the applications it locked.
function isFrozen(app) {
  return !!app.locked || app.status === 'accepted';
}

function onDragStart(app) {
  dragging.value = app;
}

function onDrop(status) {
  dragOverCol.value = null;
  if (dragging.value && dragging.value.status !== status) {
    emit('status-change', { id: dragging.value.id, from: dragging.value.status, to: status });
  }
  dragging.value = null;
}

function initials(name) {
  return name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase();
}

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return 'today';
  if (days === 1) return '1 day ago';
  return `${days} days ago`;
}

function offerCountdown(app) {
  const diff = new Date(app.offer.expires_at).getTime() - Date.now();
  const hrs = Math.max(1, Math.round(diff / 3600000));
  return hrs < 24 ? `in ${hrs}h` : `in ${Math.round(hrs / 24)}d`;
}

function caseOverdue(app) {
  return app.case && new Date(app.case.deadline_at).getTime() < Date.now();
}
function caseCountdown(app) {
  const diff = new Date(app.case.deadline_at).getTime() - Date.now();
  if (diff <= 0) return 'overdue';
  const hrs = Math.round(diff / 3600000);
  return hrs < 24 ? `in ${hrs}h` : `in ${Math.round(hrs / 24)}d`;
}
</script>

<style scoped>
.kanban-scroll {
  overflow-x: auto;
  padding-bottom: 8px;
}
.kanban-row {
  display: flex;
  gap: 12px;
  min-width: min-content;
}
.kanban-col {
  flex: 0 0 260px;
  width: 260px;
  background: rgba(var(--v-theme-on-surface), 0.03);
  border-radius: 8px;
  padding: 10px;
  transition: background 0.15s ease;
}
.kanban-col--over {
  background: rgba(var(--v-theme-primary), 0.1);
  outline: 2px dashed rgba(var(--v-theme-primary), 0.4);
}
.kanban-col-body {
  min-height: 120px;
}
.kanban-card {
  cursor: grab;
}
.kanban-card:active {
  cursor: grabbing;
}
.kanban-card--locked {
  cursor: pointer;
  opacity: 0.6;
}
.kanban-empty {
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.15);
  border-radius: 6px;
  padding: 16px;
  text-align: center;
}
</style>
