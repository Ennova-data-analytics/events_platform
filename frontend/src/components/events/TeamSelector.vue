<template>
  <div class="team-selector">
    <h3 class="text-subtitle-1 font-weight-bold mb-3">
      <v-icon start color="primary">mdi-account-group</v-icon>
      Team Selection (Required)
    </h3>

    <v-radio-group v-model="selectionMode" class="mb-4">
      <v-radio label="Join an existing team" value="join" color="primary"></v-radio>
      <v-radio label="Create a new team" value="create" color="primary"></v-radio>
      <v-radio label="Continue without a team (admin will assign later)" value="skip" color="primary"></v-radio>
    </v-radio-group>

    <!-- Join Existing Team -->
    <div v-if="selectionMode === 'join'" class="mt-4">
      <v-alert v-if="isLoadingTeams" type="info" variant="tonal" density="compact" class="mb-3">
        <v-progress-circular size="16" width="2" indeterminate class="mr-2"></v-progress-circular>
        Loading available teams...
      </v-alert>

      <v-alert v-else-if="loadError" type="error" variant="tonal" density="compact" class="mb-3">
        <v-icon start>mdi-alert-circle</v-icon>
        {{ loadError }}
      </v-alert>

      <v-alert v-else-if="availableTeams.length === 0" type="warning" variant="tonal" density="compact" class="mb-3">
        <v-icon start>mdi-alert</v-icon>
        No teams available yet. Be the first to create one!
      </v-alert>

      <div v-else>
        <p class="text-caption text-grey mb-3">
          Select a team to join. You can see who's already in each team.
        </p>

        <v-card
          v-for="team in availableTeams"
          :key="team.team_id"
          :variant="selectedTeam?.team_id === team.team_id ? 'elevated' : 'outlined'"
          :color="selectedTeam?.team_id === team.team_id ? 'primary' : ''"
          class="mb-5 team-card"
          :class="{
            'selected': selectedTeam?.team_id === team.team_id,
            'full': team.is_full,
            'selectable': !team.is_full
          }"
          @click="!team.is_full && selectTeam(team)"
        >
          <v-card-text class="pa-4">
            <div class="d-flex justify-space-between align-center mb-2">
              <div class="font-weight-bold text-body-1">
                <v-icon v-if="selectedTeam?.team_id === team.team_id" start color="white">mdi-check-circle</v-icon>
                {{ team.team_name }}
              </div>
              <v-chip
                size="small"
                :color="team.is_full ? 'error' : 'success'"
                variant="tonal"
              >
                <v-icon start size="small">mdi-account-multiple</v-icon>
                {{ team.member_count }}{{ team.max_members ? `/${team.max_members}` : '' }}
              </v-chip>
            </div>

            <div v-if="team.members.length > 0" class="text-caption text-grey-darken-1 mt-2">
              <v-icon size="small" start>mdi-account</v-icon>
              <strong>Members:</strong> {{ formatMembers(team.members) }}
            </div>

            <v-chip v-if="team.is_full" color="error" size="x-small" class="mt-2">
              <v-icon start size="x-small">mdi-cancel</v-icon>
              Team Full
            </v-chip>
          </v-card-text>
        </v-card>
      </div>
    </div>

    <!-- Create New Team -->
    <div v-if="selectionMode === 'create'" class="mt-4">
      <p class="text-caption text-grey mb-3">
        Create a new team with a unique name. Other users will be able to join your team.
      </p>

      <v-text-field
        v-model="newTeamName"
        label="Team Name"
        placeholder="Enter a unique team name"
        variant="outlined"
        :rules="[rules.required, rules.minLength, rules.maxLength]"
        counter="255"
        hint="Choose a memorable name that represents your team"
        persistent-hint
        :error-messages="teamNameError"
        @input="teamNameError = ''"
      >
        <template v-slot:prepend-inner>
          <v-icon color="primary">mdi-flag</v-icon>
        </template>
      </v-text-field>

      <v-alert
        v-if="effectiveMaxMembers"
        type="info"
        variant="tonal"
        density="compact"
        class="mt-3"
      >
        <v-icon start size="small">mdi-information</v-icon>
        Max team size: {{ effectiveMaxMembers }} members
      </v-alert>
    </div>

    <!-- Continue Without Team -->
    <div v-if="selectionMode === 'skip'" class="mt-4">
      <v-alert type="info" variant="tonal">
        <v-icon start>mdi-information</v-icon>
        <div class="text-body-2">
          <strong>No team selected</strong>
          <p class="mt-2 mb-0">
            You can continue your registration without joining or creating a team. An administrator will manually assign you to a team later.
          </p>
        </div>
      </v-alert>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { TeamService } from '@/services/TeamService.js';

