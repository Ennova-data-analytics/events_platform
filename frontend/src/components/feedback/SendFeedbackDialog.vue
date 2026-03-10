<template>
  <v-dialog v-model="model" max-width="640" persistent scrollable>
    <v-card>
      <v-card-title class="d-flex align-center justify-space-between pa-4">
        <span>Send Feedback Invitations</span>
        <v-btn icon="mdi-close" variant="text" @click="close" />
      </v-card-title>

      <v-divider />

      <v-card-text style="min-height: 380px;">
        <!-- Step 1: Choose template -->
        <div v-if="step === 1">
          <p class="text-body-2 text-medium-emphasis mb-4">
            Select which feedback template to send. Only templates attached to this event are available.
          </p>
          <v-select
            v-model="selectedTemplateId"
            :items="attachedTemplates"
            item-title="template_name"
            item-value="template_id"
            label="Feedback template *"
            variant="outlined"
            density="compact"
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps">
                <template #append>
                  <v-chip v-if="item.raw.is_primary" size="x-small" color="primary" label>Primary</v-chip>
                </template>
              </v-list-item>
            </template>
          </v-select>
        </div>

        <!-- Step 2: Choose audience -->
        <div v-if="step === 2">
          <v-tabs v-model="audienceTab" color="primary" class="mb-4">
            <v-tab value="registered">Registered Attendees</v-tab>
            <v-tab value="external">External Participants</v-tab>
          </v-tabs>

          <!-- Registered attendees filters -->
          <div v-if="audienceTab === 'registered'">
            <p class="text-body-2 text-medium-emphasis mb-3">
              Filter which registrations should receive the invitation.
            </p>

            <v-select
              v-model="filters.statuses"
              :items="statusOptions"
              label="Registration statuses"
              multiple
              chips
              closable-chips
              variant="outlined"
              density="compact"
              class="mb-3"
              hint="Leave empty to include all statuses"
              persistent-hint
            />

            <v-select
              v-if="ticketTypes.length"
              v-model="filters.ticket_type_ids"
              :items="ticketTypes"
              item-title="name"
              item-value="ticket_type_id"
              label="Ticket types"
              multiple
              chips
              closable-chips
              variant="outlined"
              density="compact"
              class="mb-3"
              hint="Leave empty to include all ticket types"
              persistent-hint
            />

            <v-checkbox
              v-model="filters.checked_in_only"
              label="Only attendees who checked in"
              density="compact"
              hide-details
              class="mb-3"
            />

            <v-btn
              variant="tonal"
              size="small"
              :loading="previewing"
              @click="previewRecipients"
            >
              Preview recipients
            </v-btn>

            <v-alert
              v-if="preview !== null"
              class="mt-3"
              :type="preview.recipient_count === 0 ? 'warning' : 'info'"
              density="compact"
              variant="tonal"
            >
              <span v-if="preview.recipient_count === 0">No matching registrations found.</span>
              <span v-else>
                <strong>{{ preview.recipient_count }}</strong> recipient{{ preview.recipient_count !== 1 ? 's' : '' }} will receive this invitation.
              </span>
            </v-alert>
          </div>

          <!-- External participants -->
          <div v-if="audienceTab === 'external'">
            <p class="text-body-2 text-medium-emphasis mb-3">
              Enter email addresses manually or upload a CSV file.
              Supported CSV columns: <code>email</code>, <code>name</code> (optional).
            </p>

            <v-textarea
              v-model="externalEmailsRaw"
              label="Email addresses (one per line, optionally: Name &lt;email&gt;)"
              variant="outlined"
              rows="5"
              density="compact"
              class="mb-3"
              placeholder="John Doe &lt;john@example.com&gt;&#10;jane@example.com"
              @input="parseManualEmails"
            />

            <div class="d-flex align-center gap-3 mb-3">
              <v-btn
                variant="tonal"
                size="small"
                prepend-icon="mdi-upload"
                @click="triggerCsvUpload"
              >
                Upload CSV
              </v-btn>
              <span v-if="csvFileName" class="text-body-2 text-medium-emphasis">
                {{ csvFileName }}
              </span>
            </div>
            <input
              ref="csvInput"
              type="file"
              accept=".csv,text/csv"
              style="display:none"
              @change="handleCsvUpload"
            />

            <v-alert
              v-if="totalExternalCount > 0"
              type="info"
              density="compact"
              variant="tonal"
              class="mt-2"
            >
              <strong>{{ totalExternalCount }}</strong> unique recipient{{ totalExternalCount !== 1 ? 's' : '' }} loaded.
            </v-alert>
          </div>
        </div>

        <!-- Step 3: Confirm -->
        <div v-if="step === 3">
          <v-card variant="tonal" color="primary" class="mb-4">
            <v-card-text>
              <div class="d-flex flex-column gap-2">
                <div class="d-flex justify-space-between">
                  <span class="text-body-2 font-weight-medium">Template</span>
                  <span class="text-body-2">{{ selectedTemplate?.template_name }}</span>
                </div>
                <div class="d-flex justify-space-between">
                  <span class="text-body-2 font-weight-medium">Audience</span>
                  <span class="text-body-2 text-capitalize">{{ audienceTab }}</span>
                </div>
                <div v-if="audienceTab === 'registered' && preview" class="d-flex justify-space-between">
                  <span class="text-body-2 font-weight-medium">Recipients</span>
                  <span class="text-body-2">{{ preview.recipient_count }}</span>
                </div>
                <div v-if="audienceTab === 'external'" class="d-flex justify-space-between">
                  <span class="text-body-2 font-weight-medium">Recipients</span>
                  <span class="text-body-2">{{ externalEntries.length }}</span>
                </div>
                <div class="d-flex justify-space-between">
                  <span class="text-body-2 font-weight-medium">Link expiry</span>
                  <span class="text-body-2">14 days</span>
                </div>
              </div>
            </v-card-text>
          </v-card>

          <v-alert v-if="sendResult" :type="sendResult.failed_count > 0 ? 'warning' : 'success'" class="mb-3" variant="tonal">
            Sent to <strong>{{ sendResult.sent_count }}</strong> recipient{{ sendResult.sent_count !== 1 ? 's' : '' }}.
            <span v-if="sendResult.failed_count > 0"> {{ sendResult.failed_count }} failed.</span>
          </v-alert>
        </div>
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-btn v-if="step > 1 && !sendResult" variant="text" @click="step--">Back</v-btn>
        <v-spacer />
        <v-btn variant="text" @click="close">{{ sendResult ? 'Close' : 'Cancel' }}</v-btn>
        <v-btn
          v-if="step < 3 && !sendResult"
          color="primary"
          :disabled="!canProceed"
          @click="step++"
        >
          Next
        </v-btn>
        <v-btn
          v-if="step === 3 && !sendResult"
          color="primary"
          :loading="sending"
          :disabled="!canSend"
          @click="send"
        >
          Send Invitations
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { FeedbackService } from '@/services/FeedbackService'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  eventId: { type: Number, required: true },
  attachedTemplates: { type: Array, default: () => [] },
  ticketTypes: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'sent'])

