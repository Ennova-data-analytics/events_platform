import ApiClient from "./ApiClient";

export const UserRoleService = {
    /**
     * List all users with their roles (super_admin only)
     */
    listUsers(q = null, skip = 0, limit = 50) {
        const params = { skip, limit };
        if (q) params.q = q;
        return ApiClient.get('/admin/users', { params });
    },

    /**
     * Grant organiser role to a user
     */
    grantOrganiser(userId) {
        return ApiClient.post(`/admin/users/${userId}/grant-organiser`);
    },

    /**
     * Revoke organiser role from a user
     */
    revokeOrganiser(userId) {
        return ApiClient.post(`/admin/users/${userId}/revoke-organiser`);
    }
};
