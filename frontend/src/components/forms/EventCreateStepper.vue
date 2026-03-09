<template>
  <div>
    <v-stepper v-model="step" alt-labels flat>
      <v-stepper-header>
        <v-stepper-item :value="1" title="Basics" :complete="step > 1" :editable="false" />
        <v-divider />
        <v-stepper-item :value="2" title="Location" :complete="step > 2" :editable="step > 2" />
        <v-divider />
        <v-stepper-item :value="3" title="Registration" :complete="step > 3" :editable="step > 3" />
        <v-divider />
        <v-stepper-item :value="4" title="Media & Emails" :complete="step > 4" :editable="step > 4" />
        <v-divider />
        <v-stepper-item :value="5" title="Review" :editable="step > 4" />
      </v-stepper-header>

      <v-stepper-window>

        <!-- ─────────────────────────────────────────────────────── Step 1: Basics -->
        <v-stepper-window-item :value="1">
          <v-form ref="form1" class="pa-2">
            <v-text-field
              v-model="form.event_name"
              label="Event Name *"
              variant="outlined"
              class="mb-4"
              :rules="[v => !!v || 'Event name is required']"
            />

            <v-textarea
              v-model="form.description"
              label="Description"
              variant="outlined"
              class="mb-4"
              rows="8"
              hint="Supports Markdown: **bold**, *italic*, ## headings, - lists, [links](url)"
              persistent-hint
            />

            <v-row>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model="form.event_date_start"
                  label="Start Date & Time *"
                  type="datetime-local"
                  variant="outlined"
                  class="mb-4"
                  :rules="[v => !!v || 'Start date is required']"
                />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model="form.event_date_end"
                  label="End Date & Time (optional)"
                  type="datetime-local"
                  variant="outlined"
                  class="mb-4"
                />
              </v-col>
            </v-row>

            <v-text-field
              v-model="form.location"
              label="Display Location"
              variant="outlined"
              class="mb-4"
              hint="What attendees will see — e.g. 'Building 9, Room 101'"
              persistent-hint
            />

          </v-form>
        </v-stepper-window-item>

        <!-- ──────────────────────────────────────────────────── Step 2: Location -->
        <v-stepper-window-item :value="2">
          <div class="pa-2">
            <p class="text-body-2 text-medium-emphasis mb-4">
              Configure how the event location appears on the interactive map. This is optional — leave everything empty to skip map display.
            </p>

            <v-radio-group v-model="mapInputMethod" class="mb-4" inline>
              <v-radio label="Map address" value="address" />
              <v-radio label="Manual coordinates" value="coordinates" />
              <v-radio label="Auto-detect from display location" value="auto" />
            </v-radio-group>

            <v-text-field
              v-if="mapInputMethod === 'address'"
              v-model="form.map_address"
              label="Map Address"
              variant="outlined"
              placeholder="e.g. Julianalaan 134, 2628 BL Delft"
              hint="The more specific the address, the better the map placement"
              persistent-hint
              prepend-inner-icon="mdi-map-search"
              clearable
              class="mb-4"
            />

            <v-row v-if="mapInputMethod === 'coordinates'">
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model.number="form.latitude"
                  label="Latitude"
                  variant="outlined"
                  type="number"
                  step="any"
                  placeholder="e.g. 52.0027"
                  prepend-inner-icon="mdi-latitude"
                />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model.number="form.longitude"
                  label="Longitude"
                  variant="outlined"
                  type="number"
                  step="any"
                  placeholder="e.g. 4.3707"
                  prepend-inner-icon="mdi-longitude"
                />
              </v-col>
            </v-row>

            <v-alert v-if="mapInputMethod === 'auto'" type="info" variant="tonal" density="compact" class="mb-4">
              <v-icon start size="small">mdi-auto-fix</v-icon>
              The map will attempt to geocode: <strong>{{ form.location || '(no display location set)' }}</strong>
            </v-alert>

            <v-btn
              v-if="mapPreviewUrl"
              :href="mapPreviewUrl"
              target="_blank"
              size="small"
              variant="outlined"
              color="primary"
              class="mt-2"
            >
              <v-icon start>mdi-open-in-new</v-icon>
              Preview on Google Maps
            </v-btn>
          </div>
        </v-stepper-window-item>

        <!-- ──────────────────────────────────────── Step 3: Registration Setup -->
        <v-stepper-window-item :value="3">
          <div class="pa-2">

            <!-- Pricing model -->
            <div class="text-subtitle-2 font-weight-bold mb-3">Pricing Model</div>
            <v-row class="mb-4">
              <v-col
                v-for="model in pricingModels"
                :key="model.value"
                cols="12"
                sm="4"
              >
                <v-card
                  :variant="pricingModel === model.value ? 'tonal' : 'outlined'"
                  :color="pricingModel === model.value ? 'primary' : undefined"
                  class="cursor-pointer h-100"
                  @click="pricingModel = model.value"
                >
                  <v-card-text class="text-center pa-4">
                    <v-icon :icon="model.icon" size="32" class="mb-2" />
                    <div class="text-subtitle-2 font-weight-bold">{{ model.label }}</div>
                    <div class="text-caption text-medium-emphasis mt-1">{{ model.description }}</div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <v-row v-if="pricingModel === 'fixed'" class="mb-2">
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model.number="form.price_euros"
                  label="Price (€)"
                  type="number"
                  min="0"
                  step="0.01"
                  variant="outlined"
                />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model.number="form.capacity"
                  label="Capacity (optional)"
                  type="number"
                  min="1"
                  variant="outlined"
                  hint="Leave empty for unlimited"
                  persistent-hint
                />
              </v-col>
            </v-row>

            <v-row v-if="pricingModel === 'free'" class="mb-2">
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model.number="form.capacity"
                  label="Capacity (optional)"
                  type="number"
                  min="1"
                  variant="outlined"
                  hint="Leave empty for unlimited"
                  persistent-hint
                />
              </v-col>
            </v-row>

            <!-- Inline ticket type builder -->
            <div v-if="pricingModel === 'tickets'" class="mb-4">
              <div class="d-flex align-center justify-space-between mb-3">
                <div class="text-subtitle-2 font-weight-bold">Ticket Types</div>
                <v-btn size="small" color="primary" prepend-icon="mdi-plus" @click="addTicketType">
                  Add Ticket Type
                </v-btn>
              </div>

              <v-alert v-if="ticketTypes.length === 0" type="info" variant="tonal" density="compact" class="mb-3">
                Add at least one ticket type to continue.
              </v-alert>

              <v-card
                v-for="(ticket, idx) in ticketTypes"
                :key="idx"
                variant="outlined"
                class="mb-3"
              >
                <v-card-text class="pa-3">
                  <div class="d-flex align-center mb-2">
                    <div class="text-subtitle-2 font-weight-medium flex-grow-1">Ticket {{ idx + 1 }}</div>
                    <v-btn
                      icon
                      size="x-small"
                      variant="text"
                      color="error"
                      @click="removeTicketType(idx)"
                    >
                      <v-icon>mdi-close</v-icon>
                    </v-btn>
                  </div>
                  <v-row dense>
                    <v-col cols="12" sm="5">
                      <v-text-field
                        v-model="ticket.name"
                        label="Name *"
                        variant="outlined"
                        density="compact"
                        placeholder="e.g. Participant"
                        :rules="[v => !!v || 'Required']"
                        hide-details="auto"
                      />
                    </v-col>
                    <v-col cols="6" sm="3">
                      <v-text-field
                        v-model.number="ticket.price_euros"
                        label="Price (€)"
                        variant="outlined"
                        density="compact"
                        type="number"
                        min="0"
                        step="0.01"
                        hide-details
                      />
                    </v-col>
                    <v-col cols="6" sm="4">
                      <v-text-field
                        v-model.number="ticket.capacity"
                        label="Capacity"
                        variant="outlined"
                        density="compact"
                        type="number"
                        min="1"
                        placeholder="Unlimited"
                        hide-details
                      />
                    </v-col>
                    <v-col cols="12">
                      <v-text-field
                        v-model="ticket.description"
                        label="Description (optional)"
                        variant="outlined"
                        density="compact"
                        hide-details
                      />
                    </v-col>
                    <v-col cols="12">
                      <v-select
                        v-model="ticket.form_template_id"
                        :items="formTemplates"
                        item-title="template_name"
                        item-value="template_id"
                        label="Registration Form (optional)"
                        variant="outlined"
                        density="compact"
                        clearable
                        hide-details
                      />
                    </v-col>
                  </v-row>

                  <v-divider class="my-3" />

                  <v-row dense>
                    <v-col cols="12" sm="6">
                      <v-checkbox
                        v-model="ticket.is_free_for_members"
                        label="Free for Ennova Members"
                        hint="Members register for free with this ticket"
                        persistent-hint
                        color="success"
                        density="compact"
                        hide-details="auto"
                      />
                    </v-col>
                    <v-col cols="12" sm="6">
                      <v-checkbox
                        v-model="ticket.show_availability"
                        label="Show Ticket Availability"
                        hint="Display remaining spots to users"
                        persistent-hint
                        color="primary"
                        density="compact"
                        hide-details="auto"
                      />
                    </v-col>
                    <v-col cols="12" sm="6">
                      <v-checkbox
                        v-model="ticket.requires_team"
                        label="Require Team Registration"
                        hint="Users must join or create a team"
                        persistent-hint
                        color="purple"
                        density="compact"
                        hide-details="auto"
                      />
                    </v-col>
                    <v-col v-if="ticket.requires_team" cols="12" sm="6">
                      <v-text-field
                        v-model.number="ticket.team_max_members"
                        label="Max Team Size"
                        variant="outlined"
                        density="compact"
                        type="number"
                        min="1"
                        placeholder="Unlimited"
                        hide-details
                      />
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </div>

            <v-divider class="my-4" />

            <!-- Toggles -->
            <div class="d-flex flex-column gap-3">
              <v-card variant="outlined">
                <v-card-text class="py-3">
                  <div class="d-flex align-center justify-space-between">
                    <div>
                      <div class="text-subtitle-2 font-weight-medium">Require Admin Approval</div>
                      <div class="text-caption text-medium-emphasis">Registrations must be manually approved before attendees can pay.</div>
                    </div>
                    <v-switch v-model="form.requires_approval" color="primary" hide-details class="ml-4 flex-shrink-0" />
                  </div>
                </v-card-text>
              </v-card>

              <v-card v-if="pricingModel === 'fixed'" variant="outlined">
                <v-card-text class="py-3">
                  <div class="d-flex align-center justify-space-between">
                    <div>
                      <div class="text-subtitle-2 font-weight-medium">Free for Ennova Members</div>
                      <div class="text-caption text-medium-emphasis">Ennova members bypass payment and are auto-approved.</div>
                    </div>
                    <v-switch v-model="form.is_free_for_members" color="success" hide-details class="ml-4 flex-shrink-0" />
                  </div>
                </v-card-text>
              </v-card>

              <v-card v-if="pricingModel !== 'tickets'" variant="outlined">
                <v-card-text class="py-3">
                  <div class="d-flex align-center justify-space-between">
                    <div>
                      <div class="text-subtitle-2 font-weight-medium">Team Registration</div>
                      <div class="text-caption text-medium-emphasis">Attendees can join or create a team when registering.</div>
                    </div>
                    <v-switch v-model="form.teams_enabled" color="primary" hide-details class="ml-4 flex-shrink-0" />
                  </div>
                  <v-text-field
                    v-if="form.teams_enabled"
                    v-model.number="form.team_max_members"
                    label="Default Max Team Size"
                    type="number"
                    min="1"
                    variant="outlined"
                    class="mt-3"
                    hint="Leave empty for unlimited"
                    persistent-hint
                  />
                </v-card-text>
              </v-card>
            </div>

            <template v-if="pricingModel !== 'tickets'">
              <v-divider class="my-4" />

              <v-select
                v-model="form.form_template_id"
                :items="formTemplates"
                item-title="template_name"
                item-value="template_id"
                label="Application Form (optional)"
                variant="outlined"
                clearable
                no-data-text="No custom forms available"
                hint="Extra questions shown during registration"
                persistent-hint
              />
            </template>
          </div>
        </v-stepper-window-item>

        <!-- ──────────────────────────────────────── Step 4: Media & Emails -->
        <v-stepper-window-item :value="4">
          <div class="pa-2">

            <!-- Cover image -->
            <div class="text-subtitle-2 font-weight-bold mb-3">Cover Image</div>
            <v-file-input
              v-model="imageFile"
              label="Cover Image (optional)"
              variant="outlined"
              prepend-icon=""
              prepend-inner-icon="mdi-camera"
              accept="image/*"
              class="mb-3"
              @update:model-value="onImageSelected"
            />
            <div v-if="imagePreviewUrl" class="mb-4">
              <img :src="imagePreviewUrl" alt="Cover preview" style="max-height:180px;border-radius:8px;object-fit:cover;width:100%;" />
            </div>

            <!-- Additional media note -->
            <v-alert type="info" variant="tonal" density="compact" class="mb-4">
              <v-icon start size="small">mdi-image-multiple-outline</v-icon>
              <strong>Sponsor logos, photo gallery and attachments</strong> can be added from the <strong>Media tab</strong> after the event is created.
            </v-alert>

            <!-- Email templates — hidden for ticket-based events -->
            <template v-if="pricingModel !== 'tickets'">
              <v-divider class="my-4" />
              <div class="text-subtitle-2 font-weight-bold mb-1">Email Templates <span class="text-caption font-weight-regular text-medium-emphasis">(optional)</span></div>
              <p class="text-body-2 text-medium-emphasis mb-4">Customise the emails sent to attendees at each stage. Leave empty to use the default system emails.</p>

              <v-row>
                <v-col cols="12" sm="6">
                  <v-select
                    v-model="form.email_template_received_id"
                    :items="receivedTemplates"
                    item-title="template_name"
                    item-value="template_id"
                    label="Registration Received"
                    variant="outlined"
                    clearable
                    hint="Sent when registration is submitted"
                    persistent-hint
                    class="mb-4"
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-select
                    v-model="form.email_template_approved_id"
                    :items="approvedTemplates"
                    item-title="template_name"
                    item-value="template_id"
                    label="Registration Approved"
                    variant="outlined"
                    clearable
                    hint="Sent when registration is approved"
                    persistent-hint
                    class="mb-4"
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-select
                    v-model="form.email_template_rejected_id"
                    :items="rejectedTemplates"
                    item-title="template_name"
                    item-value="template_id"
                    label="Registration Rejected"
                    variant="outlined"
                    clearable
                    hint="Sent when registration is rejected"
                    persistent-hint
                    class="mb-4"
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-select
                    v-model="form.email_template_payment_id"
                    :items="paymentTemplates"
                    item-title="template_name"
                    item-value="template_id"
                    label="Payment Confirmed"
                    variant="outlined"
                    clearable
                    hint="Sent when payment is confirmed"
                    persistent-hint
                    class="mb-4"
                  />
                </v-col>
              </v-row>
            </template>

          </div>
        </v-stepper-window-item>

        <!-- ────────────────────────────────────────────────── Step 5: Review -->
        <v-stepper-window-item :value="5">
          <div class="pa-2">
            <v-list lines="two" class="mb-4">
              <v-list-subheader>Basics</v-list-subheader>
              <v-list-item title="Event Name" :subtitle="form.event_name || '—'" />
              <v-list-item title="Start" :subtitle="formatDatePreview(form.event_date_start)" />
              <v-list-item v-if="form.event_date_end" title="End" :subtitle="formatDatePreview(form.event_date_end)" />
              <v-list-item title="Location" :subtitle="form.location || '—'" />
              <v-list-item v-if="imageFile" title="Cover Image" :subtitle="imageFile.name" />

              <v-divider class="my-2" />
              <v-list-subheader>Map</v-list-subheader>
              <v-list-item title="Map Config" :subtitle="mapSummary" />

              <v-divider class="my-2" />
              <v-list-subheader>Registration</v-list-subheader>
              <v-list-item title="Pricing" :subtitle="pricingModels.find(m => m.value === pricingModel)?.label" />
              <v-list-item v-if="pricingModel === 'fixed'" title="Price" :subtitle="`€${form.price_euros ?? 0}`" />
              <v-list-item v-if="pricingModel !== 'tickets' && form.capacity" title="Capacity" :subtitle="String(form.capacity)" />
              <template v-if="pricingModel === 'tickets'">
                <v-list-item
                  v-for="(ticket, idx) in ticketTypes"
                  :key="idx"
                  :title="ticket.name"
                  :subtitle="`€${ticket.price_euros ?? 0}${ticket.capacity ? ' · ' + ticket.capacity + ' spots' : ' · Unlimited'}`"
                >
                  <template #prepend>
                    <v-icon color="primary" size="small" class="mr-2">mdi-ticket-outline</v-icon>
                  </template>
                </v-list-item>
              </template>
              <v-list-item title="Requires Approval" :subtitle="form.requires_approval ? 'Yes' : 'No'" />
              <v-list-item v-if="pricingModel === 'fixed'" title="Free for Members" :subtitle="form.is_free_for_members ? 'Yes' : 'No'" />
              <v-list-item v-if="pricingModel !== 'tickets'" title="Team Registration" :subtitle="form.teams_enabled ? 'Enabled' : 'Disabled'" />
            </v-list>

            <v-alert v-if="createError" type="error" variant="tonal" class="mb-4">
              {{ createError }}
            </v-alert>

            <v-btn
              color="primary"
              size="large"
              block
              :loading="isSubmitting"
              @click="handleCreate"
            >
              Create Event
            </v-btn>
          </div>
        </v-stepper-window-item>

      </v-stepper-window>
    </v-stepper>

    <!-- Navigation -->
    <div class="d-flex justify-space-between mt-4 px-2">
      <v-btn
        v-if="step > 1"
        variant="text"
        @click="step--"
      >
        Back
      </v-btn>
      <v-spacer />
      <v-tooltip
        v-if="step === 1 && !step1Valid"
        text="Please fill in all required fields to continue"
        location="top"
      >
        <template #activator="{ props: tooltipProps }">
          <span v-bind="tooltipProps">
            <v-btn color="primary" disabled @click="nextStep">Next</v-btn>
          </span>
        </template>
      </v-tooltip>
      <v-btn
        v-else-if="step < 5"
        color="primary"
        @click="nextStep"
      >
        Next
      </v-btn>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { FormTemplateService } from '@/services/FormTemplateService.js'
