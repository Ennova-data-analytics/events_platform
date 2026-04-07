<template>
  <div>
    <div class="d-flex align-center mb-6 gap-3">
      <v-btn icon="mdi-arrow-left" variant="text" :to="{ name: 'admin-events' }" />
      <div>
        <h1 class="text-h5 font-weight-bold">{{ event.event_name || 'Edit Event' }}</h1>
        <div v-if="event.status" class="text-caption text-medium-emphasis mt-1">
          <v-chip size="x-small" :color="statusColor(event.status)" label>{{ event.status }}</v-chip>
        </div>
      </div>
    </div>

    <v-tabs v-model="activeTab" color="primary" class="mb-1">
      <v-tab value="details" prepend-icon="mdi-text-box-outline">Details</v-tab>
      <v-tab value="registration" prepend-icon="mdi-clipboard-list-outline">Registration</v-tab>
      <v-tab value="tickets" prepend-icon="mdi-ticket-outline">Tickets</v-tab>
      <v-tab value="media" prepend-icon="mdi-image-multiple-outline">Media</v-tab>
    </v-tabs>

    <v-divider class="mb-6" />

    <v-tabs-window v-model="activeTab">

      <!-- ─────────────────────────────────────── Tab: Details -->
      <v-tabs-window-item value="details">
        <v-card>
          <v-card-text class="pa-6">
            <v-form ref="detailsForm">
              <v-text-field
                v-model="editableEvent.event_name"
                label="Event Name *"
                variant="outlined"
                class="mb-4"
                :rules="[v => !!v || 'Required']"
              />

              <v-textarea
                v-model="editableEvent.description"
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
                    v-model="editableEvent.event_date_start"
                    label="Start Date & Time *"
                    type="datetime-local"
                    variant="outlined"
                    class="mb-4"
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-text-field
                    v-model="editableEvent.event_date_end"
                    label="End Date & Time (optional)"
                    type="datetime-local"
                    variant="outlined"
                    class="mb-4"
                  />
                </v-col>
              </v-row>

              <v-text-field
                v-model="editableEvent.location"
                label="Display Location"
                variant="outlined"
                class="mb-4"
                hint="What attendees will see — e.g. 'Building 9, Room 101'"
                persistent-hint
              />

              <!-- Map config -->
              <v-divider class="my-4" />
              <div class="text-subtitle-2 font-weight-bold mb-3 d-flex align-center gap-2">
                <v-icon size="18">mdi-map</v-icon> Map Settings
              </div>

              <v-radio-group v-model="mapInputMethod" class="mb-3" inline>
                <v-radio label="Map address" value="address" />
                <v-radio label="Manual coordinates" value="coordinates" />
                <v-radio label="Auto-detect" value="auto" />
              </v-radio-group>

              <v-text-field
                v-if="mapInputMethod === 'address'"
                v-model="editableEvent.map_address"
                label="Map Address"
                variant="outlined"
                prepend-inner-icon="mdi-map-search"
                clearable
                class="mb-3"
              />

              <v-row v-if="mapInputMethod === 'coordinates'">
                <v-col cols="6">
                  <v-text-field v-model.number="editableEvent.latitude" label="Latitude" variant="outlined" type="number" step="any" prepend-inner-icon="mdi-latitude" />
                </v-col>
                <v-col cols="6">
                  <v-text-field v-model.number="editableEvent.longitude" label="Longitude" variant="outlined" type="number" step="any" prepend-inner-icon="mdi-longitude" />
                </v-col>
              </v-row>

              <v-alert v-if="mapInputMethod === 'auto'" type="info" variant="tonal" density="compact" class="mb-3">
                Auto-geocoding display location: <strong>{{ editableEvent.location || 'not set' }}</strong>
              </v-alert>

              <v-btn
                v-if="mapPreviewUrl"
                :href="mapPreviewUrl"
                target="_blank"
                size="small"
                variant="outlined"
                color="primary"
                class="mb-4"
              >
                <v-icon start>mdi-open-in-new</v-icon>
                Preview on Google Maps
              </v-btn>

              <!-- Cover image -->
              <v-divider class="my-4" />
              <div class="text-subtitle-2 font-weight-bold mb-3">Cover Image</div>
              <div v-if="editableEvent.image_url" class="mb-3">
                <img :src="editableEvent.image_url" alt="Current cover" style="max-height:140px;border-radius:8px;object-fit:cover;" />
                <div class="text-caption text-medium-emphasis mt-1">Current image</div>
              </div>
              <v-file-input
                v-model="imageFile"
                label="Replace cover image"
                variant="outlined"
                prepend-icon=""
                prepend-inner-icon="mdi-camera"
                accept="image/*"
                class="mb-4"
              />
            </v-form>
          </v-card-text>

          <v-card-actions class="px-6 pb-6">
            <v-spacer />
            <v-btn color="primary" size="large" :loading="savingDetails" @click="saveDetails">
              Save Details
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-tabs-window-item>

      <!-- ──────────────────────────────────── Tab: Registration -->
      <v-tabs-window-item value="registration">
        <v-card>
          <v-card-text class="pa-6">

            <!-- Pricing — hidden when ticket types are in use -->
            <template v-if="!hasTicketTypes">
              <div class="text-subtitle-2 font-weight-bold mb-3">Pricing & Capacity</div>
              <v-row class="mb-4">
                <v-col cols="12" sm="6">
                  <v-text-field
                    v-model.number="editableEvent.price_euros"
                    label="Price (€)"
                    type="number"
                    min="0"
                    step="0.01"
                    variant="outlined"
                    hint="Set to 0 for free."
                    persistent-hint
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-text-field
                    v-model.number="editableEvent.capacity"
                    label="Capacity (optional)"
                    type="number"
                    min="1"
                    variant="outlined"
                    hint="Leave empty for unlimited."
                    persistent-hint
                  />
                </v-col>
              </v-row>
              <v-divider class="my-4" />
            </template>

            <template v-else>
              <v-alert type="info" variant="tonal" density="compact" class="mb-4">
                <v-icon start size="small">mdi-ticket-outline</v-icon>
                This event uses <strong>Ticket Types</strong>. Price and capacity are configured per ticket in the Tickets tab.
              </v-alert>
              <v-divider class="my-4" />
            </template>

            <div class="text-subtitle-2 font-weight-bold mb-3">Settings</div>

            <div class="d-flex flex-column gap-3 mb-4">
              <v-card variant="outlined">
                <v-card-text class="py-3">
                  <div class="d-flex align-center justify-space-between">
                    <div>
                      <div class="text-subtitle-2 font-weight-medium">Require Admin Approval</div>
                      <div class="text-caption text-medium-emphasis">Registrations must be manually approved before attendees can pay.</div>
                    </div>
                    <v-switch v-model="editableEvent.requires_approval" color="primary" hide-details class="ml-4 flex-shrink-0" />
                  </div>
                </v-card-text>
              </v-card>

              <v-card v-if="!hasTicketTypes && editableEvent.price_euros > 0" variant="outlined">
                <v-card-text class="py-3">
                  <div class="d-flex align-center justify-space-between">
                    <div>
                      <div class="text-subtitle-2 font-weight-medium">Free for Ennova Members</div>
                      <div class="text-caption text-medium-emphasis">Members bypass payment and are auto-approved.</div>
                    </div>
                    <v-switch v-model="editableEvent.is_free_for_members" color="success" hide-details class="ml-4 flex-shrink-0" />
                  </div>
                </v-card-text>
              </v-card>

              <v-card v-if="!hasTicketTypes" variant="outlined">
                <v-card-text class="py-3">
                  <div class="d-flex align-center justify-space-between">
                    <div>
                      <div class="text-subtitle-2 font-weight-medium">Team Registration</div>
                      <div class="text-caption text-medium-emphasis">Attendees can join or create a team when registering.</div>
                    </div>
                    <v-switch v-model="editableEvent.teams_enabled" color="primary" hide-details class="ml-4 flex-shrink-0" />
                  </div>
                  <v-text-field
                    v-if="editableEvent.teams_enabled"
                    v-model.number="editableEvent.team_max_members"
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

            <v-divider class="my-4" />
            <div class="text-subtitle-2 font-weight-bold mb-3">Forms & Email Templates</div>

            <v-select
              v-if="!hasTicketTypes"
              v-model="editableEvent.form_template_id"
              :items="formTemplates"
              item-title="template_name"
              item-value="template_id"
              label="Application Form (optional)"
              variant="outlined"
              clearable
              class="mb-4"
              hint="Extra questions shown during registration"
              persistent-hint
            />

            <v-row>
              <v-col cols="12" sm="6">
                <v-select v-model="editableEvent.email_template_approved_id" :items="approvedTemplates" item-title="template_name" item-value="template_id" label="Approved Email Template" variant="outlined" clearable hint="Sent on approval" persistent-hint class="mb-4" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-select v-model="editableEvent.email_template_rejected_id" :items="rejectedTemplates" item-title="template_name" item-value="template_id" label="Rejected Email Template" variant="outlined" clearable hint="Sent on rejection" persistent-hint class="mb-4" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-select v-model="editableEvent.email_template_received_id" :items="receivedTemplates" item-title="template_name" item-value="template_id" label="Received Email Template" variant="outlined" clearable hint="Sent on submission" persistent-hint class="mb-4" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-select v-model="editableEvent.email_template_payment_id" :items="paymentTemplates" item-title="template_name" item-value="template_id" label="Payment Email Template" variant="outlined" clearable hint="Sent on payment" persistent-hint class="mb-4" />
              </v-col>
            </v-row>
          </v-card-text>

          <v-card-actions class="px-6 pb-6">
            <v-spacer />
            <v-btn color="primary" size="large" :loading="savingRegistration" @click="saveRegistration">
              Save Registration Settings
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-tabs-window-item>

      <!-- ──────────────────────────────────────── Tab: Tickets -->
      <v-tabs-window-item value="tickets">
        <TicketTypeManagement
          v-if="event.event_id"
          :event-id="event.event_id"
          @ticket-types-updated="handleTicketTypesUpdated"
        />
        <v-card v-else>
          <v-card-text class="text-center pa-8 text-medium-emphasis">
            Save the event first to manage ticket types.
          </v-card-text>
        </v-card>
      </v-tabs-window-item>

      <!-- ─────────────────────────────────────────── Tab: Media -->
      <v-tabs-window-item value="media">
        <div class="d-flex flex-column gap-4">
          <SponsorLogoUpload
            v-if="event.event_id"
            :event-id="event.event_id"
            :logos="event.sponsor_logos"
            @updated="handleLogosUpdated"
          />
          <EventPhotosUpload
            v-if="event.event_id"
            :event-id="event.event_id"
            :photos="event.event_photos"
            @updated="handlePhotosUpdated"
          />
          <EventAttachmentsUpload
            v-if="event.event_id"
            :event-id="event.event_id"
            :attachments="event.attachments"
            @updated="handleAttachmentsUpdated"
          />
        </div>
      </v-tabs-window-item>

    </v-tabs-window>

    <!-- Save success snackbar -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" timeout="3000" location="bottom right">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import TicketTypeManagement from '@/components/admin/TicketTypeManagement.vue'
