import ApiClient from './ApiClient';

export const EmailTemplateService = {
  getAllTemplates(templateType = null) {
    const params = templateType ? { template_type: templateType } : {};
    return ApiClient.get('/email-templates/', { params });
  },
  getTemplateById(templateId) {
    return ApiClient.get(`/email-templates/${templateId}`);
  },
  createTemplate(templateData) {
    return ApiClient.post('/email-templates/', templateData);
  },
  updateTemplate(templateId, templateData) {
    return ApiClient.put(`/email-templates/${templateId}`, templateData);
  },
  deleteTemplate(templateId) {
    return ApiClient.delete(`/email-templates/${templateId}`);
  },
};
