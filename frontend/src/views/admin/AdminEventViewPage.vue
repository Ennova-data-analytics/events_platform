<template>
  <div>
    <div class="d-flex align-center mb-4">
      <v-btn icon="mdi-arrow-left" variant="text" to="/admin/events" class="mr-2"></v-btn>
      <h1 class="text-h5">Manage Attendees: {{ eventTitle }}</h1>
    </div>

    <v-tabs v-model="tab" bg-color="surface" class="mb-4">
      <v-tab value="pending">Pending Approval ({{ pendingAttendees.length }})</v-tab>
      <v-tab value="approved">Approved ({{ approvedAttendees.length }})</v-tab>
      <v-tab value="paid">Paid ({{ paidAttendees.length }})</v-tab>
      <v-tab value="rejected">Rejected ({{ rejectedAttendees.length }})</v-tab>
    </v-tabs>

    <v-card>
      <v-window v-model="tab">
        <v-window-item value="pending">
          <v-data-table
            :headers="pendingHeaders"
            :items="pendingAttendees"
            :loading="isLoading"
            item-value="registration_id"
            show-expand
            v-model:expanded="expanded"
          >
            <template v-slot:expanded-row="{ columns, item }">
              <tr>
                <td :colspan="columns.length">
                  <div class="pa-4">
                    <h4 class="text-subtitle-1 font-weight-bold mb-2">Additional Form Responses</h4>
                    <div v-if="item.form_responses && Object.keys(item.form_responses).length">
                      <div v-for="(value, key) in item.form_responses" :key="key" class="mb-2 d-flex align-center">
                        <strong class="text-capitalize mr-2">{{ key.replace(/_/g, ' ') }}:</strong>
                        <span>{{ value }}</span>
                        <template v-if="typeof value === 'string' && isFileUrl(value)">
                          <v-btn
                            class="ml-2"
                            variant="tonal"
                            size="small"
                            prepend-icon="mdi-download"
                            @click="viewFile(value)"
                          >
                            View File
                          </v-btn>
                        </template>
                      </div>
                    </div>
                    <div v-else>
                      <p>No additional information was submitted for this application.</p>
                    </div>
                  </div>
                </td>
              </tr>
            </template>

            <template v-slot:item.actions="{ item }">
              <v-btn @click="handleApproval(item, 'approve')" icon="mdi-check" color="success" variant="text" size="small" class="mr-2" title="Approve"></v-btn>
              <v-btn @click="handleApproval(item, 'reject')" icon="mdi-close" color="error" variant="text" size="small" title="Reject"></v-btn>
            </template>
          </v-data-table>
        </v-window-item>

        <!-- Other Tabs: Approved, Paid, Rejected -->
        <v-window-item v-for="status in ['approved', 'paid', 'rejected']" :key="status" :value="status">
            <v-data-table
                :headers="status === 'approved' || status === 'rejected' ? attendeeHeadersWithRevert : attendeeHeaders"
                :items="status === 'approved' ? approvedAttendees : (status === 'paid' ? paidAttendees : rejectedAttendees)"
                :loading="isLoading"
                item-value="registration_id"
                show-expand
                v-model:expanded="expanded"
            >
                <template v-slot:expanded-row="{ columns, item }">
                    <tr>
                        <td :colspan="columns.length">
                            <div class="pa-4">
                                <h4 class="text-subtitle-1 font-weight-bold mb-2">Additional Form Responses</h4>
                                <div v-if="item.form_responses && Object.keys(item.form_responses).length">
                                    <div v-for="(value, key) in item.form_responses" :key="key" class="mb-2 d-flex align-center">
                                        <strong class="text-capitalize mr-2">{{ key.replace(/_/g, ' ') }}:</strong>
                                        <span>{{ value }}</span>
                                        <template v-if="typeof value === 'string' && isFileUrl(value)">
                                            <v-btn
                                                class="ml-2"
                                                variant="tonal"
                                                size="small"
                                                prepend-icon="mdi-download"
                                                @click="viewFile(value)"
                                            >
                                                View File
                                            </v-btn>
                                        </template>
                                    </div>
                                </div>
                                <div v-else>
                                    <p>No additional information was submitted for this application.</p>
                                </div>
                            </div>
                        </td>
                    </tr>
                </template>

                <template v-slot:item.actions="{ item }">
                  <v-btn @click="handleRevert(item)" icon="mdi-undo" color="warning" variant="text" size="small" title="Revert to Pending"></v-btn>
                </template>
            </v-data-table>
        </v-window-item>
      </v-window>
    </v-card>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>

    <v-dialog v-model="confirmDialog.show" max-width="500">
      <v-card>
        <v-card-title class="text-h5">
          {{ confirmDialog.action === 'approve' ? 'Approve' : 'Reject' }} Candidate?
        </v-card-title>
        <v-card-text>
          Are you sure you want to {{ confirmDialog.action }} <strong>{{ confirmDialog.attendeeName }}</strong>?
          This action will send a notification to the candidate.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="confirmDialog.show = false">
            Cancel
          </v-btn>
          <v-btn
            :color="confirmDialog.action === 'approve' ? 'success' : 'error'"
            variant="flat"
            @click="confirmApproval"
          >
            {{ confirmDialog.action === 'approve' ? 'Approve' : 'Reject' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="revertDialog.show" max-width="500">
      <v-card>
        <v-card-title class="text-h5">
          Revert to Pending Approval?
        </v-card-title>
        <v-card-text>
          Are you sure you want to revert <strong>{{ revertDialog.attendeeName }}</strong> back to pending approval?
          No notification will be sent to the candidate.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="revertDialog.show = false">
            Cancel
          </v-btn>
          <v-btn
            color="warning"
            variant="flat"
            @click="confirmRevert"
          >
            Revert to Pending
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import { EventService } from '@/services/EventService.js';
import { AdminService } from '@/services/AdminService.js';
import { UploadService } from '@/services/UploadService.js';


const route = useRoute();
const tab = ref('pending');
const allAttendees = ref([]);
const eventTitle = ref('');
const isLoading = ref(false);
const expanded = ref([]);
const snackbar = ref({ show: false, text: '', color: '' });
const confirmDialog = ref({
  show: false,
  action: '',
  attendee: null,
  attendeeName: ''
});
const revertDialog = ref({
  show: false,
  attendee: null,
  attendeeName: ''
});

watch(tab, () => {
  expanded.value = [];
});

const pendingAttendees = computed(() => allAttendees.value.filter(a => a.status === 'Pending Approval'));
const approvedAttendees = computed(() => allAttendees.value.filter(a => a.status === 'Approved'));
const paidAttendees = computed(() => allAttendees.value.filter(a => a.status === 'Paid'));
const rejectedAttendees = computed(() => allAttendees.value.filter(a => a.status === 'Rejected'));

const attendeeHeaders = ref([
  { title: 'Full Name', key: 'user.full_name' },
  { title: 'Email', key: 'user.email' },
  { title: 'Registration Date', key: 'registration_date' },
  { title: 'Degree', key: 'user.degree' },
  { title: 'Year', key: 'user.study_year' },
  // { title: 'CV', key: 'user.cv_url', sortable: false},



]);
const pendingHeaders = ref([...attendeeHeaders.value, { title: 'Actions', key: 'actions', sortable: false, align: 'end' }]);
const attendeeHeadersWithRevert = ref([...attendeeHeaders.value, { title: 'Actions', key: 'actions', sortable: false, align: 'end' }]);

async function fetchAttendees() {
  isLoading.value = true;
  const eventId = route.params.id;
  try {
    const response = await EventService.getEventRegistrations(eventId);
    allAttendees.value = response.data;
    expanded.value = []; 
  } catch (error) {
    console.error("Failed to fetch attendees:", error);
    snackbar.value = { show: true, text: 'Failed to load attendees.', color: 'error' };
  } finally {
    isLoading.value = false;
  }
}

function handleApproval(attendee, action) {
  confirmDialog.value = {
    show: true,
    action: action,
    attendee: attendee,
    attendeeName: attendee.user?.full_name || attendee.user?.email || 'this candidate'
  };
}

async function confirmApproval() {
  const { attendee, action } = confirmDialog.value;
  confirmDialog.value.show = false;

  const actionVerb = action === 'approve' ? 'Approving' : 'Rejecting';
  const successVerb = action === 'approve' ? 'Approved' : 'Rejected';

  try {
    if (action === 'approve') {
      await AdminService.approveRegistration(attendee.registration_id);
    } else {
      await AdminService.rejectRegistration(attendee.registration_id);
    }
    snackbar.value = { show: true, text: `Applicant ${successVerb}.`, color: 'success' };
    await fetchAttendees();
  } catch (error) {
    console.error(`${actionVerb} failed:`, error);
    snackbar.value = { show: true, text: `Failed to ${action} applicant.`, color: 'error' };
  }
}

function handleRevert(attendee) {
  revertDialog.value = {
    show: true,
    attendee: attendee,
    attendeeName: attendee.user?.full_name || attendee.user?.email || 'this candidate'
  };
}

async function confirmRevert() {
  const { attendee } = revertDialog.value;
  revertDialog.value.show = false;

  try {
    await AdminService.revertRegistrationToPending(attendee.registration_id);
    snackbar.value = { show: true, text: 'Registration reverted to pending approval.', color: 'success' };
    await fetchAttendees();
  } catch (error) {
    console.error('Revert failed:', error);
    snackbar.value = { show: true, text: 'Failed to revert registration.', color: 'error' };
  }
}
function isFileUrl(value) {
  if (!value) return false;
  if (value.startsWith('http')) return true;
  if (value.startsWith('user_uploads/')) return true;
  return false;
}

async function viewFile(fileValue) {
  try {
    if (fileValue.startsWith('http')) {
      window.open(fileValue, '_blank');
    } else {
      const response = await UploadService.getPresignedUrl(fileValue);
      window.open(response.data.url, '_blank');
    }
  } catch (error) {
    console.error("Could not open file", error);
    snackbar.value = { show: true, text: 'Could not open file.', color: 'error' };
  }
}

onMounted(() => {
  fetchAttendees();
});
</script>