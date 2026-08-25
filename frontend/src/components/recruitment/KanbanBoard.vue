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
            draggable="true"
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
import { APPLICATION_STATUSES } from '@/data/recruitmentMock.js';

import { computed } from 'vue';

const props = defineProps({
  applications: { type: Array, default: () => [] },
  // Show the Marketing-only case columns (case_sent / case_submitted).
  showMarketingStages: { type: Boolean, default: false },
});
const emit = defineEmits(['open', 'status-change']);

// Kanban columns exclude "withdrawn" (a terminal side-state, not a column).
// Marketing-only columns appear only when relevant so the board stays compact.
const columns = computed(() =>
  APPLICATION_STATUSES.filter(
    (s) => s.value !== 'withdrawn' && (!s.marketing_only || props.showMarketingStages)
  )
);

const dragging = ref(null);
const dragOverCol = ref(null);

function itemsFor(status) {
  return props.applications.filter((a) => a.status === status);
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
.kanban-empty {
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.15);
  border-radius: 6px;
  padding: 16px;
  text-align: center;
}
</style>
