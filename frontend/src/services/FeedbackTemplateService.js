import ApiClient from './ApiClient';

export const FeedbackTemplateService = {
  getAllTemplates() {
    return ApiClient.get('/feedback-templates/');
  },
  getTemplateById(templateId) {
    return ApiClient.get(`/feedback-templates/${templateId}`);
  },
  createTemplate(templateData) {
    return ApiClient.post('/feedback-templates/', templateData);
  },
  updateTemplate(templateId, templateData) {
    return ApiClient.put(`/feedback-templates/${templateId}`, templateData);
  },
  deleteTemplate(templateId) {
    return ApiClient.delete(`/feedback-templates/${templateId}`);
  },
};
