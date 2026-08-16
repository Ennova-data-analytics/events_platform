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
    },

    /**
     * Grant the recruiter role (recruitment panel access)
     */
    grantRecruiter(userId) {
        return ApiClient.post(`/admin/users/${userId}/grant-recruiter`);
    },

    /**
     * Revoke the recruiter role (also clears department scoping)
     */
    revokeRecruiter(userId) {
        return ApiClient.post(`/admin/users/${userId}/revoke-recruiter`);
    },

    /**
     * Departments a recruiter is scoped to
     */
    getRecruiterDepartments(userId) {
        return ApiClient.get(`/hr/recruitment/recruiters/${userId}/departments`);
    },

    /**
     * Set the departments a recruiter can review
     */
    setRecruiterDepartments(userId, departmentIds) {
        return ApiClient.put(`/hr/recruitment/recruiters/${userId}/departments`, { department_ids: departmentIds });
    },

    /**
     * Department catalog (for the scope picker)
     */
    listDepartments() {
        return ApiClient.get('/hr/recruitment/departments');
    }
};