import { EmailTemplateService } from '@/services/EmailTemplateService.js'

const emit = defineEmits(['submit'])

const step = ref(1)
const form1 = ref(null)
const isSubmitting = ref(false)
const createError = ref(null)
const imageFile = ref(null)
const imagePreviewUrl = ref(null)

const form = ref({
  event_name: '',
  description: '',
  event_date_start: '',
  event_date_end: '',
  location: '',
  map_address: null,
  latitude: null,
  longitude: null,
  price_euros: 0,
  capacity: null,
  requires_approval: true,
  is_free_for_members: false,
  teams_enabled: false,
  team_max_members: null,
  form_template_id: null,
  email_template_received_id: null,
  email_template_approved_id: null,
  email_template_rejected_id: null,
  email_template_payment_id: null,
})

const mapInputMethod = ref('address')
const pricingModel = ref('free')
const formTemplates = ref([])
const ticketTypes = ref([])
const approvedTemplates = ref([])
const rejectedTemplates = ref([])
const receivedTemplates = ref([])
const paymentTemplates = ref([])

const pricingModels = [
  { value: 'free', label: 'Free', icon: 'mdi-gift-outline', description: 'No payment required' },
  { value: 'fixed', label: 'Fixed Price', icon: 'mdi-currency-eur', description: 'Single price for all' },
  { value: 'tickets', label: 'Ticket Types', icon: 'mdi-ticket-outline', description: 'Multiple tiers or categories' },
]