import SponsorLogoUpload from '@/components/admin/SponsorLogoUpload.vue'
import EventPhotosUpload from '@/components/admin/EventPhotosUpload.vue'
import EventAttachmentsUpload from '@/components/admin/EventAttachmentsUpload.vue'
import { useEventStore } from '@/stores/events.store.js'
import { EventService } from '@/services/EventService.js'
import { FormTemplateService } from '@/services/FormTemplateService.js'
import { EmailTemplateService } from '@/services/EmailTemplateService.js'

const route = useRoute()
const eventStore = useEventStore()

const event = ref({})
const editableEvent = ref({})
const activeTab = ref(route.query.tab || 'details')
const imageFile = ref(null)
const mapInputMethod = ref('address')

const detailsForm = ref(null)
const savingDetails = ref(false)
const savingRegistration = ref(false)

const formTemplates = ref([])
const approvedTemplates = ref([])
const rejectedTemplates = ref([])
const receivedTemplates = ref([])
const paymentTemplates = ref([])

const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

function notify(text, color = 'success') {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

function statusColor(status) {
  const map = { Draft: 'default', Published: 'success', Cancelled: 'error', Archived: 'secondary' }
  return map[status] || 'default'
}

// Convert ISO datetime to datetime-local format for input (preserve local time)
function toDatetimeLocal(isoString) {
  if (!isoString) return ''
  try {
    const d = new Date(isoString)
    const pad = n => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch { return '' }
}

watch(event, (newEvent) => {
  if (!newEvent || !newEvent.event_id) return
  const data = { ...newEvent }
  data.event_date_start = toDatetimeLocal(data.event_date_start)
  data.event_date_end = toDatetimeLocal(data.event_date_end)
  editableEvent.value = data

  if (data.latitude && data.longitude) mapInputMethod.value = 'coordinates'
  else if (data.map_address) mapInputMethod.value = 'address'
  else mapInputMethod.value = 'auto'
}, { immediate: true, deep: true })

watch(mapInputMethod, (val) => {
  if (val === 'address') {
    editableEvent.value.latitude = null
    editableEvent.value.longitude = null
  } else if (val === 'coordinates') {
    editableEvent.value.map_address = null
  } else {
    editableEvent.value.map_address = null
    editableEvent.value.latitude = null
    editableEvent.value.longitude = null
  }
})

const hasTicketTypes = computed(() => (event.value.ticket_types?.length ?? 0) > 0)

const mapPreviewUrl = computed(() => {
  if (mapInputMethod.value === 'coordinates' && editableEvent.value.latitude && editableEvent.value.longitude) {
    return `https://www.google.com/maps/search/?api=1&query=${editableEvent.value.latitude},${editableEvent.value.longitude}`
  }
  const addr = mapInputMethod.value === 'address' ? editableEvent.value.map_address : editableEvent.value.location
  if (addr) return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(addr)}`
  return null
})

function buildEventPayload(data) {
  const payload = { ...data }
  if (payload.event_date_start) payload.event_date_start = new Date(payload.event_date_start).toISOString()
  if (payload.event_date_end) payload.event_date_end = new Date(payload.event_date_end).toISOString()
  else delete payload.event_date_end
  return payload
}

async function saveDetails() {
  savingDetails.value = true
  try {
    const payload = buildEventPayload(editableEvent.value)
    await eventStore.updateEvent(event.value.event_id, payload)
    if (imageFile.value) {
      await eventStore.uploadEventImage(event.value.event_id, imageFile.value)
      imageFile.value = null
    }
    notify('Details saved')
    await reloadEvent()
  } catch {
    notify('Failed to save details', 'error')
  } finally {
    savingDetails.value = false
  }
}

async function saveRegistration() {
  savingRegistration.value = true
  try {
    const payload = buildEventPayload(editableEvent.value)
    await eventStore.updateEvent(event.value.event_id, payload)
    notify('Registration settings saved')
    await reloadEvent()
  } catch {
    notify('Failed to save settings', 'error')
  } finally {
    savingRegistration.value = false
  }
}

async function reloadEvent() {
  const res = await EventService.getEventById(event.value.event_id)
  event.value = res.data
}

function handleLogosUpdated(updatedEvent) { event.value = updatedEvent }
function handlePhotosUpdated(updatedEvent) { event.value = updatedEvent }
function handleAttachmentsUpdated(updatedEvent) { event.value = updatedEvent }
async function handleTicketTypesUpdated() { await reloadEvent() }

onMounted(async () => {
  const eventId = route.params.id
  try {
    const [eventRes, formRes, emailRes] = await Promise.all([
      EventService.getEventById(eventId),
      FormTemplateService.getAllTemplates(),
      EmailTemplateService.getAllTemplates(),
    ])
    event.value = eventRes.data
    formTemplates.value = formRes.data
    const all = emailRes.data
    approvedTemplates.value = all.filter(t => t.template_type === 'registration_approved')
    rejectedTemplates.value = all.filter(t => t.template_type === 'registration_rejected')
    receivedTemplates.value = all.filter(t => t.template_type === 'registration_received')
    paymentTemplates.value = all.filter(t => t.template_type === 'payment_confirmed')
  } catch (error) {
    console.error('Failed to load event for editing:', error)
  }
})
</script>
