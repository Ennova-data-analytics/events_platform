<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex justify-space-between align-center">
      <span>Feedback</span>
      <div class="d-flex align-center gap-2">
        <!-- QR template selector + modal -->
        <v-menu v-if="attachedTemplates.length > 1" offset-y>
          <template #activator="{ props: menuProps }">
            <v-btn color="primary" prepend-icon="mdi-qrcode" v-bind="menuProps">
              Show QR Code
            </v-btn>
          </template>
          <v-list density="compact">
            <v-list-subheader>Select template</v-list-subheader>
            <v-list-item
              v-for="tmpl in attachedTemplates"
              :key="tmpl.template_id"
              :title="tmpl.template_name"
              @click="openQrFor(tmpl.template_id)"
            >
              <template #append>
                <v-chip v-if="tmpl.is_primary" size="x-small" color="primary" label>Primary</v-chip>
              </template>
            </v-list-item>
          </v-list>
        </v-menu>
        <QRCodeModal
          v-else-if="hasFeedbackTemplate || attachedTemplates.length === 1"
          :event-id="eventId"
          :template-id="qrTemplateId"
        />

        <v-btn
          color="success"
          prepend-icon="mdi-send"
          @click="showSendDialog = true"
          :disabled="!attachedTemplates.length"
        >
          Send Feedback
        </v-btn>
      </div>
    </v-card-title>

    <v-card-text>
      <!-- Templates panel -->
      <EventFeedbackTemplatesPanel
        :event-id="eventId"
        class="mb-4"
        @updated="onTemplatesUpdated"
        ref="templatesPanelRef"
      />

      <!-- Invitation stats -->
      <div v-if="invitationStats.length" class="mb-4">
        <div class="text-subtitle-2 font-weight-bold mb-2">Invitation Tracker</div>
        <v-table density="compact">
          <thead>
            <tr>
              <th>Template</th>
              <th class="text-center">Sent</th>
              <th class="text-center">Responded</th>
              <th class="text-center">Pending</th>
              <th class="text-right">Resend</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in invitationStats" :key="s.template_id">
              <td>{{ s.template_name }}</td>
              <td class="text-center">{{ s.sent }}</td>
              <td class="text-center">
                <span :class="s.responded > 0 ? 'text-success' : ''">{{ s.responded }}</span>
              </td>
              <td class="text-center">
                <span :class="s.pending > 0 ? 'text-warning' : ''">{{ s.pending }}</span>
              </td>
              <td class="text-right">
                <v-btn
                  size="x-small"
                  variant="text"
                  color="primary"
                  :loading="resendingTemplateId === s.template_id"
                  :disabled="s.pending === 0"
                  @click="resend(s.template_id)"
                >
                  Resend
                </v-btn>
              </td>
            </tr>
          </tbody>
        </v-table>
      </div>

      <div v-if="isLoading">
        <v-progress-linear indeterminate color="primary"></v-progress-linear>
      </div>

      <div v-else-if="!hasFeedbackTemplate && !attachedTemplates.length">
        <v-alert type="info" variant="tonal">
          No feedback template attached to this event. Use the panel above to attach one.
        </v-alert>
      </div>

      <div v-else>
        <!-- Statistics Overview -->
        <v-row class="mb-4">
          <v-col cols="12" sm="4">
            <v-card variant="tonal" color="primary">
              <v-card-text class="text-center">
                <div class="text-h4">{{ stats.total_responses || 0 }}</div>
                <div class="text-caption">Total Responses</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" sm="4">
            <v-card variant="tonal" color="success">
              <v-card-text class="text-center">
                <div class="text-h4">{{ stats.response_rate ? stats.response_rate.toFixed(1) : 0 }}%</div>
                <div class="text-caption">Response Rate</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" sm="4">
            <v-card variant="tonal" color="info">
              <v-card-text class="text-center">
                <div class="text-h4">{{ stats.total_registrations || 0 }}</div>
                <div class="text-caption">Total Registrations</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Field Statistics - Grouped by Template -->
        <div v-if="hasTemplateGroups" class="mb-4">
          <h3 class="text-h6 mb-3">Response Summary</h3>
          <div v-for="group in stats.template_groups" :key="group.template_id ?? 'other'" class="mb-5">
            <div class="d-flex align-center mb-2">
              <h4 class="text-subtitle-1 font-weight-bold">{{ group.template_name }}</h4>
              <v-chip size="small" class="ml-2">{{ group.response_count }} responses</v-chip>
            </div>
            <v-expansion-panels>
              <v-expansion-panel
                v-for="(fieldData, fieldName) in group.field_statistics"
                :key="fieldName"
              >
                <v-expansion-panel-title>
                  {{ fieldName }}
                  <template v-slot:actions>
                    <v-chip size="small">{{ fieldData.response_count }} responses</v-chip>
                  </template>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <div v-if="fieldData.average !== undefined">
                    <p><strong>Average:</strong> {{ fieldData.average.toFixed(2) }}</p>
                    <p><strong>Min:</strong> {{ fieldData.min }} | <strong>Max:</strong> {{ fieldData.max }}</p>
                  </div>
                  <div v-if="fieldData.value_distribution">
                    <p class="mb-2"><strong>Distribution:</strong></p>
                    <div v-for="(count, value) in fieldData.value_distribution" :key="value" class="mb-1">
                      <v-chip size="small" class="mr-2">{{ count }}</v-chip> {{ value }}
                    </div>
                  </div>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
            <v-divider v-if="stats.template_groups.indexOf(group) < stats.template_groups.length - 1" class="mt-4"></v-divider>
          </div>
        </div>

        <!-- Field Statistics - Flat -->
        <div v-else-if="Object.keys(stats.field_statistics || {}).length > 0" class="mb-4">
          <h3 class="text-h6 mb-3">Response Summary</h3>
          <v-expansion-panels>
            <v-expansion-panel
              v-for="(fieldData, fieldName) in stats.field_statistics"
              :key="fieldName"
            >
              <v-expansion-panel-title>
                {{ fieldName }}
                <template v-slot:actions>
                  <v-chip size="small">{{ fieldData.response_count }} responses</v-chip>
                </template>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="fieldData.average !== undefined">
                  <p><strong>Average:</strong> {{ fieldData.average.toFixed(2) }}</p>
                  <p><strong>Min:</strong> {{ fieldData.min }} | <strong>Max:</strong> {{ fieldData.max }}</p>
                </div>
                <div v-if="fieldData.value_distribution">
                  <p class="mb-2"><strong>Distribution:</strong></p>
                  <div v-for="(count, value) in fieldData.value_distribution" :key="value" class="mb-1">
                    <v-chip size="small" class="mr-2">{{ count }}</v-chip> {{ value }}
                  </div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>

        <!-- Recent Responses -->
        <div v-if="stats.recent_responses && stats.recent_responses.length > 0">
          <h3 class="text-h6 mb-3">Recent Responses</h3>
          <v-list>
            <v-list-item
              v-for="response in stats.recent_responses"
              :key="response.feedback_id"
            >
              <v-list-item-title>
                {{ response.is_anonymous ? 'Anonymous' : 'User' }}
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ new Date(response.submitted_at).toLocaleString() }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </div>

        <!-- View All Button -->
        <v-btn
          :to="{ name: 'admin-event-feedback', params: { id: eventId } }"
          color="primary"
          variant="outlined"
          block
          class="mt-4"
        >
          View All Feedback Responses
        </v-btn>
      </div>
    </v-card-text>
  </v-card>

  <!-- Hidden QR modal for multi-template menu selection -->
  <v-dialog v-model="qrDialogOpen" max-width="600">
    <v-card>
      <v-card-title class="d-flex justify-space-between align-center">
        <span>Feedback QR Code</span>
        <v-btn icon="mdi-close" variant="text" @click="qrDialogOpen = false" />
      </v-card-title>
      <v-card-text class="text-center py-6">
        <div v-if="qrLoading" class="py-8">
          <v-progress-circular indeterminate color="primary" />
        </div>
        <div v-else-if="qrImageUrl">
          <img :src="qrImageUrl" alt="QR Code" style="max-width:300px;width:100%;border:2px solid #e0e0e0;border-radius:8px;" class="mb-4" />
          <p class="text-body-2 mb-4">Scan to open the feedback form</p>
          <v-text-field :model-value="qrFeedbackUrl" readonly variant="outlined" density="compact" class="mb-4">
            <template #append-inner>
              <v-btn icon="mdi-content-copy" variant="text" size="small" @click="navigator.clipboard.writeText(qrFeedbackUrl)" />
            </template>
          </v-text-field>
          <v-btn color="primary" prepend-icon="mdi-download" block @click="downloadQr">Download QR Code</v-btn>
        </div>
        <v-alert v-else type="error">Failed to generate QR code</v-alert>
      </v-card-text>
    </v-card>
  </v-dialog>

  <!-- Send feedback invitations dialog -->
  <SendFeedbackDialog
    v-model="showSendDialog"
    :event-id="eventId"
    :attached-templates="attachedTemplates"
    :ticket-types="ticketTypes"
    @sent="onSent"
  />
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { FeedbackService } from '@/services/FeedbackService.js'
import QRCodeModal from './QRCodeModal.vue'
import EventFeedbackTemplatesPanel from './EventFeedbackTemplatesPanel.vue'
import SendFeedbackDialog from './SendFeedbackDialog.vue'

