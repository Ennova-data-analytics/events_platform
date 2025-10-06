import ApiClient from "./ApiClient";

export const AdminService = {
    approveRegistration(registrationId) {
        return ApiClient.post(`/admin/registrations/${registrationId}/approve`);
    },
    rejectRegistration(registrationId) {
        return ApiClient.post(`/admin/registrations/${registrationId}/reject`);
    },
    uploadEventImage(eventId, imageFile) {
        const formData = new FormData();
        formData.append("file", imageFile);
        return ApiClient.post(`/events/${eventId}/image`, formData);
    }
};