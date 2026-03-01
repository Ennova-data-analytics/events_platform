<template>
  <v-menu
    v-model="menuOpen"
    :close-on-content-click="false"
    location="bottom end"
    offset="8"
  >
    <template v-slot:activator="{ props }">
      <v-btn
        icon
        v-bind="props"
        @click="handleBellClick"
      >
        <v-badge
          :content="unreadCount"
          :model-value="unreadCount > 0"
          color="error"
          overlap
        >
          <v-icon color="white">mdi-bell</v-icon>
        </v-badge>
      </v-btn>
    </template>

    <v-card
      max-width="420"
      max-height="600"
      class="notification-card"
    >
      <v-card-title class="d-flex justify-space-between align-center px-4 py-3">
        <span class="text-h6">Notifications</span>
        <v-btn
          v-if="unreadCount > 0"
          size="small"
          variant="text"
          color="primary"
          @click="handleMarkAllAsRead"
        >
          Mark all read
        </v-btn>
      </v-card-title>

      <v-divider />

      <!-- Notifications List -->
      <div v-if="isLoading" class="pa-4 text-center">
        <v-progress-circular indeterminate color="primary" />
      </div>

      <v-list v-else-if="notifications.length > 0" class="pa-0">
        <template v-for="(notification, index) in notifications" :key="notification.notification_id">
          <v-list-item
            :class="{ 'bg-blue-lighten-5': !notification.is_read }"
            class="notification-item"
            @click="handleNotificationClick(notification)"
          >
            <template v-slot:prepend>
              <v-avatar :color="getNotificationColor(notification.notification_type)" size="40">
                <v-icon color="white" size="20">
                  {{ getNotificationIcon(notification.notification_type) }}
                </v-icon>
              </v-avatar>
            </template>

            <v-list-item-title class="text-wrap font-weight-medium mb-1">
              {{ notification.title }}
            </v-list-item-title>

            <v-list-item-subtitle class="text-wrap">
              {{ notification.message }}
            </v-list-item-subtitle>

            <v-list-item-subtitle class="text-caption mt-2">
              {{ formatTimestamp(notification.created_at) }}
            </v-list-item-subtitle>

            <template v-slot:append>
              <div class="d-flex align-center gap-2">
                <v-icon
                  v-if="!notification.is_read"
                  size="8"
                  color="primary"
                >
                  mdi-circle
                </v-icon>

                <v-btn
                  icon="mdi-close"
                  size="x-small"
                  variant="text"
                  @click.stop="handleDelete(notification.notification_id)"
                />
              </div>
            </template>
          </v-list-item>

          <v-divider v-if="index < notifications.length - 1" />
        </template>
      </v-list>

      <v-card-text v-else class="text-center py-8 text-grey">
        <v-icon size="48" color="grey-lighten-1">mdi-bell-outline</v-icon>
        <p class="mt-2">No notifications yet</p>
      </v-card-text>

      <v-divider v-if="notifications.length > 0" />
      <v-card-actions v-if="notifications.length > 0" class="justify-center">
        <v-btn
          variant="text"
          color="primary"
          @click="viewAllNotifications"
        >
          View All Notifications
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useNotificationStore } from '@/stores/notifications.store'
import { useRouter } from 'vue-router'
import { formatDistanceToNow } from 'date-fns'

const notificationStore = useNotificationStore()
const router = useRouter()

const menuOpen = ref(false)

const notifications = computed(() => notificationStore.notifications)
const unreadCount = computed(() => notificationStore.unreadCount)
const isLoading = computed(() => notificationStore.isLoading)

function getNotificationIcon(type) {
  const icons = {
    'registration_approved': 'mdi-check-circle',
    'registration_rejected': 'mdi-close-circle',
    'registration_created': 'mdi-information',
    'event_reminder': 'mdi-calendar-clock',
    'event_updated': 'mdi-calendar-edit',
  }
  return icons[type] || 'mdi-bell'
}

function getNotificationColor(type) {
  const colors = {
    'registration_approved': 'success',
    'registration_rejected': 'error',
    'registration_created': 'info',
    'event_reminder': 'warning',
    'event_updated': 'primary',
  }
  return colors[type] || 'grey'
}

function formatTimestamp(timestamp) {
  try {
    return formatDistanceToNow(new Date(timestamp), { addSuffix: true })
  } catch (e) {
    return timestamp
  }
}

async function handleBellClick() {
  await notificationStore.fetchNotifications()
}

async function handleNotificationClick(notification) {
  if (!notification.is_read) {
    await notificationStore.markAsRead(notification.notification_id)
  }

  if (notification.related_entity_type === 'event' && notification.related_entity_id) {
    menuOpen.value = false
    router.push(`/event/${notification.related_entity_id}`)
  }
}

async function handleMarkAllAsRead() {
  await notificationStore.markAllAsRead()
}

async function handleDelete(notificationId) {
  await notificationStore.deleteNotification(notificationId)
}

function viewAllNotifications() {
  menuOpen.value = false
  // router.push('/notifications')
}

onMounted(() => {
  notificationStore.fetchNotifications()
})
</script>

<style scoped>
.notification-card {
  overflow-y: auto;
}

.notification-item {
  cursor: pointer;
  transition: background-color 0.2s;
}

.notification-item:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

.gap-2 {
  gap: 8px;
}
</style>
