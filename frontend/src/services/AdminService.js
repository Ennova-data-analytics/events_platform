import ApiClient from "./ApiClient";

export const AdminService = {
    approveRegistration(registrationId) {
        return ApiClient.post(`/admin/registrations/${registrationId}/approve`);
    },
    rejectRegistration(registrationId) {
        return ApiClient.post(`/admin/registrations/${registrationId}/reject`);
    },
    revertRegistrationToPending(registrationId) {
        return ApiClient.post(`/admin/registrations/${registrationId}/revert-to-pending`);
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
    }
};