const model = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const step = ref(1)
const selectedTemplateId = ref(null)
const audienceTab = ref('registered')
const previewing = ref(false)
const sending = ref(false)
const sendResult = ref(null)
const preview = ref(null)

const filters = ref({
  statuses: ['Approved', 'Paid'],
  ticket_type_ids: [],
  checked_in_only: false,
})

const externalEmailsRaw = ref('')
const externalEntries = ref([])
const csvFileName = ref('')
const csvParsedEntries = ref([])
const csvInput = ref(null)

const statusOptions = ['Pending Approval', 'Approved', 'Paid', 'Rejected', 'Cancelled']

const selectedTemplate = computed(() =>
  props.attachedTemplates.find(t => t.template_id === selectedTemplateId.value) || null
)

const totalExternalCount = computed(() => {
  const manualEmails = new Set(externalEntries.value.map(e => e.email))
  const csvOnly = csvParsedEntries.value.filter(e => !manualEmails.has(e.email))
  return externalEntries.value.length + csvOnly.length
})

const canProceed = computed(() => {
  if (step.value === 1) return !!selectedTemplateId.value
  if (step.value === 2) {
    if (audienceTab.value === 'registered') return true
    return totalExternalCount.value > 0
  }
  return true
})

const canSend = computed(() => {
  if (audienceTab.value === 'registered') return preview.value && preview.value.recipient_count > 0
  return totalExternalCount.value > 0
})

