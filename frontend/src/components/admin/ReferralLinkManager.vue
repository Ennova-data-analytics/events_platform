<template>
  <div class="pa-4">
    <div class="d-flex justify-space-between align-center mb-4">
      <v-btn
        color="success"
        prepend-icon="mdi-plus"
        @click="showCreateForm = true"
      >
        Create Referral Link
      </v-btn>
    </div>

    <v-card v-if="referralLinks.length > 0">
      <v-data-table
        :headers="headers"
        :items="referralLinks"
        :loading="isLoading"
        item-value="link_id"
      >
        <template v-slot:item.referrer_name="{ item }">
          <span class="font-weight-bold text-primary">{{ item.referrer_name }}</span>
        </template>

        <template v-slot:item.code="{ item }">
          <div class="d-flex align-center">
            <code class="mr-2">{{ item.code }}</code>
            <v-btn
              icon="mdi-content-copy"
              variant="text"
              size="x-small"
              @click="copyLink(item.code)"
              title="Copy referral URL"
            ></v-btn>
          </div>
        </template>

        <template v-slot:item.commission_percentage="{ item }">
          <v-chip size="small" color="primary" variant="tonal">
            {{ item.commission_percentage }}%
          </v-chip>
        </template>

        <template v-slot:item.registrations="{ item }">
          {{ item.registration_count }} total / {{ item.paid_registration_count }} paid
        </template>

        <template v-slot:item.total_revenue="{ item }">
          {{ item.total_revenue > 0 ? `€${parseFloat(item.total_revenue).toFixed(2)}` : '—' }}
        </template>

        <template v-slot:item.commission_owed="{ item }">
          <v-chip
            :color="parseFloat(item.commission_owed) > 0 ? 'warning' : 'default'"
            size="small"
            variant="tonal"
          >
            {{ parseFloat(item.commission_owed) > 0 ? `€${parseFloat(item.commission_owed).toFixed(2)}` : '—' }}
          </v-chip>
        </template>

        <template v-slot:item.is_active="{ item }">
          <v-chip
            :color="item.is_active ? 'success' : 'error'"
            size="small"
            variant="tonal"
          >
            {{ item.is_active ? 'Active' : 'Inactive' }}
          </v-chip>
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            icon="mdi-pencil"
            variant="text"
            color="warning"
            size="small"
            @click="editLink(item)"
            title="Edit"
          ></v-btn>
          <v-btn
            icon="mdi-delete"
            variant="text"
            color="error"
            size="small"
            @click="deleteLink(item.link_id)"
            title="Delete"
          ></v-btn>
        </template>
      </v-data-table>
    </v-card>

    <v-card v-else class="pa-8 text-center">
      <v-icon size="64" color="grey-lighten-1">mdi-link-variant</v-icon>
      <p class="text-grey mt-4">No referral links created yet.</p>
    </v-card>

    <v-dialog v-model="showCreateForm" max-width="600px" persistent>
      <v-card>
        <v-card-title class="text-h5">
          {{ editingLink ? 'Edit' : 'Create' }} Referral Link
        </v-card-title>

        <v-card-text>
          <v-form ref="formRef">
            <v-text-field
              v-model="formData.referrer_name"
              label="Referrer Name *"
              placeholder="e.g., John's Instagram"
              variant="outlined"
              density="comfortable"
              :rules="[v => !!v || 'Referrer name is required']"
              required
              class="mb-2"
            ></v-text-field>

            <v-text-field
              v-model.number="formData.commission_percentage"
              label="Commission Percentage * (0-100%)"
              type="number"
              step="0.01"
              min="0"
              max="100"
              variant="outlined"
              density="comfortable"
              :rules="[v => v >= 0 && v <= 100 || 'Must be between 0 and 100']"
              required
              class="mb-2"
            ></v-text-field>

            <v-switch
              v-if="editingLink"
              v-model="formData.is_active"
              label="Active"
              color="success"
              density="comfortable"
            ></v-switch>
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            color="grey"
            variant="text"
            @click="closeModal"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="flat"
            @click="submitForm"
            :loading="isSubmitting"
          >
            {{ editingLink ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>

    <v-dialog v-model="deleteDialog.show" max-width="500">
      <v-card>
        <v-card-title class="text-h5">
          Delete Referral Link?
        </v-card-title>
        <v-card-text>
          Are you sure you want to delete the referral link for <strong>{{ deleteDialog.referrerName }}</strong>?
          Existing registrations will keep their referral data but the link will no longer be usable.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            color="grey"
            variant="text"
            @click="deleteDialog.show = false"
          >
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  getEventReferralLinks,
  createReferralLink,
  updateReferralLink,
  deleteReferralLink
} from '@/services/EventService'

const props = defineProps({
  eventId: {
    type: Number,
    required: true
  }
})

const referralLinks = ref([])
const isLoading = ref(false)
const showCreateForm = ref(false)
const editingLink = ref(null)
const isSubmitting = ref(false)
const formRef = ref(null)

const headers = [
  { title: 'Referrer', key: 'referrer_name', sortable: true },
  { title: 'Code', key: 'code', sortable: false },
  { title: 'Commission', key: 'commission_percentage', sortable: true },
  { title: 'Registrations', key: 'registrations', sortable: false },
  { title: 'Revenue', key: 'total_revenue', sortable: false },
  { title: 'Commission Owed', key: 'commission_owed', sortable: false },
  { title: 'Status', key: 'is_active', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'center' }
]

const formData = ref({
  referrer_name: '',
  commission_percentage: 0,
  is_active: true
})

const snackbar = ref({
  show: false,
  text: '',
  color: 'success'
})

const deleteDialog = ref({
  show: false,
  linkId: null,
  referrerName: ''
})

const loadReferralLinks = async () => {
  isLoading.value = true
  try {
    const response = await getEventReferralLinks(props.eventId)
    referralLinks.value = response.data
  } catch (error) {
    console.error('Error loading referral links:', error)
    showSnackbar('Failed to load referral links', 'error')
  } finally {
    isLoading.value = false
  }
}

const submitForm = async () => {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  isSubmitting.value = true

  try {
    if (editingLink.value) {
      const updateData = {
        referrer_name: formData.value.referrer_name,
        commission_percentage: formData.value.commission_percentage,
        is_active: formData.value.is_active
      }
      await updateReferralLink(editingLink.value.link_id, updateData)
      showSnackbar('Referral link updated successfully', 'success')
    } else {
      await createReferralLink({
        event_id: props.eventId,
        referrer_name: formData.value.referrer_name,
        commission_percentage: formData.value.commission_percentage
      })
      showSnackbar('Referral link created successfully', 'success')
    }

    await loadReferralLinks()
    closeModal()
  } catch (error) {
    console.error('Error saving referral link:', error)
    showSnackbar(`Failed to ${editingLink.value ? 'update' : 'create'} referral link`, 'error')
  } finally {
    isSubmitting.value = false
  }
}

const editLink = (link) => {
  editingLink.value = link
  formData.value = {
    referrer_name: link.referrer_name,
    commission_percentage: parseFloat(link.commission_percentage),
    is_active: link.is_active
  }
  showCreateForm.value = true
}

const deleteLink = (linkId) => {
  const link = referralLinks.value.find(l => l.link_id === linkId)
  deleteDialog.value = {
    show: true,
    linkId: linkId,
    referrerName: link?.referrer_name || ''
  }
}

const confirmDelete = async () => {
  try {
    await deleteReferralLink(deleteDialog.value.linkId)
    await loadReferralLinks()
    showSnackbar('Referral link deleted successfully', 'success')
  } catch (error) {
    console.error('Error deleting referral link:', error)
    showSnackbar('Failed to delete referral link', 'error')
  } finally {
    deleteDialog.value.show = false
  }
}

const copyLink = async (code) => {
  const url = `${window.location.origin}/event/${props.eventId}/register?ref=${code}`
  try {
    await navigator.clipboard.writeText(url)
    showSnackbar('Referral URL copied to clipboard', 'success')
  } catch {
    showSnackbar('Failed to copy URL', 'error')
  }
}

const closeModal = () => {
  showCreateForm.value = false
  editingLink.value = null
  formData.value = {
    referrer_name: '',
    commission_percentage: 0,
    is_active: true
  }
  formRef.value?.reset()
}

const showSnackbar = (text, color = 'success') => {
  snackbar.value = {
    show: true,
    text,
    color
  }
}

onMounted(() => {
  loadReferralLinks()
})
</script>