function addTicketType() {
  ticketTypes.value.push({
    name: '',
    description: '',
    price_euros: 0,
    capacity: null,
    form_template_id: null,
    is_free_for_members: false,
    show_availability: true,
    requires_team: false,
    team_max_members: null,
    is_active: true,
  })
}

function removeTicketType(idx) {
  ticketTypes.value.splice(idx, 1)
}

// Sync pricing model selection into form data
watch(pricingModel, (val) => {
  if (val === 'free') {
    form.value.price_euros = 0
  } else if (val === 'tickets') {
    form.value.price_euros = 0
    form.value.capacity = null
  }
})

// Sync map method changes
watch(mapInputMethod, (val) => {
  if (val === 'address') {
    form.value.latitude = null
    form.value.longitude = null
  } else if (val === 'coordinates') {
    form.value.map_address = null
  } else {
    form.value.map_address = null
    form.value.latitude = null
    form.value.longitude = null
  }
})

// Reactively tracks whether step 1 required fields are filled
const step1Valid = computed(() =>
  !!form.value.event_name?.trim() && !!form.value.event_date_start
)

const mapPreviewUrl = computed(() => {
  if (mapInputMethod.value === 'coordinates' && form.value.latitude && form.value.longitude) {
    return `https://www.google.com/maps/search/?api=1&query=${form.value.latitude},${form.value.longitude}`
  }
  const addr = mapInputMethod.value === 'address' ? form.value.map_address : form.value.location
  if (addr) return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(addr)}`
  return null
})

const mapSummary = computed(() => {
  if (mapInputMethod.value === 'address' && form.value.map_address) return `Address: ${form.value.map_address}`
  if (mapInputMethod.value === 'coordinates' && form.value.latitude) return `${form.value.latitude}, ${form.value.longitude}`
  if (mapInputMethod.value === 'auto') return 'Auto-detect from display location'
  return 'Not configured'
})

function formatDatePreview(val) {
  if (!val) return '—'
  try { return new Date(val).toLocaleString() } catch { return val }
}

function onImageSelected(file) {
  if (!file) { imagePreviewUrl.value = null; return }
  const reader = new FileReader()
  reader.onload = (e) => { imagePreviewUrl.value = e.target.result }
  reader.readAsDataURL(file)
}

async function nextStep() {
  if (step.value === 1) {
    const { valid } = await form1.value.validate()
    if (!valid) return
  }
  step.value++
}

function buildPayload() {
  const payload = { ...form.value }

  // Normalise datetime-local values to ISO string
  if (payload.event_date_start) {
    payload.event_date_start = new Date(payload.event_date_start).toISOString()
  }
  if (payload.event_date_end) {
    payload.event_date_end = new Date(payload.event_date_end).toISOString()
  } else {
    delete payload.event_date_end
  }

  // Clean up pricing
  if (pricingModel.value === 'free') {
    payload.price_euros = 0
  } else if (pricingModel.value === 'tickets') {
    payload.price_euros = 0
    payload.capacity = null
  }

  // Clean up map
  if (mapInputMethod.value === 'auto') {
    payload.map_address = null
    payload.latitude = null
    payload.longitude = null
  }

  return payload
}

async function handleCreate() {
  isSubmitting.value = true
  createError.value = null
  try {
    emit('submit', buildPayload(), imageFile.value, pricingModel.value === 'tickets' ? ticketTypes.value : [])
  } catch (e) {
    createError.value = 'Failed to create event. Please try again.'
    isSubmitting.value = false
  }
}

onMounted(async () => {
  try {
    const [formRes, emailRes] = await Promise.all([
      FormTemplateService.getAllTemplates(),
      EmailTemplateService.getAllTemplates(),
    ])
    formTemplates.value = formRes.data
    const all = emailRes.data
    approvedTemplates.value = all.filter(t => t.template_type === 'registration_approved')
    rejectedTemplates.value = all.filter(t => t.template_type === 'registration_rejected')
    receivedTemplates.value = all.filter(t => t.template_type === 'registration_received')
    paymentTemplates.value = all.filter(t => t.template_type === 'payment_confirmed')
  } catch {
    // non-critical
  }
})
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
.h-100 {
  height: 100%;
}
</style>
