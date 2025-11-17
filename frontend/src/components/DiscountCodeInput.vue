<template>
  <div class="discount-code-section">
    <div class="discount-input-wrapper">
      <input
        v-model="discountCode"
        type="text"
        placeholder="Enter discount code"
        class="discount-input"
        :disabled="isValidating || isApplied"
        @keyup.enter="validateCode"
      />
      <button
        v-if="!isApplied"
        @click="validateCode"
        :disabled="!discountCode || isValidating"
        class="btn-validate"
      >
        {{ isValidating ? 'Validating...' : 'Apply' }}
      </button>
      <button
        v-else
        @click="removeCode"
        class="btn-remove"
      >
        Remove
      </button>
    </div>

    <div v-if="validationMessage" :class="['validation-message', isApplied ? 'success' : 'error']">
      {{ validationMessage }}
    </div>

    <div v-if="isApplied && discountInfo" class="discount-summary">
      <div class="price-row">
        <span>Original Price:</span>
        <span class="original-price">€{{ formatPrice(discountInfo.original_price) }}</span>
      </div>
      <div class="price-row discount">
        <span>Discount ({{ discountInfo.code }}):</span>
        <span class="discount-amount">-€{{ formatPrice(discountInfo.discount_amount) }}</span>
      </div>
      <div class="price-row final">
        <span>Final Price:</span>
        <span class="final-price">€{{ formatPrice(discountInfo.final_price) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { validateDiscountCode } from '@/services/EventService'

const props = defineProps({
  eventId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['discount-applied', 'discount-removed'])

const discountCode = ref('')
const isValidating = ref(false)
const isApplied = ref(false)
const validationMessage = ref('')
const discountInfo = ref(null)

const validateCode = async () => {
  if (!discountCode.value.trim()) return

  isValidating.value = true
  validationMessage.value = ''

  try {
    const response = await validateDiscountCode(props.eventId, discountCode.value.trim())
    const result = response.data

    if (result.valid) {
      isApplied.value = true
      validationMessage.value = result.message || 'Discount code applied successfully'
      discountInfo.value = {
        code: discountCode.value.toUpperCase(),
        original_price: result.original_price,
        discount_amount: result.discount_amount,
        final_price: result.final_price,
        discount_code_id: result.discount_code_id,
        discount_type: result.discount_type,
        discount_value: result.discount_value
      }

      emit('discount-applied', {
        code: discountCode.value.trim(),
        discountInfo: discountInfo.value
      })
    } else {
      isApplied.value = false
      validationMessage.value = result.message || 'Invalid discount code'
      discountInfo.value = null
    }
  } catch (error) {
    validationMessage.value = error.response?.data?.message || 'Error validating discount code. Please try again.'
    isApplied.value = false
    discountInfo.value = null
  } finally {
    isValidating.value = false
  }
}

const removeCode = () => {
  discountCode.value = ''
  isApplied.value = false
  validationMessage.value = ''
  discountInfo.value = null
  emit('discount-removed')
}

const formatPrice = (price) => {
  return parseFloat(price).toFixed(2)
}

watch(() => props.eventId, () => {
  removeCode()
})
</script>

<style scoped>
.discount-code-section {
  margin: 20px 0;
  padding: 15px;
  background-color: #f9f9f9;
  border-radius: 8px;
}

.discount-input-wrapper {
  display: flex;
  gap: 10px;
}

.discount-input {
  flex: 1;
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  text-transform: uppercase;
}

.discount-input:disabled {
  background-color: #e9ecef;
  cursor: not-allowed;
}

.btn-validate,
.btn-remove {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-validate {
  background-color: rgb(var(--v-theme-primary));
  color: white;
}

.btn-validate:hover:not(:disabled) {
  background-color: rgb(var(--v-theme-primary));
  opacity: 0.9;
}

.btn-validate:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.btn-remove {
  background-color: #dc3545;
  color: white;
}

.btn-remove:hover {
  background-color: #c82333;
}

.validation-message {
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 14px;
}

.validation-message.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.validation-message.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.discount-summary {
  margin-top: 15px;
  padding: 15px;
  background-color: white;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.price-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 14px;
}

.price-row.discount {
  color: #28a745;
  font-weight: 600;
}

.price-row.final {
  border-top: 2px solid #333;
  margin-top: 8px;
  padding-top: 12px;
  font-size: 16px;
  font-weight: bold;
}

.original-price {
  text-decoration: line-through;
  color: #666;
}

.discount-amount {
  color: #28a745;
}

.final-price {
  color: #007bff;
  font-size: 18px;
}
</style>
