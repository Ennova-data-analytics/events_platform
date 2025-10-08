import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import NotificationService from '@/services/NotificationService'

export const useNotificationStore = defineStore('notifications', () => {
  const notifications = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  const unreadCount = computed(() =>
    notifications.value.filter(n => !n.is_read).length
  )

  const unreadNotifications = computed(() =>
    notifications.value.filter(n => !n.is_read)
  )

  async function fetchNotifications(unreadOnly = false) {
    isLoading.value = true
    error.value = null
    try {
      const data = await NotificationService.getNotifications(unreadOnly)
      notifications.value = data
    } catch (err) {
      console.error('Failed to fetch notifications:', err)
      error.value = err.response?.data?.detail || 'Failed to load notifications'
    } finally {
      isLoading.value = false
    }
  }

  async function fetchUnreadCount() {
    try {
      const count = await NotificationService.getUnreadCount()
      return count
    } catch (err) {
      console.error('Failed to fetch unread count:', err)
      return 0
    }
  }

  async function markAsRead(notificationIds) {
    try {
      await NotificationService.markAsRead(notificationIds)

      const idsArray = Array.isArray(notificationIds) ? notificationIds : [notificationIds]
      notifications.value.forEach(notification => {
        if (idsArray.includes(notification.notification_id)) {
          notification.is_read = true
          notification.read_at = new Date().toISOString()
        }
      })
    } catch (err) {
      console.error('Failed to mark as read:', err)
      throw err
    }
  }

  async function markAllAsRead() {
    try {
      await NotificationService.markAllAsRead()

      notifications.value.forEach(notification => {
        notification.is_read = true
        notification.read_at = new Date().toISOString()
      })
    } catch (err) {
      console.error('Failed to mark all as read:', err)
      throw err
    }
  }

  async function deleteNotification(notificationId) {
    try {
      await NotificationService.deleteNotification(notificationId)

      notifications.value = notifications.value.filter(
        n => n.notification_id !== notificationId
      )
    } catch (err) {
      console.error('Failed to delete notification:', err)
      throw err
    }
  }

  function clearNotifications() {
    notifications.value = []
  }

  return {
    notifications,
    isLoading,
    error,

    unreadCount,
    unreadNotifications,

    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearNotifications
  }
})