<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-title class="d-flex align-center justify-space-between pa-4">
      <span class="text-subtitle-1 font-weight-bold">Feedback Templates</span>
      <v-btn
        size="small"
        color="primary"
        prepend-icon="mdi-plus"
        @click="showAttachDialog = true"
      >
        Attach Template
      </v-btn>
    </v-card-title>

    <v-divider />

    <v-card-text class="pa-0">
      <v-progress-linear v-if="loading" indeterminate color="primary" />

      <v-list v-if="attachedTemplates.length" lines="two">
        <v-list-item
          v-for="link in attachedTemplates"
          :key="link.template_id"
          :subtitle="`${link.field_count} fields${link.template_description ? ' · ' + link.template_description : ''}`"
        >
          <template #title>
            <span>{{ link.template_name }}</span>
            <v-chip
              v-if="link.is_primary"
              size="x-small"
              color="primary"
              class="ml-2"
              label
            >Primary</v-chip>
          </template>

          <template #append>
            <div class="d-flex align-center gap-1">
              <v-btn
                v-if="!link.is_primary"
                size="x-small"
                variant="text"
                color="secondary"
                @click="setPrimary(link.template_id)"
                :loading="actionLoading === `primary-${link.template_id}`"
              >
                Set Primary
              </v-btn>
              <v-btn
                size="x-small"
                variant="text"
                color="error"
                icon="mdi-close"
                @click="confirmDetach(link)"
              />
            </div>
          </template>
        </v-list-item>
      </v-list>

      <div v-else-if="!loading" class="pa-4 text-center text-medium-emphasis text-body-2">
        No templates attached. Attach one to enable feedback invitations and QR codes.
      </div>
    </v-card-text>

    <!-- Attach template dialog -->
    <v-dialog v-model="showAttachDialog" max-width="480">
      <v-card>
        <v-card-title>Attach Feedback Template</v-card-title>
        <v-card-text>
          <v-select
            v-model="selectedTemplateId"
            :items="availableTemplates"
            item-title="template_name"
            item-value="template_id"
            label="Select template"
            :loading="loadingAvailable"
            clearable
          />
          <v-checkbox
            v-model="attachAsPrimary"
            label="Set as primary (used for QR code by default)"
            density="compact"
            hide-details
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showAttachDialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            :disabled="!selectedTemplateId"
            :loading="attaching"
            @click="attachTemplate"
          >
            Attach
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Detach confirm dialog -->
    <v-dialog v-model="showDetachConfirm" max-width="400">
      <v-card>
        <v-card-title>Remove Template</v-card-title>
        <v-card-text>
          Remove <strong>{{ pendingDetach?.template_name }}</strong> from this event?
          Any unsent invitations for this template will not be affected.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDetachConfirm = false">Cancel</v-btn>
          <v-btn color="error" :loading="detaching" @click="detachTemplate">Remove</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { FeedbackService } from '@/services/FeedbackService'
import { FeedbackTemplateService } from '@/services/FeedbackTemplateService'

const props = defineProps({
  eventId: { type: Number, required: true }
})

const emit = defineEmits(['updated'])

const loading = ref(false)
const attachedTemplates = ref([])
const allTemplates = ref([])
const loadingAvailable = ref(false)

const showAttachDialog = ref(false)
const selectedTemplateId = ref(null)
const attachAsPrimary = ref(false)
const attaching = ref(false)

const showDetachConfirm = ref(false)
const pendingDetach = ref(null)
const detaching = ref(false)

const actionLoading = ref(null)

const attachedIds = computed(() => new Set(attachedTemplates.value.map(l => l.template_id)))
const availableTemplates = computed(() => allTemplates.value.filter(t => !attachedIds.value.has(t.template_id)))

async function load() {
  loading.value = true
  try {
    const res = await FeedbackService.getEventFeedbackTemplates(props.eventId)
    attachedTemplates.value = res.data
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function loadAllTemplates() {
  loadingAvailable.value = true
  try {
    const res = await FeedbackTemplateService.getAllTemplates()
    allTemplates.value = res.data
  } catch {
    // ignore
  } finally {
    loadingAvailable.value = false
  }
}

async function attachTemplate() {
  if (!selectedTemplateId.value) return
  attaching.value = true
  try {
    await FeedbackService.attachFeedbackTemplate(props.eventId, selectedTemplateId.value, attachAsPrimary.value)
    showAttachDialog.value = false
    selectedTemplateId.value = null
    attachAsPrimary.value = false
    await load()
    emit('updated')
  } catch {
    // ignore
  } finally {
    attaching.value = false
  }
}

function confirmDetach(link) {
  pendingDetach.value = link
  showDetachConfirm.value = true
}

async function detachTemplate() {
  if (!pendingDetach.value) return
  detaching.value = true
  try {
    await FeedbackService.detachFeedbackTemplate(props.eventId, pendingDetach.value.template_id)
    showDetachConfirm.value = false
    pendingDetach.value = null
    await load()
    emit('updated')
  } catch {
    // ignore
  } finally {
    detaching.value = false
  }
}

async function setPrimary(templateId) {
  actionLoading.value = `primary-${templateId}`
  try {
    await FeedbackService.setPrimaryFeedbackTemplate(props.eventId, templateId)
    await load()
    emit('updated')
  } catch {
    // ignore
  } finally {
    actionLoading.value = null
  }
}

onMounted(() => {
  load()
  loadAllTemplates()
})

// Re-expose attached templates for parent use
defineExpose({ attachedTemplates, reload: load })
</script>
