import ApiClient from './ApiClient';

export const UploadService = {
  uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    return ApiClient.post('/uploads/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  
  getPresignedUrl(fileKey) {
    const encodedKey = encodeURIComponent(fileKey);
    return ApiClient.get(`/uploads/file-url/${encodedKey}`);
  }
};