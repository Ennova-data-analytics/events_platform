<template>
  <div>
    <div class="d-flex align-center mb-4">
      <v-btn icon="mdi-arrow-left" variant="text" to="/admin/events" class="mr-2"></v-btn>
      <h1 class="text-h5">Manage Attendees: {{ eventTitle }}</h1>
      <v-spacer></v-spacer>
      <v-btn
        color="primary"
        variant="tonal"
        @click="openBulkEmailDialog"
        prepend-icon="mdi-email-multiple"
        class="mr-2"
      >
        Send Bulk Email
      </v-btn>
      <v-btn
        :color="signupsEnabled ? 'success' : 'error'"
        variant="tonal"
        @click="toggleSignups"
        :loading="isTogglingSignups"
        prepend-icon="mdi-account-plus"
      >
        {{ signupsEnabled ? 'Signups Enabled' : 'Signups Disabled' }}
      </v-btn>
    </div>

    <v-tabs v-model="tab" bg-color="surface" class="mb-4">
      <v-tab value="pending">Pending Approval ({{ pendingAttendees.length }})</v-tab>
      <v-tab value="approved">Approved ({{ approvedAttendees.length }})</v-tab>
      <v-tab value="paid">Paid ({{ paidAttendees.length }})</v-tab>
      <v-tab value="rejected">Rejected ({{ rejectedAttendees.length }})</v-tab>
      <v-tab value="discounts">Discount Codes</v-tab>
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
              <v-btn @click="handleApproval(item, 'reject')" icon="mdi-close" color="error" variant="text" size="small" class="mr-2" title="Reject"></v-btn>
              <v-btn @click="handleDelete(item)" icon="mdi-delete" color="error" variant="text" size="small" title="Delete"></v-btn>
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
                  <v-btn
                    v-if="status === 'approved'"
                    @click="handleMarkPaid(item)"
                    icon="mdi-cash-check"
                    color="success"
                    variant="text"
                    size="small"
                    class="mr-2"
                    title="Mark as Paid"
                  ></v-btn>
                  <v-btn @click="handleRevert(item)" icon="mdi-undo" color="warning" variant="text" size="small" title="Revert to Pending"></v-btn>
                </template>
            </v-data-table>
        </v-window-item>

        <!-- Discount Codes Tab -->
        <v-window-item value="discounts">
          <DiscountCodeManager v-if="eventId" :event-id="parseInt(eventId)" />
        </v-window-item>
      </v-window>
    </v-card>

    <!-- Feedback Section -->
    <div class="mt-6">
      <FeedbackSection
        v-if="eventId"
        :key="feedbackSectionKey"
        :event-id="parseInt(eventId)"
        :has-feedback-template="hasFeedbackTemplate"
      />
    </div>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>

    <v-dialog v-model="confirmDialog.show" max-width="500">
      <v-card>
        <v-card-title class="text-h5">
          {{ confirmDialog.action === 'approve' ? 'Approve' : 'Reject' }} Candidate?
        </v-card-title>
        <v-card-text>
          <p class="mb-4">
            Are you sure you want to {{ confirmDialog.action }} <strong>{{ confirmDialog.attendeeName }}</strong>?
            This action will send a notification to the candidate.
          </p>

          <v-text-field
            v-if="confirmDialog.action === 'approve'"
            v-model.number="customAmount"
            label="Amount to charge (€)"
            type="number"
            step="0.01"
            min="0"
            :hint="eventPrice !== null ? `Event price: €${eventPrice}. Leave empty to use event price.` : 'Leave empty to use event price.'"
            persistent-hint
            density="comfortable"
            class="mt-2"
          ></v-text-field>
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

    <v-dialog v-model="deleteDialog.show" max-width="500">
      <v-card>
        <v-card-title class="text-h5">
          Delete Registration?
        </v-card-title>
        <v-card-text>
          Are you sure you want to permanently delete the registration for <strong>{{ deleteDialog.attendeeName }}</strong>?
          This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="deleteDialog.show = false">
            Cancel
          </v-btn>
          <v-btn
            color="error"
            variant="flat"
            @click="confirmDelete"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="markPaidDialog.show" max-width="500">
      <v-card>
        <v-card-title class="text-h5">
          Mark as Paid?
        </v-card-title>
        <v-card-text>
          Are you sure you want to mark the registration for <strong>{{ markPaidDialog.attendeeName }}</strong> as paid?
          This indicates that payment has been received (e.g., through offline payment or manual transfer).
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="markPaidDialog.show = false">
            Cancel
          </v-btn>
          <v-btn
            color="success"
            variant="flat"
            @click="confirmMarkPaid"
          >
            Mark as Paid
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bulk Email Dialog -->
    <v-dialog v-model="bulkEmailDialog.show" max-width="700" scrollable>
      <v-card>
        <v-card-title class="text-h5">
          Send Bulk Email
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            This will send an email to all attendees with the selected status(es).
          </v-alert>

          <v-select
            v-model="bulkEmailDialog.recipientStatuses"
            label="Recipient Status(es)"
            :items="statusOptions"
            multiple
            chips
            closable-chips
            required
            density="comfortable"
            class="mb-4"
            :hint="`${getRecipientCount()} recipient(s) selected`"
            persistent-hint
          ></v-select>

          <v-text-field
            v-model="bulkEmailDialog.subject"
            label="Email Subject"
            required
            density="comfortable"
            class="mb-4"
          ></v-text-field>

          <v-textarea
            v-model="bulkEmailDialog.body"
            label="Email Body (Plain Text)"
            rows="8"
            required
            density="comfortable"
            class="mb-4"
          ></v-textarea>

          <v-alert v-if="bulkEmailDialog.result" :type="bulkEmailDialog.result.success ? 'success' : 'error'" class="mt-4">
            <div v-if="bulkEmailDialog.result.success">
              Successfully sent {{ bulkEmailDialog.result.emails_sent }} of {{ bulkEmailDialog.result.total_recipients }} emails.
            </div>
            <div v-if="bulkEmailDialog.result.failed_emails && bulkEmailDialog.result.failed_emails.length > 0">
              <div class="font-weight-bold">Failed to send to:</div>
              <ul>
                <li v-for="email in bulkEmailDialog.result.failed_emails" :key="email">{{ email }}</li>
              </ul>
            </div>
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="closeBulkEmailDialog">
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="flat"
            @click="sendBulkEmail"
            :loading="bulkEmailDialog.sending"
            :disabled="!canSendBulkEmail"
          >
            Send Email
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import { EventService } from '@/services/EventService.js';
import { AdminService } from '@/services/AdminService.js';
import { UploadService } from '@/services/UploadService.js';
import FeedbackSection from '@/components/feedback/FeedbackSection.vue';
import DiscountCodeManager from '@/components/admin/DiscountCodeManager.vue';


