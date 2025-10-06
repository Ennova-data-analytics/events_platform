import ApiClient from './ApiClient';

export const FormTemplateService = {
  getAllTemplates() {
    return ApiClient.get('/form-templates/');
  },
  getTemplateById(templateId) {
    return ApiClient.get(`/form-templates/${templateId}`);
  },
  createTemplate(templateData) {
    return ApiClient.post('/form-templates/', templateData);
  },
  updateTemplate(templateId, templateData) {
    return ApiClient.put(`/form-templates/${templateId}`, templateData);
  },
  deleteTemplate(templateId) {
    return ApiClient.delete(`/form-templates/${templateId}`);
  },
};