function parseManualEmails() {
  const lines = externalEmailsRaw.value.split('\n').map(l => l.trim()).filter(Boolean)
  const seen = new Set()
  const result = []
  for (const line of lines) {
    // Match "Name <email>" or plain "email"
    const match = line.match(/^(?:(.+?)\s+)?<?([^\s<>@]+@[^\s<>@]+\.[^\s<>@]+)>?$/)
    if (match) {
      const email = match[2].toLowerCase()
      if (!seen.has(email)) {
        seen.add(email)
        result.push({ email, name: match[1]?.trim() || null })
      }
    }
  }
  externalEntries.value = result
}

function triggerCsvUpload() {
  csvInput.value?.click()
}

async function handleCsvUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  csvFileName.value = file.name
  const buffer = await file.arrayBuffer()

  // Parse CSV client-side to show accurate recipient count
  const text = new TextDecoder().decode(buffer)
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean)
  if (lines.length > 1) {
    const header = lines[0].split(',').map(h => h.trim().toLowerCase())
    const emailIdx = header.indexOf('email')
    const nameIdx = header.indexOf('name')
    const seen = new Set()
    const parsed = []
    for (const line of lines.slice(1)) {
      const cols = line.split(',').map(c => c.trim().replace(/^"|"$/g, ''))
      const email = emailIdx >= 0 ? cols[emailIdx]?.toLowerCase() : ''
      const name = nameIdx >= 0 ? cols[nameIdx] || null : null
      if (email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && !seen.has(email)) {
        seen.add(email)
        parsed.push({ email, name })
      }
    }
    csvParsedEntries.value = parsed
  } else {
    csvParsedEntries.value = []
  }
}

async function previewRecipients() {
  previewing.value = true
  preview.value = null
  try {
    const res = await FeedbackService.previewInvitations(props.eventId, {
      template_id: selectedTemplateId.value,
      audience: 'registered',
      filters: filters.value,
    })
    preview.value = res.data
  } catch {
    // ignore
  } finally {
    previewing.value = false
  }
}

async function send() {
  sending.value = true
  try {
    const payload = {
      template_id: selectedTemplateId.value,
      audience: audienceTab.value,
    }
    if (audienceTab.value === 'registered') {
      payload.filters = filters.value
    } else {
      const manualEmails = new Set(externalEntries.value.map(e => e.email))
      const csvOnly = csvParsedEntries.value.filter(e => !manualEmails.has(e.email))
      payload.externals = [...externalEntries.value, ...csvOnly]
    }
    const res = await FeedbackService.sendInvitations(props.eventId, payload)
    sendResult.value = res.data
    emit('sent', res.data)
  } catch {
    // ignore
  } finally {
    sending.value = false
  }
}

function close() {
  model.value = false
}

watch(model, (v) => {
  if (!v) {
    // Reset on close
    step.value = 1
    selectedTemplateId.value = null
    audienceTab.value = 'registered'
    preview.value = null
    sendResult.value = null
    externalEmailsRaw.value = ''
    externalEntries.value = []
    csvFileName.value = ''
    csvParsedEntries.value = []
    filters.value = { statuses: ['Approved', 'Paid'], ticket_type_ids: [], checked_in_only: false }
  }
})

// Auto-select primary template when dialog opens
watch(() => props.attachedTemplates, (templates) => {
  if (templates.length && !selectedTemplateId.value) {
    const primary = templates.find(t => t.is_primary)
    selectedTemplateId.value = primary?.template_id || templates[0]?.template_id || null
  }
}, { immediate: true })
</script>
