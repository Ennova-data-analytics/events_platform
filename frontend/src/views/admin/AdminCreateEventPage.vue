<template>
  <div>
    <h1 class="text-h5 mb-6">Create New Event</h1>
    <v-card>
      <v-card-text class="pa-6">
        <EventCreateStepper @submit="handleCreateEvent" />
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import EventCreateStepper from '@/components/forms/EventCreateStepper.vue'
import { useEventStore } from '@/stores/events.store.js'
import { useRouter } from 'vue-router'
import TicketTypeService from '@/services/TicketTypeService.js'

const eventStore = useEventStore()
const router = useRouter()

const handleCreateEvent = async (eventData, imageFile, ticketTypeDefs = []) => {
  try {
    const newEvent = await eventStore.createEvent(eventData)

    if (newEvent && newEvent.event_id) {
      const uploads = []

      if (imageFile) {
        uploads.push(eventStore.uploadEventImage(newEvent.event_id, imageFile))
      }

      for (const [idx, tt] of ticketTypeDefs.entries()) {
        uploads.push(TicketTypeService.createTicketType(newEvent.event_id, { ...tt, display_order: idx }))
      }

      await Promise.all(uploads)

      router.push({ name: 'admin-edit-event', params: { id: newEvent.event_id }, query: { tab: 'media' } })
    } else {
      router.push({ name: 'admin-events' })
    }
  } catch (error) {
    console.error('Failed to create event:', error)
  }
}
</script>
