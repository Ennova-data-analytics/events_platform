import ApiClient from "./ApiClient";

export const UserService = {
    uploadCv(cvFile) {
        const formData = new FormData();
        formData.append("file", cvFile);

        return ApiClient.post('/users/me/cv', formData, {headers: { 'Content-Type': 'multipart/form-data', }});
    }
};