const props = defineProps({
  eventId: { type: Number, required: true },
  hasFeedbackTemplate: { type: Boolean, default: false },
  ticketTypes: { type: Array, default: () => [] },
})

const stats = ref({})
const isLoading = ref(false)
const attachedTemplates = ref([])
const invitationStats = ref([])
const resendingTemplateId = ref(null)
const showSendDialog = ref(false)
const templatesPanelRef = ref(null)

// QR for multi-template menu
const qrDialogOpen = ref(false)
const qrLoading = ref(false)
const qrImageUrl = ref(null)
const qrFeedbackUrl = ref('')
const qrTemplateId = computed(() => {
  const primary = attachedTemplates.value.find(t => t.is_primary)
  return primary?.template_id || attachedTemplates.value[0]?.template_id || null
})

const hasTemplateGroups = computed(() => stats.value.template_groups?.length > 0)

async function loadFeedbackStats() {
  if (!props.hasFeedbackTemplate && !attachedTemplates.value.length) {
    stats.value = {}
    return
  }
  isLoading.value = true
  try {
    const response = await FeedbackService.getFeedbackStatistics(props.eventId)
    stats.value = response.data
  } catch {
    // ignore
  } finally {
    isLoading.value = false
  }
}

async function loadAttachedTemplates() {
  try {
    const res = await FeedbackService.getEventFeedbackTemplates(props.eventId)
    attachedTemplates.value = res.data
  } catch {
    // ignore
  }
}

