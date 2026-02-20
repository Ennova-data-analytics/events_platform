<template>
  <div class="pa-4">
    <div class="d-flex justify-space-between align-center mb-4">
      <v-btn
        color="success"
        prepend-icon="mdi-plus"
        @click="showCreateForm = true"
      >
        Create Discount Code
      </v-btn>
    </div>

    <v-card v-if="discountCodes.length > 0">
      <v-data-table
        :headers="headers"
        :items="discountCodes"
        :loading="isLoading"
        item-value="code_id"
      >
        <template v-slot:item.code="{ item }">
          <span class="font-weight-bold text-primary">{{ item.code }}</span>
        </template>

        <template v-slot:item.discount_type="{ item }">
          {{ item.discount_type === 'percentage' ? 'Percentage' : 'Fixed Amount' }}
        </template>

        <template v-slot:item.discount_value="{ item }">
          <v-chip size="small" color="primary" variant="tonal">
            {{ item.discount_type === 'percentage' ? `${item.discount_value}%` : `€${item.discount_value}` }}
          </v-chip>
        </template>

        <template v-slot:item.usage="{ item }">
          <a
            href="#"
            class="text-decoration-none"
            @click.prevent="viewUsages(item)"
          >
            {{ item.used_count }}{{ item.max_uses ? ` / ${item.max_uses}` : ' / ∞' }}
          </a>
        </template>

        <template v-slot:item.expires_at="{ item }">
          {{ item.expires_at ? formatDate(item.expires_at) : 'Never' }}
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
            icon="mdi-eye"
            variant="text"
            color="info"
            size="small"
            @click="viewUsages(item)"
            title="View Usage"
          ></v-btn>
          <v-btn
            icon="mdi-pencil"
            variant="text"
            color="warning"
            size="small"
            @click="editCode(item)"
            title="Edit"
          ></v-btn>
          <v-btn
            icon="mdi-delete"
            variant="text"
            color="error"
            size="small"
            @click="deleteCode(item.code_id)"
            title="Delete"
          ></v-btn>
        </template>
      </v-data-table>
    </v-card>

    <v-card v-else class="pa-8 text-center">
      <v-icon size="64" color="grey-lighten-1">mdi-ticket-percent-outline</v-icon>
      <p class="text-grey mt-4">No discount codes created yet.</p>
    </v-card>

    <v-dialog v-model="showCreateForm" max-width="600px" persistent>
      <v-card>
        <v-card-title class="text-h5">
          {{ editingCode ? 'Edit' : 'Create' }} Discount Code
        </v-card-title>

        <v-card-text>
          <v-form ref="formRef">
            <v-text-field
              v-model="formData.code"
              label="Code *"
              placeholder="e.g., SUMMER2024"
              variant="outlined"
              density="comfortable"
              :disabled="editingCode !== null"
              :rules="[v => !!v || 'Code is required']"
              required
              class="mb-2"
            ></v-text-field>

            <v-select
              v-model="formData.discount_type"
              label="Discount Type *"
              :items="[
                { title: 'Percentage', value: 'percentage' },
                { title: 'Fixed Amount (€)', value: 'fixed_amount' }
              ]"
              variant="outlined"
              density="comfortable"
              required
              class="mb-2"
            ></v-select>

            <v-text-field
              v-model.number="formData.discount_value"
              :label="`Discount Value * ${formData.discount_type === 'percentage' ? '(0-100%)' : '(€)'}`"
              type="number"
              step="0.01"
              min="0"
              :max="formData.discount_type === 'percentage' ? 100 : undefined"
              variant="outlined"
              density="comfortable"
              :rules="[v => v > 0 || 'Value must be greater than 0']"
              required
              class="mb-2"
            ></v-text-field>

            <v-text-field
              v-model.number="formData.max_uses"
              label="Max Uses (leave empty for unlimited)"
              type="number"
              min="1"
              variant="outlined"
              density="comfortable"
              class="mb-2"
            ></v-text-field>

            <v-text-field
              v-model="formData.expires_at"
              label="Expiration Date (optional)"
              type="datetime-local"
              variant="outlined"
              density="comfortable"
              class="mb-2"
            ></v-text-field>

            <v-switch
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
            {{ editingCode ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Usage Details Dialog -->
    <v-dialog v-model="usageDialog.show" max-width="750px">
      <v-card>
        <v-card-title class="d-flex align-center">
          <span class="text-h5">Usage: {{ usageDialog.code }}</span>
          <v-spacer></v-spacer>
          <v-chip size="small" color="primary" variant="tonal" class="ml-2">
            {{ usageDialog.usedCount }} used
          </v-chip>
        </v-card-title>

        <v-card-text>
          <v-progress-linear v-if="usageDialog.loading" indeterminate color="primary" class="mb-4"></v-progress-linear>

          <div v-else-if="usageDialog.usages.length === 0" class="text-center pa-4">
            <v-icon size="48" color="grey-lighten-1">mdi-account-off-outline</v-icon>
            <p class="text-grey mt-2">No one has used this discount code yet.</p>
          </div>

          <v-table v-else density="compact">
            <thead>
              <tr>
                <th>User</th>
                <th>Status</th>
                <th class="text-right">Discount</th>
                <th class="text-right">Paid</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="usage in usageDialog.usages" :key="usage.registration_id">
                <td>
                  <div>{{ usage.user_full_name || 'N/A' }}</div>
                  <div class="text-caption text-grey">{{ usage.user_email }}</div>
                </td>
                <td>
                  <v-chip
                    :color="usage.registration_status === 'Paid' ? 'success' : 'warning'"
                    size="x-small"
                    variant="tonal"
                  >
                    {{ usage.registration_status }}
                  </v-chip>
                </td>
                <td class="text-right">
                  {{ usage.discount_amount_euros != null ? `€${Number(usage.discount_amount_euros).toFixed(2)}` : '-' }}
                </td>
                <td class="text-right">
                  {{ usage.final_amount_euros != null ? `€${Number(usage.final_amount_euros).toFixed(2)}` : '-' }}
                </td>
                <td>{{ usage.registration_date ? formatDate(usage.registration_date) : '-' }}</td>
              </tr>
            </tbody>
          </v-table>

          <!-- Backpopulate section -->
          <v-divider class="my-4"></v-divider>
          <div class="d-flex align-center">
            <div class="flex-grow-1">
              <div class="text-subtitle-2">Backpopulate from payments</div>
              <div class="text-caption text-grey">
                Find paid registrations that match this discount's expected price and link them to this code.
              </div>
            </div>
            <v-btn
              color="secondary"
              variant="tonal"
              size="small"
              prepend-icon="mdi-database-search"
              :loading="usageDialog.backpopulating"
              @click="runBackpopulate"
            >
              Backpopulate
            </v-btn>
          </div>

          <v-alert
            v-if="usageDialog.backpopulateResult !== null"
            :type="usageDialog.backpopulateResult.matched_count > 0 ? 'success' : 'info'"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            <template v-if="usageDialog.backpopulateResult.matched_count > 0">
              Found and linked {{ usageDialog.backpopulateResult.matched_count }} registration(s) to this discount code.
            </template>
            <template v-else>
              No matching registrations found. All paid registrations either already have a discount code assigned or don't match the expected discounted price.
            </template>
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            color="grey"
            variant="text"
            @click="usageDialog.show = false"
          >
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog.show" max-width="500">
      <v-card>
        <v-card-title class="text-h5">
          Delete Discount Code?
        </v-card-title>
        <v-card-text>
          Are you sure you want to delete the discount code <strong>{{ deleteDialog.codeName }}</strong>?
          This action cannot be undone.
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
  getEventDiscountCodes,
  createDiscountCode,
  updateDiscountCode,
  deleteDiscountCode,
  getDiscountCodeUsages,
  backpopulateDiscountCode
} from '@/services/EventService'

const props = defineProps({
  eventId: {
    type: Number,
    required: true
  }
})

const discountCodes = ref([])
const isLoading = ref(false)
const showCreateForm = ref(false)
const editingCode = ref(null)
const isSubmitting = ref(false)
const formRef = ref(null)

const headers = [
  { title: 'Code', key: 'code', sortable: true },
  { title: 'Type', key: 'discount_type', sortable: true },
  { title: 'Value', key: 'discount_value', sortable: false },
  { title: 'Usage', key: 'usage', sortable: false },
  { title: 'Expires', key: 'expires_at', sortable: true },
  { title: 'Status', key: 'is_active', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'center' }
]

const formData = ref({
  code: '',
  discount_type: 'percentage',
  discount_value: 0,
  max_uses: null,
  expires_at: null,
  is_active: true
})

const snackbar = ref({
  show: false,
  text: '',
  color: 'success'
})

const deleteDialog = ref({
  show: false,
  codeId: null,
  codeName: ''
})

const usageDialog = ref({
  show: false,
  codeId: null,
  code: '',
  usedCount: 0,
  usages: [],
  loading: false,
  backpopulating: false,
  backpopulateResult: null
})

const loadDiscountCodes = async () => {
  isLoading.value = true
  try {
    const response = await getEventDiscountCodes(props.eventId)
    discountCodes.value = response.data
  } catch (error) {
    console.error('Error loading discount codes:', error)
    showSnackbar('Failed to load discount codes', 'error')
  } finally {
    isLoading.value = false
  }
}

const viewUsages = async (code) => {
  usageDialog.value = {
    show: true,
    codeId: code.code_id,
    code: code.code,
    usedCount: code.used_count,
    usages: [],
    loading: true,
    backpopulating: false,
    backpopulateResult: null
  }

  try {
    const response = await getDiscountCodeUsages(code.code_id)
    usageDialog.value.usages = response.data.usages
    usageDialog.value.usedCount = response.data.used_count
  } catch (error) {
    console.error('Error loading usage details:', error)
    showSnackbar('Failed to load usage details', 'error')
  } finally {
    usageDialog.value.loading = false
  }
}

const runBackpopulate = async () => {
  usageDialog.value.backpopulating = true
  usageDialog.value.backpopulateResult = null

  try {
    const response = await backpopulateDiscountCode(usageDialog.value.codeId)
    usageDialog.value.backpopulateResult = response.data

    if (response.data.matched_count > 0) {
      // Refresh the usage list and the main table
      const usageResponse = await getDiscountCodeUsages(usageDialog.value.codeId)
      usageDialog.value.usages = usageResponse.data.usages
      usageDialog.value.usedCount = usageResponse.data.used_count
      await loadDiscountCodes()
    }
  } catch (error) {
    console.error('Error backpopulating:', error)
    showSnackbar('Failed to backpopulate discount code usage', 'error')
  } finally {
    usageDialog.value.backpopulating = false
  }
}

const submitForm = async () => {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  isSubmitting.value = true

  try {
    const payload = {
      ...formData.value,
      event_id: props.eventId
    }

    if (!payload.max_uses) delete payload.max_uses
    if (!payload.expires_at) delete payload.expires_at

    if (editingCode.value) {
      const { code, event_id, ...updateData } = payload
      await updateDiscountCode(editingCode.value.code_id, updateData)
      showSnackbar('Discount code updated successfully', 'success')
    } else {
      await createDiscountCode(payload)
      showSnackbar('Discount code created successfully', 'success')
    }

    await loadDiscountCodes()
    closeModal()
  } catch (error) {
    console.error('Error saving discount code:', error)
    showSnackbar(`Failed to ${editingCode.value ? 'update' : 'create'} discount code`, 'error')
  } finally {
    isSubmitting.value = false
  }
}

const editCode = (code) => {
  editingCode.value = code
  formData.value = {
    code: code.code,
    discount_type: code.discount_type,
    discount_value: code.discount_value,
    max_uses: code.max_uses,
    expires_at: code.expires_at ? new Date(code.expires_at).toISOString().slice(0, 16) : null,
    is_active: code.is_active
  }
  showCreateForm.value = true
}

const deleteCode = (codeId) => {
  const code = discountCodes.value.find(c => c.code_id === codeId)
  deleteDialog.value = {
    show: true,
    codeId: codeId,
    codeName: code?.code || ''
  }
}

const confirmDelete = async () => {
  try {
    await deleteDiscountCode(deleteDialog.value.codeId)
    await loadDiscountCodes()
    showSnackbar('Discount code deleted successfully', 'success')
  } catch (error) {
    console.error('Error deleting discount code:', error)
    showSnackbar('Failed to delete discount code', 'error')
  } finally {
    deleteDialog.value.show = false
  }
}

const closeModal = () => {
  showCreateForm.value = false
  editingCode.value = null
  formData.value = {
    code: '',
    discount_type: 'percentage',
    discount_value: 0,
    max_uses: null,
    expires_at: null,
    is_active: true
  }
  formRef.value?.reset()
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString('en-GB', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const showSnackbar = (text, color = 'success') => {
  snackbar.value = {
    show: true,
    text,
    color
  }
}

onMounted(() => {
  loadDiscountCodes()
})
</script>

<style scoped>
/* Additional custom styles if needed */
</style>