const props = defineProps({
  eventId: {
    type: Number,
    required: true
  },
  ticketTypeId: {
    type: Number,
    required: false,
    default: null
  },
  ticketTypeMaxMembers: {
    type: Number,
    default: null
  },
  eventMaxMembers: {
    type: Number,
    default: null
  }
});

const emit = defineEmits(['update:teamSelection']);

// State
const selectionMode = ref('join');
const availableTeams = ref([]);
const selectedTeam = ref(null);
const newTeamName = ref('');
const isLoadingTeams = ref(false);
const loadError = ref('');
const teamNameError = ref('');

// Validation Rules
const rules = {
  required: v => !!v || 'Team name is required',
  minLength: v => (v && v.length >= 2) || 'Team name must be at least 2 characters',
  maxLength: v => (v && v.length <= 255) || 'Team name must be less than 255 characters'
};

// Computed
const teamSelection = computed(() => {
  if (selectionMode.value === 'join') {
    return selectedTeam.value ? {
      action: 'join',
      team_id: selectedTeam.value.team_id,
      team_name: null
    } : null;
  } else if (selectionMode.value === 'create') {
    // Only return team selection if name is valid
    const name = newTeamName.value?.trim();
    if (!name || name.length < 2 || name.length > 255) {
      return null;
    }
    return {
      action: 'create',
      team_id: null,
      team_name: name
    };
  } else if (selectionMode.value === 'skip') {
    // User wants to continue without a team - admin will assign later
    return {
      action: 'skip',
      team_id: null,
      team_name: null
    };
  }
  return null;
});

const effectiveMaxMembers = computed(() => {
  return props.ticketTypeMaxMembers ?? props.eventMaxMembers ?? null;
});

// Watch for changes and emit
watch(teamSelection, (newValue) => {
  emit('update:teamSelection', newValue);
}, { deep: true });

// Methods
async function loadTeams() {
  isLoadingTeams.value = true;
  loadError.value = '';
  try {
    const response = await TeamService.getTeamsForEvent(props.eventId);
    availableTeams.value = response.data.teams || [];
  } catch (error) {
    console.error('Failed to load teams:', error);
    loadError.value = 'Failed to load teams. Please try again.';
    availableTeams.value = [];
  } finally {
    isLoadingTeams.value = false;
  }
}

function selectTeam(team) {
  if (team.is_full) return;
  selectedTeam.value = selectedTeam.value?.team_id === team.team_id ? null : team;
}

function formatMembers(members) {
  if (!members || members.length === 0) return 'No members yet';

  const names = members
    .map(m => m.full_name || 'Unknown')
    .filter(name => name !== 'Unknown');

  if (names.length === 0) return 'Members registered';
  if (names.length <= 3) return names.join(', ');

  return `${names.slice(0, 3).join(', ')} +${names.length - 3} more`;
}

// Lifecycle
onMounted(() => {
  loadTeams();
});

// Watch for mode changes - reset state
watch(selectionMode, () => {
  selectedTeam.value = null;
  newTeamName.value = '';
  teamNameError.value = '';

  if (selectionMode.value === 'join') {
    loadTeams();
  }
});
</script>

<style scoped>
.team-card {
  transition: all 0.2s ease;
  border: 2px solid rgb(var(--v-theme-primary)) !important;
}

.team-card.selectable {
  cursor: pointer;
}

.team-card.selectable:hover {
  border-color: rgba(var(--v-theme-primary), 0.8) !important;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.team-card.selected {
  border-color: rgb(var(--v-theme-primary)) !important;
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.team-card.full {
  opacity: 0.6;
  cursor: not-allowed;
  border-color: rgb(var(--v-theme-primary)) !important;
}

.team-card.full:hover {
  transform: none;
  box-shadow: none;
  border-color: rgb(var(--v-theme-primary)) !important;
}

.team-selector {
  padding: 16px;
  background-color: rgba(var(--v-theme-surface), 1);
  border-radius: 8px;
}
</style>