async function loadInvitationStats() {
  try {
    const res = await FeedbackService.getInvitationStats(props.eventId)
    invitationStats.value = res.data.stats
  } catch {
    // ignore
  }
}

async function onTemplatesUpdated() {
  await loadAttachedTemplates()
  await loadFeedbackStats()
}

async function resend(templateId) {
  resendingTemplateId.value = templateId
  try {
    await FeedbackService.resendInvitations(props.eventId, {
      template_id: templateId,
      non_responders_only: true,
    })
    await loadInvitationStats()
  } catch {
    // ignore
  } finally {
    resendingTemplateId.value = null
  }
}

async function openQrFor(templateId) {
  qrDialogOpen.value = true
  qrLoading.value = true
  qrImageUrl.value = null
  try {
    const qrRes = await FeedbackService.getFeedbackQRCode(props.eventId, templateId)
    const blob = new Blob([qrRes.data], { type: 'image/png' })
    qrImageUrl.value = URL.createObjectURL(blob)
    const urlRes = await FeedbackService.getFeedbackUrl(props.eventId, templateId)
    qrFeedbackUrl.value = urlRes.data.feedback_url
  } catch {
    // ignore
  } finally {
    qrLoading.value = false
  }
}

function downloadQr() {
  if (qrImageUrl.value) {
    const link = document.createElement('a')
    link.href = qrImageUrl.value
    link.download = `event_${props.eventId}_feedback_qr.png`
    link.click()
  }
}

async function onSent() {
  await loadInvitationStats()
}

watch(() => props.hasFeedbackTemplate, (v) => {
  if (v) loadFeedbackStats()
})

onMounted(async () => {
  await loadAttachedTemplates()
  await Promise.all([loadFeedbackStats(), loadInvitationStats()])
})
</script>
