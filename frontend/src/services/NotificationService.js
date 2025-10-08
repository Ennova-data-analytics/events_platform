import apiClient from './ApiClient'

const NotificationService = {
  /**
   * Get all notifications for current user
   * @param {boolean} unreadOnly - Only fetch unread notifications
   * @param {number} limit - Maximum number to fetch
   */
  async getNotifications(unreadOnly = false, limit = 50) {
    const response = await apiClient.get('/notifications/', {
      params: { unread_only: unreadOnly, limit }
    })
    return response.data
  },


  async getUnreadCount() {
    const response = await apiClient.get('/notifications/unread-count')
    return response.data.unread_count
  },

  /**
   * Mark specific notifications as read
   * @param {number[]} notificationIds - Array of notification IDs
   */
  async markAsRead(notificationIds) {
    const response = await apiClient.post('/notifications/mark-as-read', {
      notification_ids: Array.isArray(notificationIds) ? notificationIds : [notificationIds]
    })
    return response.data
  },


  async markAllAsRead() {
    const response = await apiClient.post('/notifications/mark-all-as-read')
    return response.data
  },

  /**
   * Delete a notification
   * @param {number} notificationId
   */
  async deleteNotification(notificationId) {
    const response = await apiClient.delete(`/notifications/${notificationId}`)
    return response.data
  }
}

export default NotificationService