import ApiClient from "./ApiClient";

export const EnnovaMemberService = {
    /**
     * Get all Ennova members with optional search and pagination
     */
    getMembers(skip = 0, limit = 100, search = null) {
        const params = { skip, limit };
        if (search) {
            params.search = search;
        }
        return ApiClient.get('/admin/ennova-members', { params });
    },

    /**
     * Search all users (for adding to members)
     */
    searchUsers(query, skip = 0, limit = 50) {
        return ApiClient.get('/admin/users/search', {
            params: { q: query, skip, limit }
        });
    },

    /**
     * Add a single user to Ennova members
     */
    addMember(userId) {
        return ApiClient.post('/admin/ennova-members/add', { user_id: userId });
    },

    /**
     * Remove a user from Ennova members
     */
    removeMember(userId) {
        return ApiClient.post('/admin/ennova-members/remove', { user_id: userId });
    },

    /**
     * Bulk add users to Ennova members
     */
    bulkAddMembers(userIds) {
        return ApiClient.post('/admin/ennova-members/bulk-add', { user_ids: userIds });
    },

    /**
     * Import members from Excel file
     */
    importFromExcel(file) {
        const formData = new FormData();
        formData.append('file', file);
        return ApiClient.post('/admin/ennova-members/import-excel', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    }
};