const route = useRoute();
const eventId = computed(() => route.params.id);
const tab = ref('pending');
const allAttendees = ref([]);
const eventTitle = ref('');
const eventPrice = ref(null);
const customAmount = ref(null);
const hasFeedbackTemplate = ref(false);
const feedbackSectionKey = ref(0);
const isLoading = ref(false);
const expanded = ref([]);
const signupsEnabled = ref(true);
const isTogglingSignups = ref(false);
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
const deleteDialog = ref({
  show: false,
  attendee: null,
  attendeeName: ''
});
const markPaidDialog = ref({
  show: false,
  attendee: null,
  attendeeName: ''
});
const bulkEmailDialog = ref({
  show: false,
  recipientStatuses: ['Approved', 'Paid'],
  subject: '',
  body: '',
  sending: false,
  result: null
});

const statusOptions = ['Pending Approval', 'Approved', 'Paid', 'Rejected'];

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
  { title: 'Ticket Type', key: 'ticket_type.name' },
  { title: 'Registration Date', key: 'registration_date' },
  { title: 'Degree', key: 'user.degree' },
  { title: 'Year', key: 'user.study_year' },
  // { title: 'CV', key: 'user.cv_url', sortable: false},



]);
const pendingHeaders = ref([...attendeeHeaders.value, { title: 'Actions', key: 'actions', sortable: false, align: 'end' }]);
const attendeeHeadersWithRevert = ref([...attendeeHeaders.value, { title: 'Actions', key: 'actions', sortable: false, align: 'end' }]);

async function fetchEventDetails() {
  const eventIdValue = route.params.id;
  try {
    const response = await EventService.getEventById(eventIdValue);
    eventTitle.value = response.data.event_name;
    eventPrice.value = response.data.price_euros;
    signupsEnabled.value = response.data.signups_enabled ?? true;
    hasFeedbackTemplate.value = !!response.data.feedback_template_id;
    // Force FeedbackSection to re-render when feedback template changes
    feedbackSectionKey.value++;
  } catch (error) {
    console.error("Failed to fetch event details:", error);
  }
}

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
  customAmount.value = null; // Reset custom amount
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
      await AdminService.approveRegistration(attendee.registration_id, customAmount.value);
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

