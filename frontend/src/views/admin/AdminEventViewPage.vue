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
                        <template v-if="typeof value === 'string' && value.startsWith('user_uploads/')">
                          <v-btn
                            class="ml-2"
                            variant="tonal"
                            size="small"
                            prepend-icon="mdi-download"
                            @click="getViewableUrl(value)"
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
                :headers="attendeeHeaders"
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
                                        <template v-if="typeof value === 'string' && value.startsWith('user_uploads/')">
                                            <v-btn
                                                class="ml-2"
                                                variant="tonal"
                                                size="small"
                                                prepend-icon="mdi-download"
                                                @click="getViewableUrl(value)"
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
            </v-data-table>
        </v-window-item>
      </v-window>
    </v-card>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
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

const pendingAttendees = computed(() => allAttendees.value.filter(a => a.status === 'Pending Approval'));
const approvedAttendees = computed(() => allAttendees.value.filter(a => a.status === 'Approved'));
const paidAttendees = computed(() => allAttendees.value.filter(a => a.status === 'Paid'));
const rejectedAttendees = computed(() => allAttendees.value.filter(a => a.status === 'Rejected'));

const filteredAttendees = (status) => {
  return allAttendees.value.filter(a => a.status.toLowerCase().replace(' ', '') === status);
};

const attendeeHeaders = ref([
  { title: 'Full Name', key: 'user.full_name' },
  { title: 'Email', key: 'user.email' },
  { title: 'Registration Date', key: 'registration_date' },
  { title: 'Degree', key: 'user.degree' },
  { title: 'Year', key: 'user.study_year' },
  // { title: 'CV', key: 'user.cv_url', sortable: false},



]);
const pendingHeaders = ref([...attendeeHeaders.value, { title: 'Actions', key: 'actions', sortable: false, align: 'end' }]);

async function fetchAttendees() {
  isLoading.value = true;
  const eventId = route.params.id;
  try {
    const response = await EventService.getEventRegistrations(eventId);
    allAttendees.value = response.data;
  } catch (error) {
    console.error("Failed to fetch attendees:", error);
    snackbar.value = { show: true, text: 'Failed to load attendees.', color: 'error' };
  } finally {
    isLoading.value = false;
  }
}

async function handleApproval(attendee, action) {
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
async function getViewableUrl(fileKey) {
  try {
    const response = await UploadService.getPresignedUrl(fileKey);
    window.open(response.data.url, '_blank'); 
  } catch (error) {
    console.error("Could not get presigned URL", error);
    snackbar.value = { show: true, text: 'Could not open file.', color: 'error' };
  }
}

onMounted(() => {
  fetchAttendees();
});
</script>