import { defineStore } from 'pinia';
import { ref } from 'vue';
import { EventService } from '@/services/EventService';
import router from '@/router';
import { AdminService } from '@/services/AdminService';

export const useEventStore = defineStore('events', () => {
    const events = ref([]);
    const currentEvent = ref(null);
    const isLoading = ref(false);
    const error = ref(null);

    async function fetchAllEvents() {
        isLoading.value = true;
        error.value = null;

        try {
            const response = await EventService.getAllEvents();
            events.value = response.data;
        } catch(err) {
            console.error('Failed to fetch events:', err);
            error.value = 'Could not load events';
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchEventById(event_id) {
        isLoading.value = true;
        error.value = null;
        currentEvent.value = null;
        try{
            const response = await EventService.getEventById(event_id);
            currentEvent.value = response.data;
        } catch(err) {
            console.error('Failed to fetch event $(eventId):', err);
            error.value = 'Could not load event details';
        } finally {
            isLoading.value = false;
        }
    }

    async function createEvent(eventData) {
        isLoading.value = true;
        error.value = null;
        try {
            const response = await EventService.createEvent(eventData);
            return response.data;
        } catch (err) {
            console.error('Failed to create an event: ', err);
            error.value = err.response?.data?.detail || 'Could not create an event';
        } finally {
            isLoading.value = false;
        }
    }

    async function updateEvent(eventId, eventData) {
        isLoading.value = true;
        error.value = null;
        try {
            await EventService.updateEvent(eventId, eventData)
            router.push({name: 'admin-events'});
        } catch(err) {
            console.error('Failed to update an event: ', err);
            error.value = err.response?.data?.detail || 'Could not update an event';
        } finally {
            isLoading.value = false;
        }
    }

    async function registerForEvent(eventId, registrationData = { form_responses: {} }) {
        isLoading.value = true;
        error.value = null;
        try {
            const response = await EventService.registerForEvent(eventId, registrationData);
            return response.data;

        } catch(err){
            console.error('Failed to register for event:', err);
            error.value = err.response?.data?.detail || 'Registration Failed';
            throw err;

        } finally {
            isLoading.value = false;
        }

    }

    async function uploadEventImage(eventId, imageFile) {
        console.log('=== STORE uploadEventImage DEBUG ===');
        console.log('Event ID:', eventId);
        console.log('Image File:', imageFile);
        console.log('File name:', imageFile?.name);
        console.log('File size:', imageFile?.size);
        console.log('File type:', imageFile?.type);
        try {
            console.log('Calling AdminService.uploadEventImage...');
            const result = await AdminService.uploadEventImage(eventId, imageFile);
            console.log('Upload successful, result:', result);
            return result 
        } catch (err) {
            console.error('Failed to upload event image:', err);
            console.error('Error details:', err.response?.data);
            console.error('Error status:', err.response?.status);
            throw err;
        }
    }

    async function deleteEvent(eventId){
        isLoading.value = true;
        error.value = null;

        try {
            await EventService.deleteEvent(eventId);
            const index = events.value.findIndex(e => e.event_id === eventId);
            if (index !== -1){
                events.value.splice(index, 1);
            }
        } catch (err) {
            console.error(`Failed to delete event ${eventId}:`, err);
            throw err; 
        } finally {
            isLoading.value = false;
        }
    }

    async function uploadEventPhotos(eventId, photoFiles, processImages = true) {
        isLoading.value = true;
        error.value = null;
        try {
            const response = await EventService.uploadEventPhotos(eventId, photoFiles, processImages);
            if (currentEvent.value?.event_id === eventId) {
                currentEvent.value.event_photos = response.data.photos;
            }
            return response.data;
        } catch (err) {
            console.error('Failed to upload event photos:', err);
            error.value = err.response?.data?.detail || 'Failed to upload event photos';
            throw err;
        } finally {
            isLoading.value = false;
        }
    }

    async function deleteEventPhoto(eventId, photoId) {
        isLoading.value = true;
        error.value = null;
        try {
            await EventService.deleteEventPhoto(eventId, photoId);
            if (currentEvent.value?.event_id === eventId) {
                await fetchEventById(eventId);
            }
        } catch (err) {
            console.error('Failed to delete event photo:', err);
            error.value = err.response?.data?.detail || 'Failed to delete event photo';
            throw err;
        } finally {
            isLoading.value = false;
        }
    }

    return { events, currentEvent, isLoading, error, fetchAllEvents, fetchEventById, createEvent, updateEvent, registerForEvent, uploadEventImage, deleteEvent, uploadEventPhotos, deleteEventPhoto};
});