function handleDelete(attendee) {
  deleteDialog.value = {
    show: true,
    attendee: attendee,
    attendeeName: attendee.user?.full_name || attendee.user?.email || 'Unknown'
  };
}

async function confirmDelete() {
  const { attendee } = deleteDialog.value;
  deleteDialog.value.show = false;

  try {
    await AdminService.deleteRegistration(attendee.registration_id);
    snackbar.value = { show: true, text: 'Registration deleted successfully.', color: 'success' };
    await fetchAttendees();
  } catch (error) {
    console.error('Delete failed:', error);
    snackbar.value = { show: true, text: 'Failed to delete registration.', color: 'error' };
  }
}

function handleMarkPaid(attendee) {
  markPaidDialog.value = {
    show: true,
    attendee: attendee,
    attendeeName: attendee.user?.full_name || attendee.user?.email || 'Unknown'
  };
}

async function confirmMarkPaid() {
  const { attendee } = markPaidDialog.value;
  markPaidDialog.value.show = false;

  try {
    await AdminService.markRegistrationPaid(attendee.registration_id);
    snackbar.value = { show: true, text: 'Registration marked as paid successfully.', color: 'success' };
    await fetchAttendees();
  } catch (error) {
    console.error('Mark paid failed:', error);
    snackbar.value = { show: true, text: error.response?.data?.detail || 'Failed to mark registration as paid.', color: 'error' };
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

async function toggleSignups() {
  isTogglingSignups.value = true;
  try {
    const response = await EventService.toggleSignups(route.params.id);
    signupsEnabled.value = response.data.signups_enabled;
    snackbar.value = {
      show: true,
      text: `Signups ${signupsEnabled.value ? 'enabled' : 'disabled'} successfully.`,
      color: 'success'
    };
  } catch (error) {
    console.error("Failed to toggle signups:", error);
    snackbar.value = { show: true, text: 'Failed to toggle signups.', color: 'error' };
  } finally {
    isTogglingSignups.value = false;
  }
}

function openBulkEmailDialog() {
  bulkEmailDialog.value = {
    show: true,
    recipientStatuses: ['Approved', 'Paid'],
    subject: '',
    body: '',
    sending: false,
    result: null
  };
}

function closeBulkEmailDialog() {
  bulkEmailDialog.value.show = false;
}

function getRecipientCount() {
  if (!bulkEmailDialog.value.recipientStatuses || bulkEmailDialog.value.recipientStatuses.length === 0) {
    return 0;
  }
  return allAttendees.value.filter(a =>
    bulkEmailDialog.value.recipientStatuses.includes(a.status)
  ).length;
}

const canSendBulkEmail = computed(() => {
  return bulkEmailDialog.value.recipientStatuses.length > 0 &&
         bulkEmailDialog.value.subject.trim() !== '' &&
         bulkEmailDialog.value.body.trim() !== '' &&
         !bulkEmailDialog.value.sending;
});

async function sendBulkEmail() {
  bulkEmailDialog.value.sending = true;
  bulkEmailDialog.value.result = null;

  try {
    const emailData = {
      event_id: parseInt(route.params.id),
      recipient_statuses: bulkEmailDialog.value.recipientStatuses,
      subject: bulkEmailDialog.value.subject,
      body: bulkEmailDialog.value.body
    };

    const response = await AdminService.sendBulkEmail(route.params.id, emailData);
    bulkEmailDialog.value.result = response.data;

    if (response.data.success) {
      snackbar.value = {
        show: true,
        text: `Successfully sent ${response.data.emails_sent} email(s).`,
        color: 'success'
      };
    } else {
      snackbar.value = {
        show: true,
        text: 'Some emails failed to send. Check the details above.',
        color: 'warning'
      };
    }
  } catch (error) {
    console.error('Failed to send bulk email:', error);
    snackbar.value = {
      show: true,
      text: error.response?.data?.detail || 'Failed to send bulk email.',
      color: 'error'
    };
    bulkEmailDialog.value.result = {
      success: false,
      emails_sent: 0,
      total_recipients: 0,
      failed_emails: []
    };
  } finally {
    bulkEmailDialog.value.sending = false;
  }
}

// Watch for route changes to refresh data
watch(() => route.params.id, () => {
  fetchEventDetails();
  fetchAttendees();
});

onMounted(() => {
  fetchEventDetails();
  fetchAttendees();
});

// Refresh when component is reactivated (e.g., navigating back from edit page)
onActivated(() => {
  fetchEventDetails();
  fetchAttendees();
});
</script>