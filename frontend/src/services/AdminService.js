import ApiClient from "./ApiClient";

export const AdminService = {
    approveRegistration(registrationId, customAmount = null) {
        const payload = {
            custom_amount_euros: (customAmount !== null && customAmount !== undefined && customAmount !== '') ? customAmount : null
        };
        return ApiClient.post(`/admin/registrations/${registrationId}/approve`, payload);
    },
    rejectRegistration(registrationId) {
        return ApiClient.post(`/admin/registrations/${registrationId}/reject`);
    },
    revertRegistrationToPending(registrationId) {
        return ApiClient.post(`/admin/registrations/${registrationId}/revert-to-pending`);
    },
    deleteRegistration(registrationId) {
        return ApiClient.delete(`/admin/registrations/${registrationId}`);
    },
    uploadEventImage(eventId, imageFile) {
        console.log('=== AdminService.uploadEventImage DEBUG ===');
        console.log('Creating FormData for event:', eventId);
        console.log('Image file:', imageFile);
        const formData = new FormData();
        formData.append("file", imageFile);
        console.log('FormData created, entries:');
        for (let pair of formData.entries()) {
            console.log(pair[0], pair[1]);
        }
        console.log('Posting to /events/' + eventId + '/image');


        return ApiClient.post(`/events/${eventId}/image`, formData, {headers: { 'Content-Type': 'multipart/form-data'}});
    },
    sendBulkEmail(eventId, emailData) {
        return ApiClient.post(`/admin/events/${eventId}/send-bulk-email`, emailData);
    }
};